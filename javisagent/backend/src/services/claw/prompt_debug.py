from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from ._bootstrap import ensure_local_dependency_paths
from .prompt_registry import (
    BASE_AGENT_PROMPT_ID,
    FILESYSTEM_SYSTEM_PROMPT_ID,
    MEMORY_SYSTEM_PROMPT_ID,
    SKILLS_SYSTEM_PROMPT_ID,
    SUMMARIZATION_TOOL_SYSTEM_PROMPT_ID,
    TASK_SYSTEM_PROMPT_ID,
    TODO_SYSTEM_PROMPT_ID,
)
from .skill_registry import get_enabled_skill_sources

ensure_local_dependency_paths()

from deepagents.middleware.subagents import DEFAULT_GENERAL_PURPOSE_DESCRIPTION

logger = logging.getLogger(__name__)

PromptDebugCaptureCallback = Callable[[dict[str, Any]], None]


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(_jsonable(value), ensure_ascii=False, indent=2)


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_format(template: str, **variables: str) -> str:
    try:
        return template.format(**variables)
    except Exception:
        return template


def _message_role(message: BaseMessage) -> str:
    message_type = getattr(message, "type", "") or message.__class__.__name__
    normalized_type = str(message_type).lower()
    role_map = {
        "human": "user",
        "user": "user",
        "ai": "assistant",
        "assistant": "assistant",
        "system": "system",
        "tool": "tool",
    }
    return role_map.get(normalized_type, normalized_type)


def _serialize_message(message: BaseMessage) -> dict[str, Any]:
    additional_kwargs = getattr(message, "additional_kwargs", None)
    tool_calls = getattr(message, "tool_calls", None)
    name = getattr(message, "name", None)

    return {
        "role": _message_role(message),
        "type": str(getattr(message, "type", "") or message.__class__.__name__),
        "name": str(name) if isinstance(name, str) and name else None,
        "content": _jsonable(getattr(message, "content", None)),
        "content_text": _stringify(getattr(message, "content", None)),
        "additional_kwargs": _jsonable(additional_kwargs) if additional_kwargs else None,
        "tool_calls": _jsonable(tool_calls) if tool_calls else None,
    }


def _serialize_system_prompt(value: Any) -> str:
    if isinstance(value, BaseMessage):
        return _stringify(getattr(value, "content", None))
    return _stringify(value)


def _extract_tool_schema(tool: Any) -> Any:
    if isinstance(tool, dict):
        return _jsonable(tool.get("input_schema") or tool.get("args_schema"))

    if not isinstance(tool, BaseTool):
        return None

    try:
        input_schema = tool.get_input_schema()
        if hasattr(input_schema, "model_json_schema"):
            return input_schema.model_json_schema()
    except Exception:
        logger.debug("Failed to derive tool input schema for %s", getattr(tool, "name", tool), exc_info=True)

    args_schema = getattr(tool, "args_schema", None)
    if args_schema is not None and hasattr(args_schema, "model_json_schema"):
        try:
            return args_schema.model_json_schema()
        except Exception:
            logger.debug("Failed to derive args schema for %s", getattr(tool, "name", tool), exc_info=True)

    return None


def _serialize_tool(tool: Any) -> dict[str, Any]:
    if isinstance(tool, dict):
        return {
            "name": str(tool.get("name") or ""),
            "description": str(tool.get("description") or ""),
            "input_schema": _jsonable(_extract_tool_schema(tool)),
        }

    name = getattr(tool, "name", None)
    description = getattr(tool, "description", None)
    return {
        "name": str(name or tool.__class__.__name__),
        "description": str(description or ""),
        "input_schema": _jsonable(_extract_tool_schema(tool)),
    }


def serialize_model_request(request: ModelRequest[Any]) -> dict[str, Any]:
    state = _coerce_dict(request.state)
    local_context = state.get("local_context")
    memory_contents = state.get("memory_contents")
    skills_metadata = state.get("skills_metadata")
    summarization_event = state.get("_summarization_event")
    system_prompt = getattr(request, "system_prompt", None)
    if system_prompt in (None, ""):
        system_prompt = getattr(request, "system_message", None)

    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "system_prompt": _serialize_system_prompt(system_prompt),
        "message_count": len(request.messages),
        "messages": [_serialize_message(message) for message in request.messages],
        "tool_count": len(request.tools),
        "tools": [_serialize_tool(tool) for tool in request.tools],
        "state": {
            "local_context": _stringify(local_context) if local_context else "",
            "memory_contents": _jsonable(memory_contents) if isinstance(memory_contents, dict) else {},
            "skills_metadata": _jsonable(skills_metadata) if isinstance(skills_metadata, list) else [],
            "summarization_event": _jsonable(summarization_event) if summarization_event else None,
        },
    }


def _format_memory_section(memory_contents: dict[str, str], template: str) -> str:
    if not memory_contents:
        return template.format(agent_memory="(No memory loaded)")

    sections = [
        f"{path}\n{content}"
        for path, content in memory_contents.items()
        if isinstance(path, str) and isinstance(content, str) and content
    ]
    return template.format(agent_memory="\n\n".join(sections) if sections else "(No memory loaded)")


def _format_skill_annotations(skill: dict[str, Any]) -> str:
    parts: list[str] = []
    license_name = str(skill.get("license") or "").strip()
    compatibility = str(skill.get("compatibility") or "").strip()
    if license_name:
        parts.append(f"License: {license_name}")
    if compatibility:
        parts.append(f"Compatibility: {compatibility}")
    return ", ".join(parts)


def _format_skills_locations(source_paths: list[str]) -> str:
    if not source_paths:
        return "(No skill sources configured)"

    lines: list[str] = []
    for index, source_path in enumerate(source_paths):
        source_name = source_path.rstrip("/").split("/")[-1] or "skills"
        suffix = " (higher priority)" if index == len(source_paths) - 1 else ""
        lines.append(f"**{source_name.capitalize()} Skills**: `{source_path}`{suffix}")
    return "\n".join(lines)


def _format_skills_list(skills_metadata: list[dict[str, Any]], source_paths: list[str]) -> str:
    if not skills_metadata:
        return f"(No skills available yet. You can create skills in {' or '.join(source_paths)})"

    lines: list[str] = []
    for skill in skills_metadata:
        name = str(skill.get("name") or "unknown-skill")
        description = str(skill.get("description") or "No description provided.")
        annotations = _format_skill_annotations(skill)
        path = str(skill.get("path") or "")
        allowed_tools = [
            str(item).strip()
            for item in _coerce_list(skill.get("allowed_tools"))
            if str(item).strip()
        ]

        line = f"- **{name}**: {description}"
        if annotations:
            line += f" ({annotations})"
        lines.append(line)
        if allowed_tools:
            lines.append(f"  -> Allowed tools: {', '.join(allowed_tools)}")
        if path:
            lines.append(f"  -> Read `{path}` for full instructions")
    return "\n".join(lines)


def build_prompt_debug_snapshot(
    *,
    conversation_id: str,
    llm_model: str,
    working_directory: str,
    prompt_bundle: dict[str, str],
    selected_skill: dict[str, Any] | None,
    turn_instruction: str | None,
    captured_request: dict[str, Any],
) -> dict[str, Any]:
    prompt_bundle = _coerce_dict(prompt_bundle)
    captured_request = _coerce_dict(captured_request)
    captured_state = _coerce_dict(captured_request.get("state"))
    memory_contents = {
        str(path): str(content)
        for path, content in _coerce_dict(captured_state.get("memory_contents")).items()
        if isinstance(path, str) and isinstance(content, str)
    }
    skills_metadata = [
        _coerce_dict(skill)
        for skill in _coerce_list(captured_state.get("skills_metadata"))
        if isinstance(skill, dict)
    ]
    skill_sources = get_enabled_skill_sources()

    layers: list[dict[str, Any]] = []

    system_prompt_template = str(prompt_bundle.get("system_prompt") or "")
    resolved_system_prompt = _safe_format(
        system_prompt_template,
        working_directory=working_directory,
    )
    if resolved_system_prompt:
        layers.append(
            {
                "id": "system_prompt",
                "title": "System Prompt",
                "source": "conversation prompt snapshot",
                "content": resolved_system_prompt,
            }
        )

    if turn_instruction:
        layers.append(
            {
                "id": "selected_skill_turn_instruction",
                "title": "Selected Skill Turn Instruction",
                "source": "turn-specific skill preload",
                "content": turn_instruction,
            }
        )

    base_agent_prompt = str(prompt_bundle.get(BASE_AGENT_PROMPT_ID) or "")
    if base_agent_prompt:
        layers.append(
            {
                "id": BASE_AGENT_PROMPT_ID,
                "title": "Base Agent Prompt",
                "source": "deepagents base prompt",
                "content": base_agent_prompt,
            }
        )

    todo_system_prompt = str(prompt_bundle.get(TODO_SYSTEM_PROMPT_ID) or "")
    if todo_system_prompt:
        layers.append(
            {
                "id": TODO_SYSTEM_PROMPT_ID,
                "title": "Todo Middleware Prompt",
                "source": "TodoListMiddleware",
                "content": todo_system_prompt,
            }
        )

    memory_system_prompt = str(prompt_bundle.get(MEMORY_SYSTEM_PROMPT_ID) or "")
    if memory_system_prompt:
        layers.append(
            {
                "id": MEMORY_SYSTEM_PROMPT_ID,
                "title": "Memory Middleware Prompt",
                "source": "MemoryMiddleware",
                "content": _format_memory_section(memory_contents, memory_system_prompt),
            }
        )

    skills_system_prompt = str(prompt_bundle.get(SKILLS_SYSTEM_PROMPT_ID) or "")
    if skills_system_prompt:
        layers.append(
            {
                "id": SKILLS_SYSTEM_PROMPT_ID,
                "title": "Skills Middleware Prompt",
                "source": "SkillsMiddleware",
                "content": skills_system_prompt.format(
                    skills_locations=_format_skills_locations(skill_sources),
                    skills_list=_format_skills_list(skills_metadata, skill_sources),
                ),
            }
        )

    task_system_prompt = str(prompt_bundle.get(TASK_SYSTEM_PROMPT_ID) or "")
    if task_system_prompt:
        layers.append(
            {
                "id": TASK_SYSTEM_PROMPT_ID,
                "title": "Subagent Middleware Prompt",
                "source": "SubAgentMiddleware",
                "content": (
                    f"{task_system_prompt}\n\n"
                    "Available subagent types:\n"
                    f"- general-purpose: {DEFAULT_GENERAL_PURPOSE_DESCRIPTION}"
                ),
            }
        )

    filesystem_system_prompt = str(prompt_bundle.get(FILESYSTEM_SYSTEM_PROMPT_ID) or "")
    if filesystem_system_prompt:
        layers.append(
            {
                "id": FILESYSTEM_SYSTEM_PROMPT_ID,
                "title": "Filesystem Middleware Prompt",
                "source": "FilesystemMiddleware",
                "content": filesystem_system_prompt,
            }
        )

    local_context = str(captured_state.get("local_context") or "").strip()
    if local_context:
        layers.append(
            {
                "id": "local_context",
                "title": "Local Context",
                "source": "ClawLocalContextMiddleware",
                "content": local_context,
            }
        )

    summarization_tool_system_prompt = str(prompt_bundle.get(SUMMARIZATION_TOOL_SYSTEM_PROMPT_ID) or "")
    if summarization_tool_system_prompt:
        layers.append(
            {
                "id": SUMMARIZATION_TOOL_SYSTEM_PROMPT_ID,
                "title": "Summarization Tool Prompt",
                "source": "SummarizationToolMiddleware",
                "content": summarization_tool_system_prompt,
            }
        )

    selected_skill_summary = None
    if isinstance(selected_skill, dict):
        selected_skill_summary = {
            "name": str(selected_skill.get("name") or ""),
            "declared_name": str(selected_skill.get("declared_name") or ""),
            "description": str(selected_skill.get("description") or ""),
            "aliases": [
                str(alias).strip()
                for alias in _coerce_list(selected_skill.get("aliases"))
                if str(alias).strip()
            ],
            "path": str(selected_skill.get("skill_file_path") or selected_skill.get("path") or ""),
        }

    return {
        "version": "claw.prompt_debug.v1",
        "captured_at": captured_request.get("captured_at"),
        "conversation": {
            "id": conversation_id,
            "llm_model": llm_model,
            "working_directory": working_directory,
        },
        "selected_skill": selected_skill_summary,
        "prompt_layers": layers,
        "captured_request": {
            "system_prompt": str(captured_request.get("system_prompt") or ""),
            "message_count": int(captured_request.get("message_count") or 0),
            "messages": _coerce_list(captured_request.get("messages")),
            "tool_count": int(captured_request.get("tool_count") or 0),
            "tools": _coerce_list(captured_request.get("tools")),
        },
        "resolved_state": {
            "local_context": local_context,
            "memory_contents": memory_contents,
            "skills_source_paths": skill_sources,
            "skills_loaded": skills_metadata,
            "summarization_event": captured_state.get("summarization_event"),
        },
    }


class ClawPromptDebugCaptureMiddleware(AgentMiddleware):
    """Capture the fully transformed model request after all prompt middleware runs."""

    def __init__(self, on_capture: PromptDebugCaptureCallback) -> None:
        self._on_capture = on_capture
        self._captured = False

    def _capture(self, request: ModelRequest[Any]) -> None:
        if self._captured:
            return

        try:
            self._on_capture(serialize_model_request(request))
            self._captured = True
        except Exception:
            logger.warning("Failed to capture prompt debug request snapshot", exc_info=True)

    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any]:
        self._capture(request)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        self._capture(request)
        return await handler(request)
