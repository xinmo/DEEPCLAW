import importlib
import sys
import types
import uuid
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
LOCAL_DEEPAGENTS_ROOT = PROJECT_ROOT / "libs" / "deepagents"
LOCAL_CLI_ROOT = PROJECT_ROOT / "libs" / "cli"

for candidate in (str(BACKEND_ROOT), str(LOCAL_DEEPAGENTS_ROOT), str(LOCAL_CLI_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


class FakeCompositeBackend:
    def __init__(self, default, routes):
        self.default = default
        self.routes = routes


class FakeFilesystemBackend:
    def __init__(self, root_dir=None, virtual_mode=None, max_file_size_mb=10):
        self.cwd = Path(root_dir).resolve() if root_dir else Path.cwd()
        self.virtual_mode = virtual_mode
        self.max_file_size_mb = max_file_size_mb


class FakeLocalShellBackend:
    def __init__(self, root_dir=None, virtual_mode=None, inherit_env=False):
        self.cwd = Path(root_dir).resolve() if root_dir else Path.cwd()
        self.virtual_mode = virtual_mode
        self.inherit_env = inherit_env


@dataclass
class FakeWriteResult:
    error: str | None = None
    path: str | None = None
    files_update: dict | None = None


@dataclass
class FakeEditResult:
    error: str | None = None
    path: str | None = None
    files_update: dict | None = None
    occurrences: int | None = None


@dataclass
class FakeFileUploadResponse:
    path: str
    error: str | None = None


fake_langchain_anthropic = types.ModuleType("langchain_anthropic")
fake_langchain_anthropic.ChatAnthropic = type("ChatAnthropic", (), {})
sys.modules["langchain_anthropic"] = fake_langchain_anthropic

fake_langchain_openai = types.ModuleType("langchain_openai")
fake_langchain_openai.ChatOpenAI = type("ChatOpenAI", (), {})
sys.modules["langchain_openai"] = fake_langchain_openai

fake_deepagents = types.ModuleType("deepagents")
fake_deepagents.create_deep_agent = lambda **kwargs: kwargs
sys.modules["deepagents"] = fake_deepagents

fake_deepagents_backends = types.ModuleType("deepagents.backends")
sys.modules["deepagents.backends"] = fake_deepagents_backends

fake_deepagents_backends_composite = types.ModuleType("deepagents.backends.composite")
fake_deepagents_backends_composite.CompositeBackend = FakeCompositeBackend
sys.modules["deepagents.backends.composite"] = fake_deepagents_backends_composite

fake_deepagents_backends_filesystem = types.ModuleType("deepagents.backends.filesystem")
fake_deepagents_backends_filesystem.FilesystemBackend = FakeFilesystemBackend
sys.modules["deepagents.backends.filesystem"] = fake_deepagents_backends_filesystem

fake_deepagents_backends_protocol = types.ModuleType("deepagents.backends.protocol")
fake_deepagents_backends_protocol.WriteResult = FakeWriteResult
fake_deepagents_backends_protocol.EditResult = FakeEditResult
fake_deepagents_backends_protocol.FileUploadResponse = FakeFileUploadResponse
sys.modules["deepagents.backends.protocol"] = fake_deepagents_backends_protocol

fake_deepagents_backends_local_shell = types.ModuleType("deepagents.backends.local_shell")
fake_deepagents_backends_local_shell.LocalShellBackend = FakeLocalShellBackend
sys.modules["deepagents.backends.local_shell"] = fake_deepagents_backends_local_shell

fake_deepagents_middleware = types.ModuleType("deepagents.middleware")
sys.modules["deepagents.middleware"] = fake_deepagents_middleware

fake_deepagents_middleware_summarization = types.ModuleType(
    "deepagents.middleware.summarization"
)
fake_deepagents_middleware_summarization.create_summarization_tool_middleware = (
    lambda model, backend, *, system_prompt=None: {
        "model": model,
        "backend": backend,
        "system_prompt": system_prompt,
    }
)
sys.modules["deepagents.middleware.summarization"] = (
    fake_deepagents_middleware_summarization
)

fake_deepagents_cli = types.ModuleType("deepagents_cli")
sys.modules["deepagents_cli"] = fake_deepagents_cli

fake_deepagents_cli_local_context = types.ModuleType("deepagents_cli.local_context")
fake_deepagents_cli_local_context.LocalContextMiddleware = type(
    "LocalContextMiddleware",
    (),
    {"__init__": lambda self, *, backend: setattr(self, "backend", backend)},
)
sys.modules["deepagents_cli.local_context"] = fake_deepagents_cli_local_context

fake_prompt_debug = types.ModuleType("src.services.claw.prompt_debug")
fake_prompt_debug.ClawPromptDebugCaptureMiddleware = type(
    "ClawPromptDebugCaptureMiddleware",
    (),
    {"__init__": lambda self, callback: setattr(self, "callback", callback)},
)
sys.modules["src.services.claw.prompt_debug"] = fake_prompt_debug

existing_claw_package = sys.modules.get("src.services.claw")
if existing_claw_package is not None and not getattr(existing_claw_package, "__file__", None):
    sys.modules.pop("src.services.claw", None)
    sys.modules.pop("src.services.claw.agent", None)
    sys.modules.pop("src.services.claw.local_context", None)
    sys.modules.pop("src.services.claw.skill_registry", None)
    sys.modules.pop("src.services.claw.tools", None)

claw_agent_module = importlib.import_module("src.services.claw.agent")


def test_create_claw_agent_uses_global_composite_backend(monkeypatch):
    tmp_path = BACKEND_ROOT / "tests" / ".tmp" / f"claw-agent-{uuid.uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(claw_agent_module, "CLAW_MEMORY_DIR", tmp_path / ".memory")
    monkeypatch.setattr(
        claw_agent_module,
        "CLAW_MEMORY_FILE",
        tmp_path / ".memory" / "AGENTS.md",
    )
    monkeypatch.setattr(claw_agent_module, "CLAW_SKILLS_DIR", tmp_path / ".agents" / "skills")
    monkeypatch.setattr(
        claw_agent_module,
        "CLAW_CONVERSATION_HISTORY_DIR",
        tmp_path / ".conversation_history",
    )

    captured: dict[str, object] = {}

    class DummyLLM:
        pass

    class FakeLocalContextMiddleware:
        def __init__(self, *, backend):
            self.backend = backend

    class FakeSummarizationToolMiddleware:
        def __init__(self, *, model, backend, system_prompt):
            self.model = model
            self.backend = backend
            self.system_prompt = system_prompt

    def fake_create_llm(llm_model, model_config, api_key):
        captured["llm_kwargs"] = {
            "llm_model": llm_model,
            "model_config": model_config,
            "api_key": api_key,
        }
        return DummyLLM()

    def fake_create_summarization_tool_middleware(model, backend, *, system_prompt=None):
        captured["summarization_tool_kwargs"] = {
            "model": model,
            "backend": backend,
            "system_prompt": system_prompt,
        }
        return FakeSummarizationToolMiddleware(
            model=model,
            backend=backend,
            system_prompt=system_prompt,
        )

    def fake_create_deep_agent(**kwargs):
        captured["agent_kwargs"] = kwargs
        return "fake-agent"

    monkeypatch.setattr(claw_agent_module, "_create_llm", fake_create_llm)
    monkeypatch.setattr(
        claw_agent_module,
        "ClawLocalContextMiddleware",
        FakeLocalContextMiddleware,
    )
    monkeypatch.setattr(
        claw_agent_module,
        "create_summarization_tool_middleware",
        fake_create_summarization_tool_middleware,
    )
    monkeypatch.setattr(
        claw_agent_module,
        "get_enabled_skill_sources",
        lambda: ["/skills/test-skill"],
    )
    monkeypatch.setattr(claw_agent_module, "create_deep_agent", fake_create_deep_agent)

    result = claw_agent_module.create_claw_agent(
        working_directory=str(tmp_path),
        llm_model="deepseek-chat",
        conversation_id="conv-123",
        custom_system_prompt="Workspace: {working_directory}",
        prompt_overrides={
            "summarization_tool_system_prompt": "Compact prompt snapshot",
        },
        turn_instruction="Use /brainstorming for this turn only.",
    )

    assert result == "fake-agent"

    backend = captured["agent_kwargs"]["backend"]
    assert isinstance(backend, claw_agent_module.CompositeBackend)
    assert isinstance(backend.default, claw_agent_module.LocalShellBackend)
    assert backend.default.cwd == tmp_path.resolve()
    assert backend.default.virtual_mode is True
    assert set(backend.routes) == {
        "/memory/",
        "/skills/",
        "/conversation_history/",
    }
    assert isinstance(backend.routes["/memory/"], claw_agent_module.FilesystemBackend)
    assert backend.routes["/memory/"].cwd == (tmp_path / ".memory").resolve()
    assert isinstance(
        backend.routes["/skills/"],
        claw_agent_module.ReadOnlyFilesystemBackend,
    )
    assert backend.routes["/skills/"].cwd == (tmp_path / ".agents" / "skills").resolve()
    assert backend.routes["/conversation_history/"].cwd == (
        tmp_path / ".conversation_history"
    ).resolve()
    write_result = backend.routes["/skills/"].write("/test-skill/SKILL.md", "blocked")
    assert write_result.error == "permission_denied: '/test-skill/SKILL.md' is read-only"
    edit_result = backend.routes["/skills/"].edit("/test-skill/SKILL.md", "a", "b")
    assert edit_result.error == "permission_denied: '/test-skill/SKILL.md' is read-only"
    upload_result = backend.routes["/skills/"].upload_files(
        [("/test-skill/SKILL.md", b"blocked")]
    )
    assert upload_result[0].error == "permission_denied"
    assert captured["agent_kwargs"]["memory"] == [claw_agent_module.CLAW_MEMORY_SOURCE]
    assert captured["agent_kwargs"]["skills"] == ["/skills/test-skill"]
    assert captured["agent_kwargs"]["prompt_overrides"] == {
        "summarization_tool_system_prompt": "Compact prompt snapshot",
    }
    assert "Workspace:" in captured["agent_kwargs"]["system_prompt"]
    assert "Use /brainstorming for this turn only." in captured["agent_kwargs"]["system_prompt"]
    assert captured["agent_kwargs"]["checkpointer"] is claw_agent_module.CLAW_CHECKPOINTER
    assert len(captured["agent_kwargs"]["middleware"]) == 2
    local_context = captured["agent_kwargs"]["middleware"][0]
    compact_tool = captured["agent_kwargs"]["middleware"][1]
    assert isinstance(local_context, FakeLocalContextMiddleware)
    assert local_context.backend is backend.default
    assert isinstance(compact_tool, FakeSummarizationToolMiddleware)
    assert compact_tool.backend is backend
    assert compact_tool.system_prompt == "Compact prompt snapshot"
    assert (tmp_path / ".memory").is_dir()
    assert (tmp_path / ".agents" / "skills").is_dir()
    assert (tmp_path / ".conversation_history").is_dir()
    assert (tmp_path / ".memory" / "AGENTS.md").exists()
