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

fake_claw_service = types.ModuleType("src.services.claw")
fake_claw_service.create_claw_agent = lambda **_: None
fake_claw_service.validate_working_directory = lambda path: (True, None)
sys.modules.setdefault("src.services.claw", fake_claw_service)

from src.models.base import Base
from src.models.claw import ClawConversation, ClawMessage, MessageRole

CHAT_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "chat.py"
CHAT_MODULE_NAME = "test_claw_chat_duplicate_prompt_cache_route"
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
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session_local()


@pytest.mark.asyncio
async def test_chat_stream_reuses_recent_identical_question_without_agent(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Weather cache",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    db.add(
        ClawMessage(
            conversation_id=str(conversation.id),
            role=MessageRole.USER,
            content="北京的天气是什么",
        )
    )
    db.add(
        ClawMessage(
            conversation_id=str(conversation.id),
            role=MessageRole.ASSISTANT,
            content="北京今天晴，0°C 到 13°C。",
            extra_data={"tool_call_count": 1},
        )
    )
    db.commit()

    fake_agent = FakeAgent(build_fake_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="北京的天气是什么",
            conversation=conversation,
            db=db,
        )
    )

    assert [event["type"] for event in events] == ["text", "done"]
    assert events[0]["content"] == "北京今天晴，0°C 到 13°C。"
    assert fake_agent.calls == []

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_messages = [message for message in messages if message["role"] == "assistant"]
    latest_assistant = assistant_messages[-1]
    assert latest_assistant["content"] == "北京今天晴，0°C 到 13°C。"
    assert latest_assistant["metadata"]["cache_hit"] is True
    assert latest_assistant["tool_calls"] == []
