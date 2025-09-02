from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import logging
from typing import Dict, Any

from app.models.database import get_db
from app.models.task import Task
from app.models.execution import Execution, ExecutionCreate, ExecutionResponse
from app.services.automation import AutomationEngine, automation_engines, websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class ExecuteRequest(BaseModel):
    data_file: Optional[str] = None

@router.post("/execute/{task_id}")
async def execute_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    request: Optional[ExecuteRequest] = None,  # Make the request body optional
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
        
        # Create execution record
        execution = Execution(
            session_id=session_id,
            task_id=task_id,
            status="pending",
            total_steps=len(task.steps)
        )
        
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        
        # Create automation engine
        engine = AutomationEngine(session_id, websocket_manager)
        automation_engines[session_id] = engine
        
        # Convert task data
        task_data = {
            "id": task.id,
            "name": task.name,
            "steps": task.steps
        }
        
        # Safely get the data_file if the request body exists
        data_file_name = request.data_file if request else None
        
        # Start automation in background, optionally with data_file
        background_tasks.add_task(engine.execute_task, task_data, data_file=data_file_name)
        
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
        await engine.pause()
        
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
        await engine.resume()
        
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
    """Stop automation"""
    try:
        if session_id not in automation_engines:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation session {session_id} not found"
            )
        
        engine = automation_engines[session_id]
        await engine.stop()
        
        # Clean up
        del automation_engines[session_id]
        
        return {"message": "Automation stopped", "session_id": session_id}
        
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
        
        # Check if engine is still running
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
