import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

fake_claw_service = types.ModuleType("src.services.claw")
fake_claw_service.__path__ = []
fake_claw_service.create_claw_agent = lambda **_: None
fake_claw_service.validate_working_directory = lambda path: (True, None)
sys.modules["src.services.claw"] = fake_claw_service

fake_prompt_registry = types.ModuleType("src.services.claw.prompt_registry")
fake_prompt_registry.SYSTEM_PROMPT_ID = "system"
fake_prompt_registry.build_deep_agent_prompt_overrides = lambda *_args, **_kwargs: {}
fake_prompt_registry.get_current_prompt_bundle = lambda: {}
fake_prompt_registry.get_system_prompt_from_bundle = lambda bundle: bundle.get("system", "")
fake_prompt_registry.normalize_prompt_bundle = lambda bundle: dict(bundle or {})
sys.modules["src.services.claw.prompt_registry"] = fake_prompt_registry

fake_prompt_debug = types.ModuleType("src.services.claw.prompt_debug")
fake_prompt_debug.build_prompt_debug_snapshot = lambda **kwargs: {
    "captured_request": kwargs.get("captured_request", {})
}
sys.modules["src.services.claw.prompt_debug"] = fake_prompt_debug

fake_skill_registry = types.ModuleType("src.services.claw.skill_registry")
fake_skill_registry.extract_slash_skill_command = lambda message: (None, message)
fake_skill_registry.get_skill_detail = lambda *_args, **_kwargs: None
fake_skill_registry.resolve_skill_reference = lambda *_args, **_kwargs: None
sys.modules["src.services.claw.skill_registry"] = fake_skill_registry

from src.models.base import Base
from src.models.claw import ClawConversation

CHAT_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "chat.py"
CHAT_MODULE_NAME = "test_claw_chat_route_regressions"
chat_spec = importlib.util.spec_from_file_location(CHAT_MODULE_NAME, CHAT_MODULE_PATH)
chat_route = importlib.util.module_from_spec(chat_spec)
sys.modules[CHAT_MODULE_NAME] = chat_route
assert chat_spec.loader is not None
chat_spec.loader.exec_module(chat_route)


class FakeAgent:
    def __init__(self, chunks):
        self._chunks = chunks

    async def astream(self, input_data, **kwargs):
        del input_data, kwargs
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


def build_task_child_tool_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_task_child_1",
                            "name": "task",
                            "args": {"description": "Inspect repository layout"},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            ("worker",),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_glob_child_1",
                            "name": "glob",
                            "args": {"pattern": "**/*.py"},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            ("worker",),
            "messages",
            (
                ToolMessage(
                    content=["src/main.py", "src/routes/claw/chat.py"],
                    tool_call_id="call_glob_child_1",
                    name="glob",
                ),
                {},
            ),
        ),
        (
            ("worker",),
            "messages",
            (
                AIMessage(content=[{"type": "text", "text": "Indexed project files."}]),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content="Subagent finished repository inspection.",
                    tool_call_id="call_task_child_1",
                    name="task",
                ),
                {},
            ),
        ),
        (
            ("worker",),
            "messages",
            (
                AIMessage(content=[{"type": "text", "text": "Final note after completion."}]),
                {},
            ),
        ),
    ]


def build_task_child_tool_tool_namespace_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_task_namespaced_1",
                            "name": "task",
                            "args": {"description": "Inspect repository layout"},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            (("worker", "tools:call_glob_child_1"),),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_glob_child_1",
                            "name": "glob",
                            "args": {"pattern": "**/*.py"},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            (("worker", "tools:call_glob_child_1"),),
            "messages",
            (
                ToolMessage(
                    content=["src/main.py", "src/routes/claw/chat.py"],
                    tool_call_id="call_glob_child_1",
                    name="glob",
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content="Subagent finished repository inspection.",
                    tool_call_id="call_task_namespaced_1",
                    name="task",
                ),
                {},
            ),
        ),
    ]


