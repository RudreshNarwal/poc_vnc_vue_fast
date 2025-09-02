from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.database import Base
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class Execution(Base):
    __tablename__ = "executions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    status = Column(String(50), nullable=False)  # pending, running, paused, completed, failed
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    screenshots = Column(JSON, nullable=True)  # List of screenshot paths
    logs = Column(JSON, nullable=True)  # Execution logs
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="executions")
    file = relationship("File", back_populates="executions")

# Pydantic models for API
class ExecutionCreate(BaseModel):
    task_id: int
    session_id: str

class ExecutionUpdate(BaseModel):
    status: Optional[str] = None
    current_step: Optional[int] = None
    error_message: Optional[str] = None
    screenshots: Optional[List[str]] = None
    logs: Optional[List[Dict[str, Any]]] = None

class ExecutionResponse(BaseModel):
    id: int
    session_id: str
    task_id: int
    status: str
    current_step: int
    total_steps: int
    file_id: Optional[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error_message: Optional[str]
    screenshots: Optional[List[str]]
    logs: Optional[List[Dict[str, Any]]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ExecutionStatus(BaseModel):
    session_id: str
    status: str
    message: str
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    screenshot: Optional[str] = None
    timestamp: datetime
