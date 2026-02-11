from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.sql import func
import enum
from .base import Base

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    file_id = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    mineru_task_id = Column(String, nullable=True)
    mineru_batch_id = Column(String, nullable=True)
    result = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
