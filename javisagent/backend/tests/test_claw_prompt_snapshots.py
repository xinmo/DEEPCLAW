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
sys.modules["src.services.claw"] = fake_claw_service

from src.models.base import Base
from src.models.claw import ClawConversation, ClawConversationPromptSnapshot
from src.schemas.claw import ConversationCreate

PROMPT_REGISTRY_MODULE_PATH = BACKEND_ROOT / "src" / "services" / "claw" / "prompt_registry.py"
PROMPT_REGISTRY_MODULE_NAME = "src.services.claw.prompt_registry"
prompt_registry_spec = importlib.util.spec_from_file_location(
    PROMPT_REGISTRY_MODULE_NAME,
    PROMPT_REGISTRY_MODULE_PATH,
)
prompt_registry_module = importlib.util.module_from_spec(prompt_registry_spec)
sys.modules[PROMPT_REGISTRY_MODULE_NAME] = prompt_registry_module
assert prompt_registry_spec.loader is not None
prompt_registry_spec.loader.exec_module(prompt_registry_module)

CONVERSATIONS_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "conversations.py"
CONVERSATIONS_MODULE_NAME = "test_claw_conversations_route"
conversations_spec = importlib.util.spec_from_file_location(
    CONVERSATIONS_MODULE_NAME,
    CONVERSATIONS_MODULE_PATH,
)
conversations_route = importlib.util.module_from_spec(conversations_spec)
sys.modules[CONVERSATIONS_MODULE_NAME] = conversations_route
assert conversations_spec.loader is not None
conversations_spec.loader.exec_module(conversations_route)

CHAT_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "chat.py"
CHAT_MODULE_NAME = "test_claw_chat_prompt_snapshot_route"
chat_spec = importlib.util.spec_from_file_location(CHAT_MODULE_NAME, CHAT_MODULE_PATH)
chat_route = importlib.util.module_from_spec(chat_spec)
sys.modules[CHAT_MODULE_NAME] = chat_route
assert chat_spec.loader is not None
chat_spec.loader.exec_module(chat_route)


PROMPT_BUNDLE = {
    "system_prompt": "System prompt for {working_directory}",
    "base_agent_prompt": "Base prompt snapshot",
    "todo_system_prompt": "Todo prompt snapshot",
    "filesystem_system_prompt": "Filesystem prompt snapshot",
    "task_system_prompt": "Task prompt snapshot",
    "general_purpose_subagent_prompt": "General-purpose subagent prompt snapshot",
    "summarization_summary_prompt": "Summarization prompt snapshot",
    "memory_system_prompt": "Memory prompt snapshot",
    "skills_system_prompt": "Skills prompt snapshot",
    "summarization_tool_system_prompt": "Summarization tool prompt snapshot",
}


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


@pytest.mark.asyncio
async def test_create_conversation_saves_prompt_snapshot(monkeypatch):
    db = build_session()
    monkeypatch.setattr(
        conversations_route,
        "get_current_prompt_bundle",
        lambda: PROMPT_BUNDLE.copy(),
    )

    conversation = await conversations_route.create_conversation(
        ConversationCreate(
            title="Snapshot conversation",
            working_directory=str(Path.cwd()),
            llm_model="deepseek-chat",
        ),
        db=db,
    )

    snapshot = (
        db.query(ClawConversationPromptSnapshot)
        .filter_by(conversation_id=str(conversation.id))
        .first()
    )
    assert snapshot is not None
    assert snapshot.prompt_bundle == PROMPT_BUNDLE
    assert conversation.system_prompt == PROMPT_BUNDLE["system_prompt"]


@pytest.mark.asyncio
async def test_chat_stream_backfills_missing_prompt_snapshot(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Legacy conversation",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
        system_prompt="Legacy system prompt for {working_directory}",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    monkeypatch.setattr(chat_route, "get_current_prompt_bundle", lambda: PROMPT_BUNDLE.copy())
    monkeypatch.setattr(
        chat_route,
        "get_system_prompt_from_bundle",
        lambda bundle: bundle.get("system_prompt"),
    )
    monkeypatch.setattr(
        chat_route,
        "build_deep_agent_prompt_overrides",
        lambda bundle: {"base_agent_prompt": bundle["base_agent_prompt"]},
    )

    captured_kwargs = {}
    fake_agent = FakeAgent(
        [
            (
                (),
                "messages",
                (
                    AIMessage(content=[{"type": "text", "text": "snapshot ok"}]),
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
            user_message="hello",
            conversation=conversation,
            db=db,
        )
    )

    snapshot = (
        db.query(ClawConversationPromptSnapshot)
        .filter_by(conversation_id=str(conversation.id))
        .first()
    )
    assert snapshot is not None
    assert snapshot.prompt_bundle["system_prompt"] == conversation.system_prompt
    assert snapshot.prompt_bundle["base_agent_prompt"] == PROMPT_BUNDLE["base_agent_prompt"]
    assert captured_kwargs["custom_system_prompt"] == conversation.system_prompt
    assert captured_kwargs["prompt_overrides"] == {
        "base_agent_prompt": PROMPT_BUNDLE["base_agent_prompt"]
    }
    assert [event["type"] for event in events] == ["text", "done"]
