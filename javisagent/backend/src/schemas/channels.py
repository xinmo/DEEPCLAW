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
