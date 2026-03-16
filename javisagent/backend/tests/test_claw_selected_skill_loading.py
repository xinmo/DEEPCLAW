import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

fake_claw_service = types.ModuleType("src.services.claw")
fake_claw_service.create_claw_agent = lambda **_: None
fake_claw_service.validate_working_directory = lambda path: (True, None)
fake_claw_service.__path__ = [str(BACKEND_ROOT / "src" / "services" / "claw")]
sys.modules.setdefault("src.services.claw", fake_claw_service)

from src.models.base import Base
from src.models.claw import ClawConversation, ClawMessage, MessageRole

CHAT_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "chat.py"
CHAT_MODULE_NAME = "test_claw_selected_skill_loading_route"
chat_spec = importlib.util.spec_from_file_location(CHAT_MODULE_NAME, CHAT_MODULE_PATH)
chat_route = importlib.util.module_from_spec(chat_spec)
sys.modules[CHAT_MODULE_NAME] = chat_route
assert chat_spec.loader is not None
chat_spec.loader.exec_module(chat_route)


class FakeAgent:
    def __init__(self, chunks):
        self._chunks = chunks
        self.calls = []

    async def astream(self, input_data, **kwargs):
        self.calls.append({"input_data": input_data, **kwargs})
        for chunk in self._chunks:
            yield chunk


def build_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session_local()


def parse_sse_payload(raw_event: str) -> dict:
    assert raw_event.startswith("data: ")
    return json.loads(raw_event[len("data: ") :])


async def collect_events(generator):
    events = []
    async for raw_event in generator:
        events.append(parse_sse_payload(raw_event))
    return events


def _build_skill_detail(content: str) -> dict[str, object]:
    return {
        "name": "brainstorming-0.1.0",
        "declared_name": "brainstorming",
        "description": "Use before implementation.",
        "aliases": ["brainstorming", "brainstorming-0.1.0"],
        "skill_file_path": "C:/Users/WLX/.agents/skills/brainstorming-0.1.0/SKILL.md",
        "path": "C:/Users/WLX/.agents/skills/brainstorming-0.1.0",
        "content": content,
    }


def _stub_prompt_bundle(monkeypatch) -> None:
    monkeypatch.setattr(
        chat_route,
        "get_current_prompt_bundle",
        lambda: {"system_prompt": "Workspace: {working_directory}"},
    )
    monkeypatch.setattr(
        chat_route,
        "get_system_prompt_from_bundle",
        lambda bundle: bundle.get("system_prompt"),
    )
    monkeypatch.setattr(
        chat_route,
        "build_deep_agent_prompt_overrides",
        lambda bundle: {},
    )


@pytest.mark.asyncio
async def test_selected_skill_is_preloaded_into_turn_instruction(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Selected skill",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    selected_skill = _build_skill_detail(
        "---\nname: brainstorming\ndescription: Use before implementation.\n---\n\n# Brainstorming\n\nAlways explore requirements before coding.\n"
    )

    monkeypatch.setattr(
        chat_route,
        "resolve_skill_reference",
        lambda reference, enabled_only=True: {
            "name": "brainstorming-0.1.0",
            "aliases": ["brainstorming", "brainstorming-0.1.0"],
        },
    )
    monkeypatch.setattr(chat_route, "get_skill_detail", lambda name: selected_skill)
    _stub_prompt_bundle(monkeypatch)

    captured_kwargs = {}
    fake_agent = FakeAgent(
        [
            (
                (),
                "messages",
                (
                    AIMessage(content=[{"type": "text", "text": "skill loaded"}]),
                    {},
                ),
            ),
        ]
    )

    def fake_create_claw_agent(**kwargs):
        captured_kwargs.update(kwargs)
        return fake_agent

    monkeypatch.setattr(chat_route, "create_claw_agent", fake_create_claw_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="help me design a login flow",
            conversation=conversation,
            db=db,
            selected_skill_name="brainstorming-0.1.0",
        )
    )

    assert [event["type"] for event in events] == ["text", "done"]
    assert "The full contents of `C:/Users/WLX/.agents/skills/brainstorming-0.1.0/SKILL.md` are preloaded below." in captured_kwargs["turn_instruction"]
    assert "<preloaded_skill_file>" in captured_kwargs["turn_instruction"]
    assert "# Brainstorming" in captured_kwargs["turn_instruction"]
    assert "Always explore requirements before coding." in captured_kwargs["turn_instruction"]

    messages = await chat_route.get_messages(conversation.id, db=db)
    user_message = next(message for message in messages if message["role"] == "user")
    assert user_message["metadata"]["selected_skill"] == "brainstorming-0.1.0"
    assert user_message["metadata"]["selected_skill_alias"] == "brainstorming"
    assert user_message["metadata"]["selected_skill_file_path"] == selected_skill["skill_file_path"]
    assert user_message["metadata"]["selected_skill_preloaded"] is True
    assert isinstance(user_message["metadata"]["selected_skill_revision"], str)
    assert len(user_message["metadata"]["selected_skill_revision"]) == 16


@pytest.mark.asyncio
async def test_selected_skill_revision_busts_duplicate_reply_cache(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Selected skill cache",
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
            content="help me design a login flow",
            extra_data={
                "selected_skill": "brainstorming-0.1.0",
                "selected_skill_revision": "oldrevision00001",
            },
        )
    )
    db.add(
        ClawMessage(
            conversation_id=str(conversation.id),
            role=MessageRole.ASSISTANT,
            content="old cached answer",
            extra_data={"tool_call_count": 1},
        )
    )
    db.commit()

    monkeypatch.setattr(
        chat_route,
        "resolve_skill_reference",
        lambda reference, enabled_only=True: {
            "name": "brainstorming-0.1.0",
            "aliases": ["brainstorming", "brainstorming-0.1.0"],
        },
    )
    monkeypatch.setattr(
        chat_route,
        "get_skill_detail",
        lambda name: _build_skill_detail(
            "---\nname: brainstorming\ndescription: Use before implementation.\n---\n\n# Brainstorming\n\nA changed instruction body.\n"
        ),
    )
    _stub_prompt_bundle(monkeypatch)

    fake_agent = FakeAgent(
        [
            (
                (),
                "messages",
                (
                    AIMessage(content=[{"type": "text", "text": "fresh answer"}]),
                    {},
                ),
            ),
        ]
    )
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="help me design a login flow",
            conversation=conversation,
            db=db,
            selected_skill_name="brainstorming-0.1.0",
        )
    )

    assert [event["type"] for event in events] == ["text", "done"]
    assert fake_agent.calls != []

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_messages = [message for message in messages if message["role"] == "assistant"]
    latest_assistant = assistant_messages[-1]
    assert latest_assistant["content"] == "fresh answer"
    assert latest_assistant["metadata"].get("cache_hit") is None
