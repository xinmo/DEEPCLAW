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
fake_claw_service.__path__ = []  # mark as package for submodule imports
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

fake_skill_registry = types.ModuleType("src.services.claw.skill_registry")
fake_skill_registry.extract_slash_skill_command = lambda message: (None, message)
fake_skill_registry.get_skill_detail = lambda *_args, **_kwargs: None
fake_skill_registry.resolve_skill_reference = lambda *_args, **_kwargs: None
sys.modules["src.services.claw.skill_registry"] = fake_skill_registry

from src.models.base import Base
from src.models.claw import ClawConversation, ClawMessage, MessageRole

CHAT_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "chat.py"
CHAT_MODULE_NAME = "test_claw_chat_route"
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
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def build_file_session_factory(db_path: Path):
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session_local


def parse_sse_payload(raw_event: str) -> dict:
    assert raw_event.startswith("data: ")
    return json.loads(raw_event[len("data: ") :])


async def collect_events(generator):
    events = []
    async for raw_event in generator:
        events.append(parse_sse_payload(raw_event))
    return events


def test_extract_shell_payload_splits_combined_output():
    message = ToolMessage(
        content="[stderr] 系统找不到指定的路径。\n\nExit code: 255\n[Command failed with exit code 255]",
        tool_call_id="call_shell_1",
        name="shell",
    )

    payload = chat_route._extract_shell_payload(message, {"command": "dir missing-folder"})

    assert payload["command"] == "dir missing-folder"
    assert payload["stdout"] == ""
    assert payload["stderr"] == "系统找不到指定的路径。"
    assert payload["exit_code"] == 255


def build_fake_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(content=[{"type": "text", "text": "我来帮你查询。"}]),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call_chunk",
                            "id": "call_shell_1",
                            "name": "shell",
                            "args": '{"command":"pw',
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_shell_1",
                            "name": "shell",
                            "args": {"command": "pwd"},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_plan_1",
                            "name": "write_todos",
                            "args": {
                                "todos": [
                                    {
                                        "content": "查询北京天气",
                                        "status": "in_progress",
                                    }
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
                        {"content": "查询北京天气", "status": "completed"},
                        {"content": "整理结论", "status": "in_progress"},
                    ]
                }
            },
        ),
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_task_1",
                            "name": "task",
                            "args": {"description": "调研北京天气并总结"},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            ("subagent:weather",),
            "messages",
            (
                AIMessage(
                    content=[{"type": "text", "text": "正在检索天气来源。"}]
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content="C:/repo",
                    tool_call_id="call_shell_1",
                    name="shell",
                    artifact={
                        "command": "pwd",
                        "stdout": "C:/repo\n",
                        "stderr": "",
                        "exit_code": 0,
                    },
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content='[{"content":"查询北京天气","status":"completed"}]',
                    tool_call_id="call_plan_1",
                    name="write_todos",
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content="子智能体已完成北京天气调研",
                    tool_call_id="call_task_1",
                    name="task",
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[{"type": "text", "text": "北京当前 13C，北风 4 级。"}]
                ),
                {},
            ),
        ),
    ]


def build_tool_namespace_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_glob_1",
                            "name": "glob",
                            "args": {"pattern": "**/*.py"},
                        }
                    ],
                ),
                {},
            ),
        ),
        (
            ("tools:call_glob_1",),
            "messages",
            (
                AIMessage(content=[{"type": "text", "text": "internal tool namespace"}]),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content=["src/main.py", "src/routes/claw/chat.py"],
                    tool_call_id="call_glob_1",
                    name="glob",
                ),
                {},
            ),
        ),
    ]


def build_glob_late_args_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_glob_late_1",
                            "name": "glob",
                            "args": {},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_glob_late_1",
                            "name": "glob",
                            "args": {"pattern": "**/*.ts", "path": "src"},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content=["src/server.ts"],
                    tool_call_id="call_glob_late_1",
                    name="glob",
                ),
                {},
            ),
        ),
    ]


