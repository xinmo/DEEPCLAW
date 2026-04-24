from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskBase(BaseModel):
    name: str
    status: TaskStatus = TaskStatus.PENDING


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[TaskStatus] = None


class Task(TaskBase):
    id: str
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    file_id: str
    file_name: str


class ParseResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[str] = None
    error: Optional[str] = None


class ParseRequest(BaseModel):
    file_id: str
    file_name: str


class ExtractProgress(BaseModel):
    extracted_pages: int
    total_pages: Optional[int] = None
    status: str
