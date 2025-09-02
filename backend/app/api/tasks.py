from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload # Import selectinload
from typing import List
import logging

from app.models.database import get_db
from app.models.task import Task, TaskCreate, TaskUpdate, TaskResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new automation task"""
    try:
        # Convert Pydantic models to dict for JSON storage
        steps_data = [step.model_dump() for step in task_data.steps]
        prerequisites_data = [prereq.model_dump() for prereq in task_data.prerequisites] if task_data.prerequisites else None
        
        # Create task
        task = Task(
            name=task_data.name,
            description=task_data.description,
            steps=steps_data,
            prerequisites=prerequisites_data,
            status="draft"
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Created task: {task.name} (ID: {task.id})")
        return task
        
    except Exception as e:
        logger.error(f"Failed to create task: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all automation tasks"""
    try:
        query = (
            select(Task)
            .offset(skip)
            .limit(limit)
            .order_by(Task.created_at.desc())
            .options(selectinload(Task.executions))  # Eagerly load executions
        )
        result = await db.execute(query)
        tasks = result.scalars().unique().all() # Use .unique() to handle cartesian product
        return tasks
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {str(e)}", exc_info=True) # Add exc_info for full traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: An internal error occurred."
        )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific task by ID"""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task: {str(e)}"
        )

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a task"""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        # Update fields
        update_data = task_update.model_dump(exclude_unset=True)
        
        # Handle steps conversion
        if "steps" in update_data and update_data["steps"]:
            update_data["steps"] = [step.model_dump() for step in task_update.steps]
        
        # Handle prerequisites conversion
        if "prerequisites" in update_data and update_data["prerequisites"]:
            update_data["prerequisites"] = [prereq.model_dump() for prereq in task_update.prerequisites]
        
        for field, value in update_data.items():
            setattr(task, field, value)
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Updated task: {task.name} (ID: {task.id})")
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}"
        )

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a task"""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        await db.delete(task)
        await db.commit()
        
        logger.info(f"Deleted task: {task.name} (ID: {task.id})")
        return {"message": f"Task {task_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )
