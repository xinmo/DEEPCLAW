import importlib.util
from pathlib import Path
import sys
import types

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


fake_claw_package = types.ModuleType("src.services.claw")
fake_claw_package.__path__ = []  # mark as package for submodule imports
fake_claw_package.create_claw_agent = lambda **_: None
fake_claw_package.validate_working_directory = lambda path: (True, None)
sys.modules["src.services.claw"] = fake_claw_package

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
from src.models.claw import ClawConversation

CHAT_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "chat.py"
CHAT_MODULE_NAME = "test_claw_shell_status_route"
chat_spec = importlib.util.spec_from_file_location(CHAT_MODULE_NAME, CHAT_MODULE_PATH)
chat_route = importlib.util.module_from_spec(chat_spec)
sys.modules[CHAT_MODULE_NAME] = chat_route
assert chat_spec.loader is not None
chat_spec.loader.exec_module(chat_route)


class FakeAgent:
    def __init__(self, chunks):
        self._chunks = chunks

    async def astream(self, _input_data, **_kwargs):
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
    import json

    return json.loads(raw_event[len("data: ") :])


async def collect_events(generator):
    events = []
    async for raw_event in generator:
        events.append(parse_sse_payload(raw_event))
    return events


def build_shell_failure_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_shell_fail_1",
                            "name": "shell",
                            "args": {"command": "dir missing-folder"},
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
                    content="[stderr] missing-folder not found\nExit code: 255\n[Command failed with exit code 255]",
                    tool_call_id="call_shell_fail_1",
                    name="shell",
                ),
                {},
            ),
        ),
    ]


def build_shell_delayed_args_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_shell_delayed_1",
                            "name": "shell",
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
                            "type": "tool_call_chunk",
                            "id": "call_shell_delayed_1",
                            "name": "shell",
                            "args": '{"command":"node --version"}',
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
                    content="v24.12.0\n\n[Command succeeded with exit code 0]",
                    tool_call_id="call_shell_delayed_1",
                    name="shell",
                ),
                {},
            ),
        ),
    ]


def build_shell_failure_without_args_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_shell_missing_args_1",
                            "name": "Bash",
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
                ToolMessage(
                    content="[stderr] 'head' 不是内部或外部命令，也不是可运行的程序\n或批处理文件。\nExit code: 255\n[Command failed with exit code 255]",
                    tool_call_id="call_shell_missing_args_1",
                    name="Bash",
                ),
                {},
            ),
        ),
    ]


def build_shell_malformed_args_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_shell_malformed_1",
                            "name": "Bash",
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
                            "type": "tool_call_chunk",
                            "id": "call_shell_malformed_1",
                            "name": "Bash",
                            "args": "command: cmd /c vol c:",
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
                    content="驱动器 C 中的卷是 系统\n卷的序列号是 1E4B-9E67\n\n[Command succeeded with exit code 0]",
                    tool_call_id="call_shell_malformed_1",
                    name="Bash",
                ),
                {},
            ),
        ),
    ]


def build_shell_snapshot_style_args_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call_chunk",
                            "id": "call_shell_snapshot_1",
                            "name": "shell",
                            "args": '{"path": "/"}',
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
                            "type": "tool_call_chunk",
                            "id": "call_shell_snapshot_1",
                            "name": "shell",
                            "args": '{"file_path": "/create_excel.py"}',
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
                            "type": "tool_call_chunk",
                            "id": "call_shell_snapshot_1",
                            "name": "shell",
                            "args": '{"command": "echo %USER',
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
                            "type": "tool_call_chunk",
                            "id": "call_shell_snapshot_1",
                            "name": "shell",
                            "args": '{"command": "echo %USERPROFILE%\\\\Desktop"}',
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
                    content="%USERPROFILE%\\Desktop",
                    tool_call_id="call_shell_snapshot_1",
                    name="shell",
                    artifact={
                        "command": "echo %USERPROFILE%\\Desktop",
                        "stdout": "%USERPROFILE%\\Desktop\n",
                        "stderr": "",
                        "exit_code": 0,
                    },
                ),
                {},
            ),
        ),
    ]


def build_execute_tool_call_chunk_message_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {
                            "id": "call_execute_chunk_1",
                            "name": "execute",
                            "args": '{"command": "cmd /c dir %USERPROFILE%\\\\Desktop"}',
                            "index": 0,
                        }
                    ],
                ),
                {},
            ),
        ),
        (
            (),
            "messages",
            (
                ToolMessage(
                    content=" Volume in drive C is System\n Directory of C:\\Users\\WLX\\Desktop\n\n[Command succeeded with exit code 0]",
                    tool_call_id="call_execute_chunk_1",
                    name="execute",
                ),
                {},
            ),
        ),
    ]


def build_execute_tool_result_artifact_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call_execute_artifact_1",
                            "name": "execute",
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
                ToolMessage(
                    content="hello from execute\n\n[Command succeeded with exit code 0]",
                    tool_call_id="call_execute_artifact_1",
                    name="execute",
                    artifact={
                        "command": "python /check_excel.py",
                        "exit_code": 0,
                        "output": "hello from execute",
                    },
                ),
                {},
            ),
        ),
    ]