def build_updates_only_planning_timeline_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(content=[{"type": "text", "text": "Starting investigation."}]),
                {},
            ),
        ),
        (
            (),
            "updates",
            {
                "planner": {
                    "todos": [
                        {"content": "Inspect backend", "status": "completed"},
                        {"content": "Inspect frontend", "status": "in_progress"},
                    ]
                }
            },
        ),
        (
            (),
            "messages",
            (
                AIMessage(content=[{"type": "text", "text": "Investigation finished."}]),
                {},
            ),
        ),
    ]


def build_updates_embedded_subagent_child_tool_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_task_update_child_1",
                            "name": "task",
                            "args": {"description": "Inspect repository layout"},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            ("worker",),
            "updates",
            {
                "model": {
                    "messages": [
                        AIMessage(
                            content=[
                                {
                                    "type": "tool_call",
                                    "id": "call_glob_update_child_1",
                                    "name": "glob",
                                    "args": {"pattern": "**/*.py"},
                                }
                            ]
                        )
                    ]
                },
                "planner": {
                    "todos": [
                        {"content": "Inspect backend", "status": "completed"},
                        {"content": "Inspect frontend", "status": "in_progress"},
                    ]
                },
            },
        ),
        (
            ("worker",),
            "updates",
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=["src/main.py", "src/routes/claw/chat.py"],
                            tool_call_id="call_glob_update_child_1",
                            name="glob",
                        )
                    ]
                }
            },
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content="Subagent report complete.",
                    tool_call_id="call_task_update_child_1",
                    name="task",
                ),
                {},
            ),
        ),
    ]


@pytest.mark.asyncio
async def test_subagent_child_tools_are_streamed_and_persisted(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Task child tools",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_task_child_tool_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="Inspect the repository deeply",
            conversation=conversation,
            db=db,
        )
    )

    child_tool_updates = [
        event
        for event in events
        if event["type"] == "subagent_updated" and event.get("child_tools")
    ]
    assert child_tool_updates[0]["child_tools"][0]["tool_name"] == "glob"
    assert child_tool_updates[0]["child_tools"][0]["status"] == "running"
    completed_child_tool_update = next(
        event
        for event in child_tool_updates
        if event["child_tools"][0]["status"] == "success"
        and event["child_tools"][0].get("tool_output") is not None
    )
    assert completed_child_tool_update["child_tools"][0]["tool_output"] == [
        "src/main.py",
        "src/routes/claw/chat.py",
    ]

    trailing_update = events[-2]
    assert trailing_update["type"] == "subagent_updated"
    assert trailing_update["status"] == "success"
    assert "Final note after completion." in trailing_update["transcript"]

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    assert [tool_call["tool_name"] for tool_call in assistant_message["tool_calls"]] == ["task"]

    subagent_event = next(
        event for event in assistant_message["process_events"] if event["kind"] == "subagent"
    )
    assert subagent_event["status"] == "success"
    assert subagent_event["data"]["child_tools"][0]["tool_name"] == "glob"
    assert subagent_event["data"]["child_tools"][0]["tool_output"] == [
        "src/main.py",
        "src/routes/claw/chat.py",
    ]


