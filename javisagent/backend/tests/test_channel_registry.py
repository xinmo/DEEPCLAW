import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.models.base import Base
from src.services.channels.registry import (
    QQ_CHANNEL_NAME,
    get_qq_channel_config,
    list_channel_summaries,
    save_qq_channel_config,
)


def _make_session():
    sqlite_path = BACKEND_ROOT / "tests" / ".tmp" / f"channels-{uuid.uuid4().hex}.db"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{sqlite_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def test_channel_registry_returns_default_qq_config():
    db = _make_session()
    try:
        detail = get_qq_channel_config(db)
    finally:
        db.close()

    assert detail["name"] == QQ_CHANNEL_NAME
    assert detail["enabled"] is False
    assert detail["configured"] is False
    assert detail["config"]["app_id"] == ""
    assert detail["config"]["secret"] == ""
    assert detail["config"]["allow_from"] == []


def test_channel_registry_normalizes_and_summarizes_qq_config():
    db = _make_session()
    try:
        detail = save_qq_channel_config(
            db,
            {
                "enabled": True,
                "app_id": "  app-123  ",
                "secret": " secret-456 ",
                "allow_from": [" user-a ", "", "user-b", "user-a"],
            },
        )
        summaries = list_channel_summaries(
            db,
            runtime_statuses={
                "qq": {
                    "state": "running",
                    "message": "QQ 渠道运行中。",
                }
            },
        )
    finally:
        db.close()

    assert detail["enabled"] is True
    assert detail["configured"] is True
    assert detail["validation_errors"] == []
    assert detail["config"]["app_id"] == "app-123"
    assert detail["config"]["secret"] == "secret-456"
    assert detail["config"]["allow_from"] == ["user-a", "user-b"]
    assert summaries == [
        {
            "name": "qq",
            "label": "QQ",
            "enabled": True,
            "configured": True,
            "status": "running",
            "status_message": "QQ 渠道运行中。",
            "updated_at": detail["updated_at"],
        }
    ]