def build_shell_mismatched_tool_id_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content=[
                        {
                            "type": "tool_call",
                            "id": "call.shell/1",
                            "name": "Bash",
                            "args": {"command": "cmd /c vol c:"},
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
                    content="椹卞姩鍣?C 涓殑鍗锋槸 绯荤粺\n鍗风殑搴忓垪鍙锋槸 1E4B-9E67\n\n[Command succeeded with exit code 0]",
                    tool_call_id="call_shell_1",
                    name="Bash",
                ),
                {},
            ),
        ),
    ]


def build_shell_additional_kwargs_function_call_chunks():
    return [
        (
            (),
            "messages",
            (
                AIMessage(
                    content="",
                    additional_kwargs={
                        "function_call": {
                            "name": "execute",
                            "arguments": '{"command":"cmd /c vol c:"}',
                        }
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
                    content="椹卞姩鍣?C 涓殑鍗锋槸 绯荤粺\n鍗风殑搴忓垪鍙锋槸 1E4B-9E67\n\n[Command succeeded with exit code 0]",
                    tool_call_id="call_shell_function_1",
                    name="execute",
                ),
                {},
            ),
        ),
    ]


@pytest.mark.parametrize(
    ("tool_input", "expected"),
    [
        ({"command": "dir"}, "dir"),
        ({"cmd": "git status"}, "git status"),
        ({"script": "npm test"}, "npm test"),
        ({"commands": ["pwd", "ls -la"]}, "pwd && ls -la"),
        ({"args": ["python", "app.py", "--help"]}, "python app.py --help"),
    ],
)
def test_derive_shell_command_supports_common_input_shapes(tool_input, expected):
    assert chat_route._derive_shell_command(tool_input) == expected


@pytest.mark.asyncio
async def test_chat_stream_marks_shell_failure_from_nonzero_exit_code(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Shell failure",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_shell_failure_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="run a failing shell command",
            conversation=conversation,
            db=db,
        )
    )

    tool_completed = next(event for event in events if event["type"] == "tool_call_completed")
    stderr_output = next(
        event for event in events if event["type"] == "shell_output" and event["stream"] == "stderr"
    )
    shell_completed = next(event for event in events if event["type"] == "shell_completed")

    assert tool_completed["status"] == "failed"
    assert shell_completed["status"] == "failed"
    assert shell_completed["exit_code"] == 255
    assert shell_completed["command"] == "dir missing-folder"
    assert shell_completed["tool_input"] == {"command": "dir missing-folder"}
    assert stderr_output["output"] == "missing-folder not found"


@pytest.mark.asyncio
async def test_chat_stream_backfills_shell_command_when_args_arrive_after_start(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Shell delayed args",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_shell_delayed_args_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="run node version check",
            conversation=conversation,
            db=db,
        )
    )

    shell_started_events = [event for event in events if event["type"] == "shell_started"]
    shell_output = next(event for event in events if event["type"] == "shell_output")
    shell_completed = next(event for event in events if event["type"] == "shell_completed")

    assert len(shell_started_events) == 2
    assert shell_started_events[-1]["command"] == "node --version"
    assert shell_started_events[-1]["tool_input"] == {"command": "node --version"}
    assert shell_output["command"] == "node --version"
    assert shell_completed["command"] == "node --version"
    assert shell_completed["tool_input"] == {"command": "node --version"}


@pytest.mark.asyncio
async def test_chat_stream_inferrs_shell_command_from_error_output_when_args_missing(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Shell missing args",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_shell_failure_without_args_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="run a missing shell command",
            conversation=conversation,
            db=db,
        )
    )

    shell_started = next(event for event in events if event["type"] == "shell_started")
    shell_output = next(event for event in events if event["type"] == "shell_output")
    shell_completed = next(event for event in events if event["type"] == "shell_completed")

    assert shell_started["command"] == ""
    assert shell_output["command"] == "head"
    assert shell_completed["command"] == "head"
    assert shell_completed["tool_input"] == {"command": "head"}


@pytest.mark.asyncio
async def test_chat_stream_backfills_shell_command_from_malformed_raw_args(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Shell malformed args",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_shell_malformed_args_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="run vol command",
            conversation=conversation,
            db=db,
        )
    )

    shell_started_events = [event for event in events if event["type"] == "shell_started"]
    shell_output = next(event for event in events if event["type"] == "shell_output")
    shell_completed = next(event for event in events if event["type"] == "shell_completed")

    assert len(shell_started_events) == 2
    assert shell_started_events[-1]["command"] == "cmd /c vol c:"
    assert shell_started_events[-1]["tool_input"] == {"command": "cmd /c vol c:"}
    assert shell_output["command"] == "cmd /c vol c:"
    assert shell_completed["command"] == "cmd /c vol c:"
    assert shell_completed["tool_input"] == {"command": "cmd /c vol c:"}


