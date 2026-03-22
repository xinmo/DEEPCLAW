from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.models import get_db
from src.schemas.channels import (
    ChannelListResponse,
    QQChannelConfigPayload,
    QQChannelConfigResponse,
    QQChannelLogsResponse,
    QQChannelTestResponse,
)
from src.services.channels.registry import get_qq_channel_config, list_channel_summaries, save_qq_channel_config
from src.services.channels.runtime import channel_runtime

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("", response_model=ChannelListResponse)
async def list_channels(db: Session = Depends(get_db)) -> dict[str, object]:
    return {
        "channels": list_channel_summaries(
            db,
            runtime_statuses={"qq": channel_runtime.get_qq_runtime_status()},
        )
    }


@router.get("/qq", response_model=QQChannelConfigResponse)
async def get_qq_channel(db: Session = Depends(get_db)) -> dict[str, object]:
    detail = get_qq_channel_config(db)
    detail["runtime"] = channel_runtime.get_qq_runtime_status()
    return detail


@router.put("/qq", response_model=QQChannelConfigResponse)
async def update_qq_channel(
    payload: QQChannelConfigPayload,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    detail = save_qq_channel_config(db, payload.model_dump())
    await channel_runtime.refresh_from_db()
    detail["runtime"] = channel_runtime.get_qq_runtime_status()
    return detail


@router.post("/qq/test", response_model=QQChannelTestResponse)
async def test_qq_channel(payload: QQChannelConfigPayload) -> dict[str, object]:
    return await channel_runtime.test_qq_connection(payload.model_dump())


@router.get("/qq/logs", response_model=QQChannelLogsResponse)
async def get_qq_channel_logs(
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    return {
        "channel": "qq",
        "entries": channel_runtime.get_qq_logs(limit=limit),
    }
