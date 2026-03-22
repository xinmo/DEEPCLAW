import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import src.services.channels.runtime as runtime_module


def test_runtime_returns_latest_logs():
    manager = runtime_module.ChannelRuntimeManager()

    manager._record_log("info", "first log", source="test.qq")
    manager._record_log("error", "second log", source="test.qq")

    entries = manager.get_qq_logs(limit=1)

    assert len(entries) == 1
    assert entries[0]["level"] == "ERROR"
    assert entries[0]["message"] == "second log"
    assert entries[0]["source"] == "test.qq"


@pytest.mark.asyncio
async def test_connection_check_requires_complete_config():
    manager = runtime_module.ChannelRuntimeManager()

    result = await manager.test_qq_connection(
        {
            "enabled": False,
            "app_id": "",
            "secret": "",
            "allow_from": [],
        }
    )

    assert result["success"] is False
    assert result["state"] == "error"
    assert result["message"] == "测试连接前需要先填写完整的 App ID 和 App Secret。"
    assert result["checks"][0]["key"] == "configuration"
    assert result["checks"][0]["status"] == "error"


@pytest.mark.asyncio
async def test_connection_check_reports_missing_sdk(monkeypatch):
    monkeypatch.setattr(runtime_module, "NANOBOT_AVAILABLE", True)
    monkeypatch.setattr(runtime_module, "QQ_AVAILABLE", False)
    monkeypatch.setattr(runtime_module, "QQChannel", object())
    monkeypatch.setattr(runtime_module, "QQConfig", object())
    monkeypatch.setattr(runtime_module, "MessageBus", object())

    manager = runtime_module.ChannelRuntimeManager()
    result = await manager.test_qq_connection(
        {
            "enabled": False,
            "app_id": "app-123",
            "secret": "secret-456",
            "allow_from": [],
        }
    )

    assert result["success"] is False
    assert result["state"] == "error"
    assert result["message"] == "当前环境缺少 qq-botpy，无法执行测试连接。"
    assert any(check["key"] == "sdk" and check["status"] == "error" for check in result["checks"])