@pytest.mark.asyncio
async def test_subagent_child_tools_embedded_in_updates_are_persisted(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Updates embedded child tools",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_updates_embedded_subagent_child_tool_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="Inspect the repository deeply",
            conversation=conversation,
            db=db,
        )
    )

    child_tool_updates = [
        event
        for event in events
        if event["type"] == "subagent_updated" and event.get("child_tools")
    ]
    assert child_tool_updates
    latest_child_tools = child_tool_updates[-1]["child_tools"]
    child_tool_names = {child_tool["tool_name"] for child_tool in latest_child_tools}
    assert child_tool_names == {"glob", "write_todos"}
    glob_child_tool = next(
        child_tool for child_tool in latest_child_tools if child_tool["tool_name"] == "glob"
    )
    assert glob_child_tool["status"] == "success"
    assert glob_child_tool["tool_output"] == [
        "src/main.py",
        "src/routes/claw/chat.py",
    ]

    planning_child_tool = next(
        child_tool for child_tool in latest_child_tools if child_tool["tool_name"] == "write_todos"
    )
    assert planning_child_tool["status"] == "running"
    assert len(planning_child_tool["tool_output"]) == 2

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    assert all(
        process_event["kind"] != "planning" for process_event in assistant_message["process_events"]
    )

    subagent_event = next(
        event for event in assistant_message["process_events"] if event["kind"] == "subagent"
    )
    persisted_child_tool_names = {
        child_tool["tool_name"] for child_tool in subagent_event["data"]["child_tools"]
    }
    assert persisted_child_tool_names == {"glob", "write_todos"}


@pytest.mark.asyncio
async def test_subagent_child_tools_are_bound_from_tool_namespaces(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Namespaced child tools",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_task_child_tool_tool_namespace_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="Inspect the repository deeply",
            conversation=conversation,
            db=db,
        )
    )

    child_tool_updates = [
        event
        for event in events
        if event["type"] == "subagent_updated" and event.get("child_tools")
    ]
    assert child_tool_updates
    assert child_tool_updates[-1]["child_tools"][0]["tool_name"] == "glob"
    assert child_tool_updates[-1]["child_tools"][0]["status"] == "success"

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    subagent_event = next(
        event for event in assistant_message["process_events"] if event["kind"] == "subagent"
    )
    assert subagent_event["data"]["child_tools"][0]["tool_name"] == "glob"
    assert subagent_event["data"]["child_tools"][0]["tool_output"] == [
        "src/main.py",
        "src/routes/claw/chat.py",
    ]


@pytest.mark.asyncio
async def test_updates_only_planning_is_persisted_in_timeline_order(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Updates planning timeline",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_updates_only_planning_timeline_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="Investigate the repository",
            conversation=conversation,
            db=db,
        )
    )

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    timeline = assistant_message["metadata"]["timeline"]

    assert [entry["kind"] for entry in timeline] == ["text", "planning", "text"]
    assert timeline[1]["item_id"].startswith("planning:")


@pytest.mark.asyncio
async def test_planning_status_merges_latest_tool_output(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Planning completion",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(
        [
            (
                (),
                "messages",
                (
                    AIMessage(
                        content=[
                            {
                                "type": "tool_call",
                                "id": "call_plan_merge_1",
                                "name": "write_todos",
                                "args": {
                                    "todos": [
                                        {"content": "Inspect backend", "status": "in_progress"},
                                        {"content": "Inspect frontend", "status": "pending"},
                                    ]
                                },
                            }
                        ]
                    ),
                    {},
                ),
            ),
            (
                (),
                "updates",
                {
                    "planner": {
                        "todos": [
                            {"content": "Inspect backend", "status": "completed"},
                        ]
                    }
                },
            ),
            (
                (),
                "messages",
                (
                    ToolMessage(
                        content=json.dumps(
                            [
                                {"content": "Inspect backend", "status": "completed"},
                                {"content": "Inspect frontend", "status": "completed"},
                            ]
                        ),
                        tool_call_id="call_plan_merge_1",
                        name="write_todos",
                    ),
                    {},
                ),
            ),
        ]
    )
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="Plan the investigation",
            conversation=conversation,
            db=db,
        )
    )

    planning_updates = [event for event in events if event["type"] == "planning_updated"]
    assert planning_updates[-1]["status"] == "completed"
    assert all(todo["status"] == "completed" for todo in planning_updates[-1]["todos"])

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    planning_event = next(
        event for event in assistant_message["process_events"] if event["kind"] == "planning"
    )
    assert planning_event["status"] == "completed"
    assert all(todo["status"] == "completed" for todo in planning_event["data"]["todos"])
