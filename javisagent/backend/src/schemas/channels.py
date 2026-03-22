from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChannelRuntimeStatus(BaseModel):
    installed: bool
    available: bool
    running: bool
    state: str
    message: str
    updated_at: str | None = None


class ChannelSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    label: str
    enabled: bool
    configured: bool
    status: str
    status_message: str
    updated_at: str | None = None


class ChannelListResponse(BaseModel):
    channels: list[ChannelSummary]


class QQChannelConfigPayload(BaseModel):
    enabled: bool = False
    app_id: str = ""
    secret: str = ""
    allow_from: list[str] = Field(default_factory=list)


class QQChannelConfigResponse(BaseModel):
    name: str
    label: str
    enabled: bool
    configured: bool
    config: QQChannelConfigPayload
    validation_errors: list[str] = Field(default_factory=list)
    runtime: ChannelRuntimeStatus
    created_at: str | None = None
    updated_at: str | None = None


class ChannelLogEntry(BaseModel):
    timestamp: str
    level: str
    source: str
    message: str


class ChannelConnectivityCheck(BaseModel):
    key: str
    label: str
    status: Literal["success", "warning", "error", "info"]
    message: str


class QQChannelTestResponse(BaseModel):
    success: bool
    state: Literal["success", "warning", "error"]
    message: str
    tested_at: str
    checks: list[ChannelConnectivityCheck] = Field(default_factory=list)
    runtime: ChannelRuntimeStatus


class QQChannelLogsResponse(BaseModel):
    channel: str
    entries: list[ChannelLogEntry] = Field(default_factory=list)
