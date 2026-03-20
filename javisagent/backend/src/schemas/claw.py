from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str | None = "New Conversation"
    working_directory: str
    llm_model: str = "claude-opus-4-6"


class ConversationUpdate(BaseModel):
    title: str | None = None
    working_directory: str | None = None
    llm_model: str | None = None


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    working_directory: str
    llm_model: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str | list = Field(...)
    selected_skill: str | None = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str | list) -> str | list:
        if isinstance(v, str) and not v.strip():
            raise ValueError("content must not be empty")
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("content list must not be empty")
        return v


class ToolCallInfo(BaseModel):
    id: str
    tool_name: str
    tool_input: Any
    tool_output: Any | None = None
    status: str
    duration: float | None = None
    error: str | None = None


class ProcessEventResponse(BaseModel):
    id: str
    kind: str
    title: str
    status: str
    sequence: int
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)
    process_events: list[ProcessEventResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DirectoryValidation(BaseModel):
    path: str


class DirectoryValidationResponse(BaseModel):
    valid: bool
    reason: str | None = None


class ModelInfo(BaseModel):
    model_id: str
    name: str
    provider: str


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