@pytest.mark.asyncio
async def test_chat_stream_merges_snapshot_style_shell_arg_chunks(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Shell snapshot args",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_shell_snapshot_style_args_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="run desktop echo command",
            conversation=conversation,
            db=db,
        )
    )

    shell_started_events = [event for event in events if event["type"] == "shell_started"]
    shell_completed = next(event for event in events if event["type"] == "shell_completed")

    assert len(shell_started_events) >= 2
    assert shell_started_events[-1]["command"] == "echo %USERPROFILE%\\Desktop"
    assert shell_started_events[-1]["tool_input"] == {
        "path": "/",
        "file_path": "/create_excel.py",
        "command": "echo %USERPROFILE%\\Desktop",
    }
    assert shell_completed["command"] == "echo %USERPROFILE%\\Desktop"
    assert shell_completed["tool_input"] == {
        "path": "/",
        "file_path": "/create_excel.py",
        "command": "echo %USERPROFILE%\\Desktop",
    }

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    assert assistant_message["tool_calls"][0]["tool_input"] == {
        "path": "/",
        "file_path": "/create_excel.py",
        "command": "echo %USERPROFILE%\\Desktop",
    }


@pytest.mark.asyncio
async def test_chat_stream_reads_execute_command_from_tool_call_chunks(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Execute tool call chunks",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_execute_tool_call_chunk_message_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="list desktop files",
            conversation=conversation,
            db=db,
        )
    )

    shell_started = next(event for event in events if event["type"] == "shell_started")
    shell_completed = next(event for event in events if event["type"] == "shell_completed")

    assert shell_started["command"] == "cmd /c dir %USERPROFILE%\\Desktop"
    assert shell_started["tool_input"] == {"command": "cmd /c dir %USERPROFILE%\\Desktop"}
    assert shell_completed["command"] == "cmd /c dir %USERPROFILE%\\Desktop"
    assert shell_completed["tool_input"] == {"command": "cmd /c dir %USERPROFILE%\\Desktop"}

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    assert assistant_message["tool_calls"][0]["tool_input"] == {
        "command": "cmd /c dir %USERPROFILE%\\Desktop"
    }
    assert assistant_message["process_events"][0]["data"]["input"] == {
        "command": "cmd /c dir %USERPROFILE%\\Desktop"
    }


@pytest.mark.asyncio
async def test_chat_stream_backfills_execute_command_from_tool_result_artifact(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Execute tool result artifact",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_execute_tool_result_artifact_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="run execute via artifact",
            conversation=conversation,
            db=db,
        )
    )

    shell_completed = next(event for event in events if event["type"] == "shell_completed")
    assert shell_completed["command"] == "python /check_excel.py"
    assert shell_completed["tool_input"] == {"command": "python /check_excel.py"}

    messages = await chat_route.get_messages(conversation.id, db=db)
    assistant_message = next(message for message in messages if message["role"] == "assistant")
    assert assistant_message["tool_calls"][0]["tool_input"] == {"command": "python /check_excel.py"}
    assert assistant_message["process_events"][0]["data"]["input"] == {
        "command": "python /check_excel.py"
    }


@pytest.mark.asyncio
async def test_chat_stream_reuses_running_shell_record_when_tool_message_id_is_sanitized(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Shell id mismatch",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_shell_mismatched_tool_id_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="run volume command",
            conversation=conversation,
            db=db,
        )
    )

    shell_started = next(event for event in events if event["type"] == "shell_started")
    shell_completed = next(event for event in events if event["type"] == "shell_completed")

    assert shell_started["tool_id"] == "call.shell/1"
    assert shell_started["tool_input"] == {"command": "cmd /c vol c:"}
    assert shell_completed["tool_id"] == "call.shell/1"
    assert shell_completed["command"] == "cmd /c vol c:"
    assert shell_completed["tool_input"] == {"command": "cmd /c vol c:"}


@pytest.mark.asyncio
async def test_chat_stream_reads_shell_command_from_additional_kwargs_function_call(monkeypatch):
    db = build_session()
    conversation = ClawConversation(
        title="Shell function_call",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    fake_agent = FakeAgent(build_shell_additional_kwargs_function_call_chunks())
    monkeypatch.setattr(chat_route, "create_claw_agent", lambda **_: fake_agent)

    events = await collect_events(
        chat_route.chat_event_generator(
            conv_id=conversation.id,
            user_message="run volume command",
            conversation=conversation,
            db=db,
        )
    )

    shell_started = next(event for event in events if event["type"] == "shell_started")
    shell_completed = next(event for event in events if event["type"] == "shell_completed")

    assert shell_started["command"] == "cmd /c vol c:"
    assert shell_started["tool_input"] == {"command": "cmd /c vol c:"}
    assert shell_completed["command"] == "cmd /c vol c:"
    assert shell_completed["tool_input"] == {"command": "cmd /c vol c:"}
