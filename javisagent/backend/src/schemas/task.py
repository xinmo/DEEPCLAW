from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskBase(BaseModel):
    name: str
    file_id: Optional[str] = None
    file_name: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    result: Optional[str] = None

class Task(TaskBase):
    id: str
    status: TaskStatus
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    file_id: str
    file_name: str

class ParseResponse(BaseModel):
    task_id: str

class ParseRequest(BaseModel):
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    url: Optional[str] = None

class ExtractProgress(BaseModel):
    extracted_pages: int
    total_pages: int

class TaskStatusResponse(BaseModel):
    task: Task
    result: Optional[str] = None
    progress: Optional[ExtractProgress] = None