def build_task_internal_namespace_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_task_1",
                            "name": "task",
                            "args": {
                                "description": "搜索项目目录",
                                "subagent_type": "general-purpose",
                            },
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            ("worker",),
            "updates",
            {"worker_state": {"step": "indexing"}},
        ),
        (
            (("tools:call_internal_1",),),
            "messages",
            (
                AIMessage(content=[{"type": "text", "text": "这是一条内部工具命名空间消息。"}]),
                {},
            ),
        ),
        (
            ("worker",),
            "messages",
            (
                AIMessage(content=[{"type": "text", "text": "正在整理搜索结果。"}]),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content="搜索完成",
                    tool_call_id="call_task_1",
                    name="task",
                ),
                {},
            ),
        ),
    ]


def build_read_file_fallback_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_read_1",
                            "name": "read_file",
                            "args": {"offset": 100, "limit": 50},
                        }
                    ]
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content="   101\tconst foo = 1;\n   102\tconst bar = 2;",
                    tool_call_id="call_read_1",
                    name="read_file",
                    additional_kwargs={"read_file_path": "/src/pages/App.tsx"},
                ),
                {},
            ),
        ),
    ]


def build_read_file_chunk_preservation_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call_chunk",
                            "id": "call_read_chunk_1",
                            "args": '{"file_path":"/src/main.tsx","offset":0,"limit":100}',
                        },
                        {
                            "type": "tool_call",
                            "id": "call_read_chunk_1",
                            "name": "read_file",
                            "args": {},
                        },
                    ]
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content="     1\timport React from 'react';",
                    tool_call_id="call_read_chunk_1",
                    name="read_file",
                ),
                {},
            ),
        ),
    ]


@pytest.mark.asyncio
async def test_chat_stream_emits_cli_parity_events(monkeypatch):
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

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="北京的天气如何",
            conversation=conversation,
            db=db,
        )
    )

    event_types = [event["type"] for event in events]
    assert event_types == [
        "text",
        "tool_call_delta",
        "tool_call_started",
        "shell_started",
        "tool_call_started",
        "planning_started",
        "planning_updated",
        "tool_call_started",
        "subagent_started",
        "subagent_updated",
        "tool_call_completed",
        "shell_output",
        "shell_completed",
        "tool_call_completed",
        "planning_updated",
        "tool_call_completed",
        "subagent_completed",
        "text",
        "done",
    ]

    stream_call = fake_agent.calls[0]
    assert stream_call["stream_mode"] == ["messages", "updates"]
    assert stream_call["subgraphs"] is True
    assert stream_call["config"] == {
        "configurable": {"thread_id": str(conversation.id)}
    }

    shell_started = next(event for event in events if event["type"] == "shell_started")
    assert shell_started["tool_id"] == "call_shell_1"
    assert shell_started["command"] == "pwd"
    assert shell_started["tool_input"] == {"command": "pwd"}

    subagent_started = next(
        event for event in events if event["type"] == "subagent_started"
    )
    assert subagent_started["tool_id"] == "call_task_1"
    assert subagent_started["item_id"].startswith("subagent:")

    shell_output = next(event for event in events if event["type"] == "shell_output")
    assert shell_output["output"] == "C:/repo\n"

    assert events[-1] == {"type": "done"}


@pytest.mark.asyncio
async def test_chat_stream_uses_message_tool_calls_and_ignores_tool_namespaces(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Glob",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_tool_namespace_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="找一下 Python 文件",
            conversation=conversation,
            db=db,
        )
    )

    assert [event["type"] for event in events] == [
        "tool_call_started",
        "tool_call_completed",
        "done",
    ]
    assert events[0]["tool_name"] == "glob"
    assert events[0]["tool_input"] == {"pattern": "**/*.py"}
    assert events[1]["output"] == ["src/main.py", "src/routes/claw/chat.py"]


@pytest.mark.asyncio
async def test_chat_stream_backfills_glob_args_after_start(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Glob late args",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_glob_late_args_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="查找 TypeScript 文件",
            conversation=conversation,
            db=db,
        )
    )

    assert [event["type"] for event in events] == [
        "tool_call_started",
        "tool_call_started",
        "tool_call_completed",
        "done",
    ]
    assert events[0]["tool_input"] == {}
    assert events[1]["tool_input"] == {"pattern": "**/*.ts", "path": "src"}
    assert events[2]["tool_input"] == {"pattern": "**/*.ts", "path": "src"}
    assert events[2]["output"] == ["src/server.ts"]


