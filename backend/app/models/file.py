from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.database import Base
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, unique=True)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    file_type = Column(String(50), nullable=False)  # e.g., 'csv', 'xlsx'
    status = Column(String(50), default="uploaded") # uploaded, validated, error
    validation_results = Column(JSON, nullable=True)
    
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="files")
    executions = relationship("Execution", back_populates="file")

# Pydantic models for API
class FileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    status: str
    validation_results: Optional[Dict[str, Any]]
    task_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
