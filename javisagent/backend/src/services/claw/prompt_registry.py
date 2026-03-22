from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._bootstrap import ensure_local_dependency_paths

ensure_local_dependency_paths()

CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"
PROMPTS_FILE = CONFIG_DIR / "claw_prompts.json"
LEGACY_SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"
LOCAL_DEEPAGENTS_ROOT = Path(__file__).resolve().parents[4] / "libs" / "deepagents" / "deepagents"

SYSTEM_PROMPT_ID = "system_prompt"
BASE_AGENT_PROMPT_ID = "base_agent_prompt"
TODO_SYSTEM_PROMPT_ID = "todo_system_prompt"
FILESYSTEM_SYSTEM_PROMPT_ID = "filesystem_system_prompt"
TASK_SYSTEM_PROMPT_ID = "task_system_prompt"
GENERAL_PURPOSE_SUBAGENT_PROMPT_ID = "general_purpose_subagent_prompt"
SUMMARIZATION_SUMMARY_PROMPT_ID = "summarization_summary_prompt"
MEMORY_SYSTEM_PROMPT_ID = "memory_system_prompt"
SKILLS_SYSTEM_PROMPT_ID = "skills_system_prompt"
SUMMARIZATION_TOOL_SYSTEM_PROMPT_ID = "summarization_tool_system_prompt"


@dataclass(frozen=True)
class PromptDefinition:
    id: str
    name: str
    description: str
    default_content: str
    variables: tuple[str, ...] = ()


def _load_python_constant(module_path: Path, constant_name: str) -> str:
    module = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == constant_name:
                value = ast.literal_eval(node.value)
                if isinstance(value, str):
                    return value
                break

    msg = f"Unable to load constant {constant_name} from {module_path}"
    raise KeyError(msg)


def _load_deepagents_prompt_defaults() -> dict[str, str]:
    try:
        return {
            "FILESYSTEM_SYSTEM_PROMPT": _load_python_constant(
                LOCAL_DEEPAGENTS_ROOT / "middleware" / "filesystem.py",
                "FILESYSTEM_SYSTEM_PROMPT",
            ),
            "EXECUTION_SYSTEM_PROMPT": _load_python_constant(
                LOCAL_DEEPAGENTS_ROOT / "middleware" / "filesystem.py",
                "EXECUTION_SYSTEM_PROMPT",
            ),
            "MEMORY_SYSTEM_PROMPT": _load_python_constant(
                LOCAL_DEEPAGENTS_ROOT / "middleware" / "memory.py",
                "MEMORY_SYSTEM_PROMPT",
            ),
            "SKILLS_SYSTEM_PROMPT": _load_python_constant(
                LOCAL_DEEPAGENTS_ROOT / "middleware" / "skills.py",
                "SKILLS_SYSTEM_PROMPT",
            ),
            "DEFAULT_SUBAGENT_PROMPT": _load_python_constant(
                LOCAL_DEEPAGENTS_ROOT / "middleware" / "subagents.py",
                "DEFAULT_SUBAGENT_PROMPT",
            ),
            "TASK_SYSTEM_PROMPT": _load_python_constant(
                LOCAL_DEEPAGENTS_ROOT / "middleware" / "subagents.py",
                "TASK_SYSTEM_PROMPT",
            ),
            "SUMMARIZATION_SYSTEM_PROMPT": _load_python_constant(
                LOCAL_DEEPAGENTS_ROOT / "middleware" / "summarization.py",
                "SUMMARIZATION_SYSTEM_PROMPT",
            ),
            "BASE_AGENT_PROMPT": _load_python_constant(
                LOCAL_DEEPAGENTS_ROOT / "prompt_defaults.py",
                "BASE_AGENT_PROMPT",
            ),
        }
    except (FileNotFoundError, KeyError, SyntaxError, UnicodeDecodeError, ValueError):
        from deepagents.middleware.filesystem import (
            EXECUTION_SYSTEM_PROMPT,
            FILESYSTEM_SYSTEM_PROMPT,
        )
        from deepagents.middleware.memory import MEMORY_SYSTEM_PROMPT
        from deepagents.middleware.skills import SKILLS_SYSTEM_PROMPT
        from deepagents.middleware.subagents import (
            DEFAULT_SUBAGENT_PROMPT,
            TASK_SYSTEM_PROMPT,
        )
        from deepagents.middleware.summarization import SUMMARIZATION_SYSTEM_PROMPT
        from deepagents.prompt_defaults import BASE_AGENT_PROMPT

        return {
            "FILESYSTEM_SYSTEM_PROMPT": FILESYSTEM_SYSTEM_PROMPT,
            "EXECUTION_SYSTEM_PROMPT": EXECUTION_SYSTEM_PROMPT,
            "MEMORY_SYSTEM_PROMPT": MEMORY_SYSTEM_PROMPT,
            "SKILLS_SYSTEM_PROMPT": SKILLS_SYSTEM_PROMPT,
            "DEFAULT_SUBAGENT_PROMPT": DEFAULT_SUBAGENT_PROMPT,
            "TASK_SYSTEM_PROMPT": TASK_SYSTEM_PROMPT,
            "SUMMARIZATION_SYSTEM_PROMPT": SUMMARIZATION_SYSTEM_PROMPT,
            "BASE_AGENT_PROMPT": BASE_AGENT_PROMPT,
        }


def _default_system_prompt() -> str:
    return _load_python_constant(
        Path(__file__).resolve().with_name("agent.py"),
        "SYSTEM_PROMPT_TEMPLATE",
    )


def _get_prompt_definitions() -> list[PromptDefinition]:
    from langchain.agents.middleware.summarization import DEFAULT_SUMMARY_PROMPT
    from langchain.agents.middleware.todo import WRITE_TODOS_SYSTEM_PROMPT

    prompt_defaults = _load_deepagents_prompt_defaults()

    return [
        PromptDefinition(
            id=SYSTEM_PROMPT_ID,
            name="System Prompt",
            description="Claw main agent system prompt template. New conversations keep using the conversation snapshot of this prompt.",
            default_content=_default_system_prompt(),
            variables=("working_directory",),
        ),
        PromptDefinition(
            id=BASE_AGENT_PROMPT_ID,
            name="BASE_AGENT_PROMPT",
            description="DeepAgents base behavior prompt appended after the Claw system prompt.",
            default_content=prompt_defaults["BASE_AGENT_PROMPT"],
        ),
        PromptDefinition(
            id=TODO_SYSTEM_PROMPT_ID,
            name="TodoListMiddleware",
            description="Prompt that teaches the agent when and how to use write_todos.",
            default_content=WRITE_TODOS_SYSTEM_PROMPT,
        ),
        PromptDefinition(
            id=FILESYSTEM_SYSTEM_PROMPT_ID,
            name="FilesystemMiddleware",
            description="Combined filesystem and execute-tool guidance injected by FilesystemMiddleware.",
            default_content="\n\n".join(
                [
                    prompt_defaults["FILESYSTEM_SYSTEM_PROMPT"],
                    prompt_defaults["EXECUTION_SYSTEM_PROMPT"],
                ]
            ).strip(),
        ),
        PromptDefinition(
            id=TASK_SYSTEM_PROMPT_ID,
            name="SubAgentMiddleware TASK_SYSTEM_PROMPT",
            description="Main-agent instructions for when to delegate work through the task tool.",
            default_content=prompt_defaults["TASK_SYSTEM_PROMPT"],
        ),
        PromptDefinition(
            id=GENERAL_PURPOSE_SUBAGENT_PROMPT_ID,
            name="General-purpose Subagent Prompt",
            description="Default system prompt used by the built-in general-purpose subagent.",
            default_content=prompt_defaults["DEFAULT_SUBAGENT_PROMPT"],
        ),
        PromptDefinition(
            id=SUMMARIZATION_SUMMARY_PROMPT_ID,
            name="Summarization Summary Prompt",
            description="Internal summarization prompt used when the middleware compacts old conversation history.",
            default_content=DEFAULT_SUMMARY_PROMPT,
        ),
        PromptDefinition(
            id=MEMORY_SYSTEM_PROMPT_ID,
            name="MemoryMiddleware",
            description="Prompt template that injects persistent global memory from ~/.memory/AGENTS.md into the main agent.",
            default_content=prompt_defaults["MEMORY_SYSTEM_PROMPT"],
            variables=("agent_memory",),
        ),
        PromptDefinition(
            id=SKILLS_SYSTEM_PROMPT_ID,
            name="SkillsMiddleware",
            description="Prompt template that exposes built-in global skills loaded from ~/.agents/skills.",
            default_content=prompt_defaults["SKILLS_SYSTEM_PROMPT"],
            variables=("skills_locations", "skills_list"),
        ),
        PromptDefinition(
            id=SUMMARIZATION_TOOL_SYSTEM_PROMPT_ID,
            name="SummarizationToolMiddleware",
            description="Prompt that teaches the agent when and how to use compact_conversation.",
            default_content=prompt_defaults["SUMMARIZATION_SYSTEM_PROMPT"],
        ),
    ]


def get_prompt_definition_map() -> dict[str, PromptDefinition]:
    return {definition.id: definition for definition in _get_prompt_definitions()}


def list_prompt_infos() -> list[dict[str, Any]]:
    return [
        {
            "id": definition.id,
            "name": definition.name,
            "description": definition.description,
        }
        for definition in _get_prompt_definitions()
    ]


def _load_prompt_overrides() -> dict[str, str]:
    if not PROMPTS_FILE.exists():
        return {}

    try:
        raw = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw, dict):
        return {}

    prompt_ids = get_prompt_definition_map()
    overrides: dict[str, str] = {}
    for prompt_id, value in raw.items():
        if prompt_id not in prompt_ids or not isinstance(value, str):
            continue
        overrides[prompt_id] = value
    return overrides


def _write_prompt_overrides(overrides: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(overrides, ensure_ascii=False, indent=2)
    PROMPTS_FILE.write_text(serialized + "\n", encoding="utf-8")


def get_current_prompt(prompt_id: str) -> str:
    definitions = get_prompt_definition_map()
    definition = definitions.get(prompt_id)
    if definition is None:
        msg = f"Unknown prompt id: {prompt_id}"
        raise KeyError(msg)

    overrides = _load_prompt_overrides()
    if prompt_id in overrides:
        return overrides[prompt_id]

    if prompt_id == SYSTEM_PROMPT_ID and LEGACY_SYSTEM_PROMPT_FILE.exists():
        try:
            return LEGACY_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        except OSError:
            pass

    return definition.default_content


def get_current_system_prompt() -> str:
    return get_current_prompt(SYSTEM_PROMPT_ID)


def get_prompt_detail(prompt_id: str) -> dict[str, Any]:
    definition = get_prompt_definition_map().get(prompt_id)
    if definition is None:
        msg = f"Unknown prompt id: {prompt_id}"
        raise KeyError(msg)

    return {
        "id": definition.id,
        "name": definition.name,
        "description": definition.description,
        "content": get_current_prompt(prompt_id),
        "default_content": definition.default_content,
        "variables": list(definition.variables),
    }


def save_prompt(prompt_id: str, content: str) -> None:
    if not content.strip():
        msg = "Prompt content cannot be empty."
        raise ValueError(msg)

    definitions = get_prompt_definition_map()
    if prompt_id not in definitions:
        msg = f"Unknown prompt id: {prompt_id}"
        raise KeyError(msg)

    overrides = _load_prompt_overrides()
    overrides[prompt_id] = content
    _write_prompt_overrides(overrides)

    if prompt_id == SYSTEM_PROMPT_ID:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        LEGACY_SYSTEM_PROMPT_FILE.write_text(content, encoding="utf-8")


def reset_prompt(prompt_id: str) -> str:
    definitions = get_prompt_definition_map()
    definition = definitions.get(prompt_id)
    if definition is None:
        msg = f"Unknown prompt id: {prompt_id}"
        raise KeyError(msg)

    overrides = _load_prompt_overrides()
    if prompt_id in overrides:
        overrides.pop(prompt_id, None)
        _write_prompt_overrides(overrides)

    if prompt_id == SYSTEM_PROMPT_ID and LEGACY_SYSTEM_PROMPT_FILE.exists():
        LEGACY_SYSTEM_PROMPT_FILE.unlink()

    return definition.default_content


def get_current_prompt_bundle() -> dict[str, str]:
    return {
        prompt_id: get_current_prompt(prompt_id)
        for prompt_id in get_prompt_definition_map()
    }


def normalize_prompt_bundle(prompt_bundle: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(prompt_bundle, dict):
        return {}

    definitions = get_prompt_definition_map()
    normalized: dict[str, str] = {}
    for prompt_id in definitions:
        value = prompt_bundle.get(prompt_id)
        if isinstance(value, str):
            normalized[prompt_id] = value
    return normalized


def get_system_prompt_from_bundle(prompt_bundle: dict[str, Any] | None) -> str | None:
    normalized = normalize_prompt_bundle(prompt_bundle)
    system_prompt = normalized.get(SYSTEM_PROMPT_ID)
    if system_prompt:
        return system_prompt
    return None


def build_deep_agent_prompt_overrides(prompt_bundle: dict[str, Any] | None) -> dict[str, str]:
    prompt_bundle = normalize_prompt_bundle(prompt_bundle)
    return {
        "base_agent_prompt": prompt_bundle.get(
            BASE_AGENT_PROMPT_ID,
            get_current_prompt(BASE_AGENT_PROMPT_ID),
        ),
        "todo_system_prompt": prompt_bundle.get(
            TODO_SYSTEM_PROMPT_ID,
            get_current_prompt(TODO_SYSTEM_PROMPT_ID),
        ),
        "filesystem_system_prompt": prompt_bundle.get(
            FILESYSTEM_SYSTEM_PROMPT_ID,
            get_current_prompt(FILESYSTEM_SYSTEM_PROMPT_ID),
        ),
        "task_system_prompt": prompt_bundle.get(
            TASK_SYSTEM_PROMPT_ID,
            get_current_prompt(TASK_SYSTEM_PROMPT_ID),
        ),
        "general_purpose_subagent_system_prompt": prompt_bundle.get(
            GENERAL_PURPOSE_SUBAGENT_PROMPT_ID,
            get_current_prompt(GENERAL_PURPOSE_SUBAGENT_PROMPT_ID),
        ),
        "summarization_summary_prompt": prompt_bundle.get(
            SUMMARIZATION_SUMMARY_PROMPT_ID,
            get_current_prompt(SUMMARIZATION_SUMMARY_PROMPT_ID),
        ),
        "memory_system_prompt": prompt_bundle.get(
            MEMORY_SYSTEM_PROMPT_ID,
            get_current_prompt(MEMORY_SYSTEM_PROMPT_ID),
        ),
        "skills_system_prompt": prompt_bundle.get(
            SKILLS_SYSTEM_PROMPT_ID,
            get_current_prompt(SKILLS_SYSTEM_PROMPT_ID),
        ),
        "summarization_tool_system_prompt": prompt_bundle.get(
            SUMMARIZATION_TOOL_SYSTEM_PROMPT_ID,
            get_current_prompt(SUMMARIZATION_TOOL_SYSTEM_PROMPT_ID),
        ),
    }


def get_deep_agent_prompt_overrides() -> dict[str, str]:
    return build_deep_agent_prompt_overrides(get_current_prompt_bundle())
