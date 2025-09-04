from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import logging
from typing import Dict, Any, List

from app.models.database import get_db
from app.models.task import Task
from app.models.execution import Execution, ExecutionCreate, ExecutionResponse
from app.models.file import File as FileModel
from app.services.automation import AutomationEngine, automation_engines, websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/end-session/{session_id}")
async def end_session(session_id: str):
    """Fully close the browser and VNC session, freeing resources."""
    try:
        if session_id not in automation_engines:
            # If engine already gone, consider it already closed
            return {"message": "Session already closed", "session_id": session_id}
        engine = automation_engines[session_id]
        await engine.end_session()
        # Remove engine from registry
        del automation_engines[session_id]
        return {"message": "Session closed", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to close session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to close session: {str(e)}")
class ExecuteRequest(BaseModel):
    file_id: int

@router.post("/execute/{task_id}")
async def execute_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start executing an automation task"""
    try:
        # Get task
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        file_id = request.file_id
        file_record = None
        if file_id:
            result = await db.execute(select(FileModel).where(FileModel.id == file_id))
            file_record = result.scalar_one_or_none()
            if not file_record:
                raise HTTPException(status_code=404, detail=f"File with id {file_id} not found.")
            if file_record.task_id != task_id:
                raise HTTPException(status_code=400, detail="File does not belong to this task.")

        # Create execution record
        execution = Execution(
            session_id=session_id,
            task_id=task_id,
            status="pending",
            total_steps=len(task.steps) if task.steps else 0,
            file_id=file_id
        )
        
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        
        # Create automation engine
        engine = AutomationEngine(session_id, websocket_manager)
        engine.execution_id = execution.id
        automation_engines[session_id] = engine
        
        # Convert task data
        task_data = {
            "id": task.id,
            "name": task.name,
            "steps": task.steps,
            "script_path": task.script_path
        }
        
        # Start automation in background
        background_tasks.add_task(engine.execute_task, task_data, file=file_record, execution_id=execution.id)
        
        logger.info(f"Started automation for task {task_id}, session {session_id}")
        
        return {
            "session_id": session_id,
            "task_id": task_id,
            "status": "started",
            "message": "Automation started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start automation for task {task_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start automation: {str(e)}"
        )

@router.post("/pause/{session_id}")
async def pause_automation(session_id: str):
    """Pause automation"""
    try:
        if session_id not in automation_engines:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation session {session_id} not found"
            )
        
        engine = automation_engines[session_id]
        await engine.pause(engine.execution_id)
        
        return {"message": "Automation paused", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause automation {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause automation: {str(e)}"
        )

@router.post("/resume/{session_id}")
async def resume_automation(session_id: str):
    """Resume automation"""
    try:
        if session_id not in automation_engines:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation session {session_id} not found"
            )
        
        engine = automation_engines[session_id]
        await engine.resume(engine.execution_id)
        
        return {"message": "Automation resumed", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume automation {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume automation: {str(e)}"
        )

@router.post("/stop/{session_id}")
async def stop_automation(session_id: str):
    """Stop automation but keep the VNC session/browser open for manual control"""
    try:
        if session_id not in automation_engines:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation session {session_id} not found"
            )
        
        engine = automation_engines[session_id]
        await engine.stop(engine.execution_id)
        
        # IMPORTANT: do NOT delete the engine here so manual control remains available
        return {"message": "Automation stopped (manual control available)", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop automation {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop automation: {str(e)}"
        )

@router.get("/status/{session_id}")
async def get_automation_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get automation status"""
    try:
        # Get execution from database
        result = await db.execute(
            select(Execution).where(Execution.session_id == session_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {session_id} not found"
            )
        
        # Check if engine is still present (manual control may still be available even if not running)
        is_active = session_id in automation_engines
        
        return {
            "session_id": session_id,
            "status": execution.status,
            "current_step": execution.current_step,
            "total_steps": execution.total_steps,
            "is_active": is_active,
            "start_time": execution.start_time,
            "end_time": execution.end_time,
            "error_message": execution.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )
