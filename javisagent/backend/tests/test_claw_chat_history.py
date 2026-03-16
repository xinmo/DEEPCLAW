import importlib.util
from pathlib import Path
import sys
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
TESTS_ROOT = BACKEND_ROOT / "tests"
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

fake_claw_service = types.ModuleType("src.services.claw")
fake_claw_service.create_claw_agent = lambda **_: None
fake_claw_service.validate_working_directory = lambda path: (True, None)
sys.modules.setdefault("src.services.claw", fake_claw_service)

from src.models.base import Base
from src.models.claw import ClawConversation

CHAT_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "chat.py"
CHAT_MODULE_NAME = "test_claw_chat_route_history"
chat_spec = importlib.util.spec_from_file_location(CHAT_MODULE_NAME, CHAT_MODULE_PATH)
chat_route = importlib.util.module_from_spec(chat_spec)
sys.modules[CHAT_MODULE_NAME] = chat_route
assert chat_spec.loader is not None
chat_spec.loader.exec_module(chat_route)
from test_claw_chat_stream import FakeAgent, build_fake_chunks, collect_events


def build_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


@pytest.mark.asyncio
async def test_chat_history_returns_process_items_in_order(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Weather",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_fake_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="北京的天气如何",
            conversation=conversation,
            db=db,
        )
    )

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")

    tool_ids = [tool["id"] for tool in assistant_message["tool_calls"]]
    assert tool_ids == ["call_shell_1", "call_plan_1", "call_task_1"]
    assert assistant_message["metadata"]["timeline"] == [
        {"kind": "text", "item_id": f"text:{assistant_message['id']}:1", "content": "我来帮你查询。"},
        {"kind": "shell", "item_id": "shell:call_shell_1", "tool_id": "call_shell_1"},
        {"kind": "planning", "item_id": "planning:call_plan_1", "tool_id": "call_plan_1"},
        {"kind": "subagent", "item_id": "subagent:call_task_1", "tool_id": "call_task_1"},
        {"kind": "text", "item_id": f"text:{assistant_message['id']}:2", "content": "北京当前 13C，北风 4 级。"},
    ]

    process_events = assistant_message["process_events"]
    assert [event["kind"] for event in process_events] == [
        "shell",
        "planning",
        "subagent",
    ]
    assert [event["sequence"] for event in process_events] == [1, 2, 3]

    shell_event = process_events[0]
    assert shell_event["status"] == "success"
    assert shell_event["data"]["command"] == "pwd"
    assert shell_event["data"]["stdout"] == "C:/repo\n"

    planning_event = process_events[1]
    assert planning_event["status"] == "in_progress"
    assert planning_event["data"]["todos"] == [
        {"content": "查询北京天气", "status": "completed"},
        {"content": "整理结论", "status": "in_progress"},
    ]

    subagent_event = process_events[2]
    assert subagent_event["status"] == "success"
    assert subagent_event["data"]["result"] == "子智能体已完成北京天气调研"
    assert "正在检索天气来源。" in subagent_event["data"]["transcript"]

    assert assistant_message["content"] == "我来帮你查询。北京当前 13C，北风 4 级。"