@pytest.mark.asyncio
async def test_chat_stream_persists_partial_history_for_refresh(tmp_path, monkeypatch):
    session_factory = build_file_session_factory(tmp_path / "claw-refresh.db")
    db = session_factory()
    conversation = ClawConversation(
        title="Refresh persistence",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_fake_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    generator = chat_route.chat_event_generator(
        conv_id=conversation.id,
        user_message="刷新时不要丢最近的工具消息",
        conversation=conversation,
        db=db,
    )

    seen_types = []
    try:
        while True:
            event = parse_sse_payload(await generator.__anext__())
            seen_types.append(event["type"])
            if event["type"] == "shell_started":
                break

        refresh_db = session_factory()
        try:
            history = await chat_route.get_messages(conversation.id, db=refresh_db)
        finally:
            refresh_db.close()
    finally:
        await generator.aclose()
        db.close()

    assistant_message = next(message for message in history if message["role"] == "assistant")

    assert seen_types[:3] == ["text", "tool_call_delta", "tool_call_started"]
    assert assistant_message["content"]
    assert assistant_message["metadata"]["stream_protocol"] == "claw.v2"
    assert assistant_message["metadata"]["stream_in_progress"] is True
    assert any(entry["kind"] == "text" for entry in assistant_message["metadata"]["timeline"])
    assert any(entry["kind"] == "shell" for entry in assistant_message["metadata"]["timeline"])
    assert any(tool_call["tool_name"] == "shell" for tool_call in assistant_message["tool_calls"])
    assert any(process_event["kind"] == "shell" for process_event in assistant_message["process_events"])


@pytest.mark.asyncio
async def test_chat_stream_backfills_read_file_path_from_tool_message(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Read file",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_read_file_fallback_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="璇诲彇鏂囦欢",
            conversation=conversation,
            db=db,
        )
    )

    assert [event["type"] for event in events] == [
        "tool_call_started",
        "tool_call_completed",
        "done",
    ]
    assert events[0]["tool_input"] == {"offset": 100, "limit": 50}
    assert events[1]["tool_input"] == {
        "offset": 100,
        "limit": 50,
        "file_path": "/src/pages/App.tsx",
    }

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    assert assistant_message["tool_calls"][0]["tool_input"] == {
        "offset": 100,
        "limit": 50,
        "file_path": "/src/pages/App.tsx",
    }


@pytest.mark.asyncio
async def test_chat_stream_preserves_chunked_read_file_args_when_final_tool_call_is_empty(
    monkeypatch,
):
    db = build_session()
    conversation = ClawConversation(
        title="Read file chunked",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_read_file_chunk_preservation_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="read src/main.tsx",
            conversation=conversation,
            db=db,
        )
    )

    assert [event["type"] for event in events] == [
        "tool_call_delta",
        "tool_call_started",
        "tool_call_completed",
        "done",
    ]
    assert events[1]["tool_input"] == {
        "file_path": "/src/main.tsx",
        "offset": 0,
        "limit": 100,
    }
    assert events[2]["tool_input"] == {
        "file_path": "/src/main.tsx",
        "offset": 0,
        "limit": 100,
    }

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    assert assistant_message["tool_calls"][0]["tool_input"] == {
        "file_path": "/src/main.tsx",
        "offset": 0,
        "limit": 100,
    }


@pytest.mark.asyncio
async def test_chat_stream_does_not_persist_internal_task_namespaces(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Task namespace",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_task_internal_namespace_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="搜索这个项目",
            conversation=conversation,
            db=db,
        )
    )

    assert [event["type"] for event in events] == [
        "tool_call_started",
        "subagent_started",
        "subagent_updated",
        "tool_call_completed",
        "subagent_completed",
        "done",
    ]

    subagent_started = next(event for event in events if event["type"] == "subagent_started")
    subagent_updated = next(event for event in events if event["type"] == "subagent_updated")
    assert subagent_started["item_id"] == "subagent:call_task_1"
    assert subagent_started["title"] == "搜索项目目录"
    assert subagent_updated["item_id"] == "subagent:call_task_1"
    assert "正在整理搜索结果。" in subagent_updated["transcript"]

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    subagent_events = [
        event for event in assistant_message["process_events"] if event["kind"] == "subagent"
    ]
    assert len(subagent_events) == 1
    assert subagent_events[0]["id"] == "subagent:call_task_1"
    assert subagent_events[0]["title"] == "搜索项目目录"
    assert "正在整理搜索结果。" in subagent_events[0]["data"]["transcript"]
