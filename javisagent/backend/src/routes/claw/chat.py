import hashlib
import json
import logging
import os
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, ToolMessage
from sqlalchemy.orm import Session

from src.models import get_db
from src.models.claw import (
    ClawConversation,
    ClawConversationPromptSnapshot,
    ClawMessage,
    ClawProcessEvent,
    ClawToolCall,
    MessageRole,
    ToolCallStatus,
)
from src.schemas.claw import MessageCreate, MessageResponse
from src.services.claw import create_claw_agent
from src.services.claw.prompt_debug import build_prompt_debug_snapshot
from src.services.claw.prompt_registry import (
    SYSTEM_PROMPT_ID,
    build_deep_agent_prompt_overrides,
    get_current_prompt_bundle,
    get_system_prompt_from_bundle,
    normalize_prompt_bundle,
)
from src.services.claw.skill_registry import (
    extract_slash_skill_command,
    get_skill_detail,
    resolve_skill_reference,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/claw", tags=["claw-chat"])

SHELL_TOOL_NAMES = {"shell", "bash", "execute"}
PLANNING_TOOL_NAMES = {"write_todos"}
SUBAGENT_TOOL_NAMES = {"task"}
REPEAT_QUERY_CACHE_WINDOW = timedelta(minutes=10)
TERMINAL_PROCESS_STATUSES = {"success", "completed", "failed"}
_UNSET = object()
SUBAGENT_DEBUG_ENV = "CLAW_SUBAGENT_DEBUG"


def _normalize_tool_name(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _sanitize_tool_call_id(value: Any) -> str:
    return str(value).replace(".", "_").replace("/", "_").replace("\\", "_") if value else ""


def _extract_text_content(content: str | list) -> str:
    """从多模态 content 中提取纯文本，用于存入数据库。"""
    if isinstance(content, str):
        return content
    parts = [
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return " ".join(parts) or "[图片]"


def _count_images(content: str | list) -> int:
    """统计 content 中的图片数量。"""
    if isinstance(content, str):
        return 0
    return sum(
        1 for block in content
        if isinstance(block, dict) and block.get("type") == "image_url"
    )


def _ensure_conversation_prompt_snapshot(
    conversation: ClawConversation,
    db: Session,
) -> dict[str, str]:
    current_prompt_bundle = get_current_prompt_bundle()
    snapshot = conversation.prompt_snapshot
    stored_prompt_bundle = normalize_prompt_bundle(
        snapshot.prompt_bundle if snapshot is not None else None
    )

    prompt_bundle = {**current_prompt_bundle, **stored_prompt_bundle}
    if conversation.system_prompt:
        prompt_bundle[SYSTEM_PROMPT_ID] = stored_prompt_bundle.get(
            SYSTEM_PROMPT_ID,
            conversation.system_prompt,
        )

    if snapshot is None:
        conversation.prompt_snapshot = ClawConversationPromptSnapshot(
            conversation_id=str(conversation.id),
            prompt_bundle=prompt_bundle,
        )
        db.add(conversation.prompt_snapshot)
        db.commit()
        db.refresh(conversation)
        return prompt_bundle

    if snapshot.prompt_bundle != prompt_bundle:
        snapshot.prompt_bundle = prompt_bundle
        db.commit()
        db.refresh(conversation)

    return prompt_bundle


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
    return json.dumps(_jsonable(value), ensure_ascii=False)


def _sse_event(event_type: str, **payload: Any) -> str:
    return f"data: {json.dumps({'type': event_type, **payload}, ensure_ascii=False)}\n\n"


def _iter_content_blocks(message: AIMessage | ToolMessage) -> list[dict[str, Any]]:
    blocks = getattr(message, "content_blocks", None)
    if blocks:
        return blocks

    content = getattr(message, "content", None)
    if isinstance(content, str) and content:
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


def _tool_call_blocks_from_message(message: AIMessage, existing_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_ids = {
        block.get("id")
        for block in existing_blocks
        if block.get("type") in {"tool_call", "tool_call_chunk"} and block.get("id")
    }
    extra_blocks: list[dict[str, Any]] = []

    for tool_call in getattr(message, "tool_calls", []) or []:
        if not isinstance(tool_call, dict):
            continue

        tool_name = tool_call.get("name")
        if not tool_name:
            continue

        tool_id = tool_call.get("id")
        if tool_id and tool_id in seen_ids:
            continue

        extra_blocks.append(
            {
                "type": "tool_call",
                "id": tool_id,
                "name": tool_name,
                "args": tool_call.get("args", {}),
            }
        )

    return extra_blocks


def _tool_call_chunk_blocks_from_message(
    message: AIMessage,
    existing_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_chunks = getattr(message, "tool_call_chunks", None)
    if not isinstance(raw_chunks, list):
        return []

    seen_signatures = {
        (
            str(block.get("id") or ""),
            block.get("index"),
            str(block.get("name") or ""),
            json.dumps(_jsonable(block.get("args")), ensure_ascii=False, sort_keys=True),
        )
        for block in existing_blocks
        if block.get("type") == "tool_call_chunk"
    }
    extra_blocks: list[dict[str, Any]] = []

    for raw_chunk in raw_chunks:
        if not isinstance(raw_chunk, dict):
            continue

        signature = (
            str(raw_chunk.get("id") or ""),
            raw_chunk.get("index"),
            str(raw_chunk.get("name") or ""),
            json.dumps(_jsonable(raw_chunk.get("args")), ensure_ascii=False, sort_keys=True),
        )
        if signature in seen_signatures:
            continue

        block = {
            "type": "tool_call_chunk",
            "id": raw_chunk.get("id"),
            "name": raw_chunk.get("name"),
            "args": raw_chunk.get("args"),
        }
        if raw_chunk.get("index") is not None:
            block["index"] = raw_chunk["index"]

        extra_blocks.append(block)
        seen_signatures.add(signature)

    return extra_blocks


def _tool_call_blocks_from_additional_kwargs(
    message: AIMessage,
    existing_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    additional_kwargs = getattr(message, "additional_kwargs", None)
    if not isinstance(additional_kwargs, dict):
        return []

    seen_ids = {
        str(block.get("id"))
        for block in existing_blocks
        if block.get("type") in {"tool_call", "tool_call_chunk"} and block.get("id") is not None
    }
    seen_signatures = {
        (
            str(block.get("name") or ""),
            json.dumps(_jsonable(block.get("args")), ensure_ascii=False, sort_keys=True),
        )
        for block in existing_blocks
        if block.get("type") in {"tool_call", "tool_call_chunk"} and block.get("name")
    }
    extra_blocks: list[dict[str, Any]] = []

    def add_candidate(
        *,
        tool_id: Any = None,
        tool_name: Any = None,
        tool_args: Any = None,
        index: int | None = None,
    ) -> None:
        normalized_name = str(tool_name).strip() if tool_name is not None else ""
        if not normalized_name and tool_args is None:
            return

        normalized_id = str(tool_id).strip() if tool_id is not None else ""
        if normalized_id and normalized_id in seen_ids:
            return

        signature = (
            normalized_name,
            json.dumps(_jsonable(tool_args), ensure_ascii=False, sort_keys=True),
        )
        if signature in seen_signatures:
            return

        block: dict[str, Any] = {
            "type": "tool_call",
            "name": normalized_name or None,
            "args": tool_args,
        }
        if normalized_id:
            block["id"] = normalized_id
            seen_ids.add(normalized_id)
        if index is not None:
            block["index"] = index

        seen_signatures.add(signature)
        extra_blocks.append(block)

    raw_tool_calls = additional_kwargs.get("tool_calls")
    if isinstance(raw_tool_calls, list):
        for index, raw_tool_call in enumerate(raw_tool_calls):
            if not isinstance(raw_tool_call, dict):
                continue

            function_payload = raw_tool_call.get("function")
            tool_name = raw_tool_call.get("name")
            tool_args = raw_tool_call.get("arguments") or raw_tool_call.get("args")
            if isinstance(function_payload, dict):
                tool_name = function_payload.get("name") or tool_name
                tool_args = function_payload.get("arguments") or tool_args

            add_candidate(
                tool_id=raw_tool_call.get("id") or raw_tool_call.get("tool_call_id"),
                tool_name=tool_name,
                tool_args=tool_args,
                index=index,
            )

    raw_function_call = additional_kwargs.get("function_call")
    if isinstance(raw_function_call, dict):
        add_candidate(
            tool_id=raw_function_call.get("id") or raw_function_call.get("tool_call_id"),
            tool_name=raw_function_call.get("name"),
            tool_args=raw_function_call.get("arguments") or raw_function_call.get("args"),
            index=0,
        )

    return extra_blocks


def _find_todos(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, dict):
        todos = payload.get("todos")
        if isinstance(todos, list):
            return _jsonable(todos)
        for value in payload.values():
            found = _find_todos(value)
            if found is not None:
                return found
        return None

    if isinstance(payload, list):
        if payload and all(
            isinstance(item, dict)
            and isinstance(item.get("status"), str)
            and any(
                isinstance(item.get(key), str) and item.get(key)
                for key in ("content", "title", "task", "id")
            )
            for item in payload
        ):
            return _jsonable(payload)
        for item in payload:
            found = _find_todos(item)
            if found is not None:
                return found
        return None

    if isinstance(payload, str):
        stripped = payload.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        return _find_todos(parsed)

    return None


def _derive_planning_status(todos: list[dict[str, Any]]) -> str:
    if not todos:
        return "pending"

    statuses = {str(item.get("status", "pending")) for item in todos if isinstance(item, dict)}
    if "in_progress" in statuses:
        return "in_progress"
    if statuses and statuses <= {"completed"}:
        return "completed"
    return "pending"


def _is_terminal_process_status(value: Any) -> bool:
    return str(value) in TERMINAL_PROCESS_STATUSES


def _preserve_terminal_status(current_status: Any, next_status: str) -> str:
    if _is_terminal_process_status(current_status) and not _is_terminal_process_status(next_status):
        return str(current_status)
    return next_status


def _todo_merge_key(todo: Any) -> str:
    if not isinstance(todo, dict):
        return ""

    for key in ("id", "content", "title", "task"):
        value = todo.get(key)
        if isinstance(value, str) and value.strip():
            return f"{key}:{value.strip()}"

    return ""


def _merge_todos(existing: Any, incoming: Any) -> list[dict[str, Any]]:
    normalized_existing = [
        dict(item) for item in _jsonable(existing or []) if isinstance(item, dict)
    ]
    normalized_incoming = [
        dict(item) for item in _jsonable(incoming or []) if isinstance(item, dict)
    ]

    if not normalized_existing:
        return normalized_incoming
    if not normalized_incoming:
        return normalized_existing

    merged = [dict(item) for item in normalized_existing]
    key_to_index = {
        key: index
        for index, item in enumerate(merged)
        if (key := _todo_merge_key(item))
    }

    for item in normalized_incoming:
        key = _todo_merge_key(item)
        if key and key in key_to_index:
            merged[key_to_index[key]] = {**merged[key_to_index[key]], **item}
            continue
        merged.append(dict(item))
        if key:
            key_to_index[key] = len(merged) - 1

    return merged


def _derive_shell_command(tool_input: Any) -> str:
    if isinstance(tool_input, str) and tool_input:
        return tool_input

    if not isinstance(tool_input, dict):
        return ""

    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value

    commands = tool_input.get("commands")
    if isinstance(commands, list):
        parts = [part.strip() for part in commands if isinstance(part, str) and part.strip()]
        if parts:
            return " && ".join(parts)

    argv = tool_input.get("args")
    if isinstance(argv, list):
        parts = [str(part).strip() for part in argv if str(part).strip()]
        if parts:
            return " ".join(parts)

    return ""


def _extract_shell_command_from_text(output: str) -> str:
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        for pattern in (
            r"^'([^'\r\n]+)'\s+不是内部或外部命令",
            r"^'([^'\r\n]+)'\s+is not recognized as an internal or external command",
            r"^([^:\r\n]+)\s*:\s+The term '([^'\r\n]+)' is not recognized as the name of a cmdlet",
            r"^(?:/bin/sh:\s*\d+:\s*)?([^\s:]+):\s+(?:not found|command not found)",
            r"^bash:\s+([^\s:]+):\s+command not found",
        ):
            match = re.search(pattern, line, re.IGNORECASE)
            if not match:
                continue

            for group in match.groups():
                if isinstance(group, str) and group.strip():
                    return group.strip()

    return ""


def _extract_shell_input_from_raw_args(raw_args: Any) -> dict[str, Any] | None:
    if not isinstance(raw_args, str):
        return None

    trimmed = raw_args.strip()
    if not trimmed:
        return None

    if trimmed.startswith("{") or trimmed.startswith("["):
        return None

    patterns = (
        r'"(?:command|cmd|script)"\s*:\s*"(?P<value>.+?)"(?:\s*[,}])?',
        r'"(?:command|cmd|script)"\s*:\s*"(?P<value>.+)$',
        r"(?:command|cmd|script)\s*[:=]\s*(?P<value>.+)$",
    )

    for pattern in patterns:
        match = re.search(pattern, trimmed, re.IGNORECASE)
        if not match:
            continue

        value = match.group("value").strip().rstrip(",}")
        if value.endswith('"'):
            value = value[:-1]
        value = value.replace('\\"', '"').replace("\\\\", "\\").strip()
        if value:
            return {"command": value}

    return None


def _parse_tool_call_args_dict(raw_args: Any) -> dict[str, Any] | None:
    if isinstance(raw_args, dict):
        return raw_args

    if not isinstance(raw_args, str):
        return None

    trimmed = raw_args.strip()
    if not trimmed:
        return None

    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def _merge_tool_call_arg_text(existing_text: str, new_text: str) -> str:
    if not existing_text:
        return new_text
    if not new_text:
        return existing_text
    if new_text.startswith(existing_text):
        return new_text
    if existing_text.startswith(new_text):
        return existing_text
    return f"{existing_text}{new_text}"


def _normalize_partial_tool_call_args(raw_args: Any, tool_name: str = "") -> dict[str, Any] | None:
    if raw_args is None:
        return None

    strict_dict = _parse_tool_call_args_dict(raw_args)
    if strict_dict is not None:
        return strict_dict

    if not isinstance(raw_args, str):
        return None

    stripped = raw_args.strip()
    if not stripped:
        return None

    normalized_tool_name = _normalize_tool_name(tool_name)
    if normalized_tool_name in SHELL_TOOL_NAMES:
        extracted = _extract_shell_input_from_raw_args(stripped)
        if extracted is not None:
            return extracted
        if stripped.startswith("{") or stripped.startswith("["):
            return None
        return {"command": stripped}

    return None


def _derive_subagent_title(tool_input: dict[str, Any]) -> str:
    for key in ("description", "task", "prompt", "subtask", "objective"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return "Subagent"


def _extract_tool_output(message: ToolMessage) -> Any:
    artifact = getattr(message, "artifact", None)
    if artifact is not None:
        return _jsonable(artifact)
    return _jsonable(getattr(message, "content", None))


def _merge_tool_input_from_message(
    tool_name: str,
    tool_input: dict[str, Any] | None,
    message: ToolMessage,
) -> dict[str, Any]:
    merged_input = dict(_jsonable(tool_input or {}))
    additional_kwargs = getattr(message, "additional_kwargs", None)
    normalized_tool_name = _normalize_tool_name(tool_name)

    if isinstance(additional_kwargs, dict):
        if normalized_tool_name == "read_file":
            read_file_path = additional_kwargs.get("read_file_path")
            has_path = any(
                isinstance(merged_input.get(key), str) and merged_input.get(key)
                for key in ("file_path", "path", "target_path")
            )
            if isinstance(read_file_path, str) and read_file_path and not has_path:
                merged_input["file_path"] = read_file_path

    if normalized_tool_name in SHELL_TOOL_NAMES:
        for source in (
            additional_kwargs if isinstance(additional_kwargs, dict) else None,
            getattr(message, "artifact", None),
            getattr(message, "content", None),
        ):
            if not isinstance(source, dict):
                continue

            for key in ("command", "cmd", "script", "commands", "args"):
                value = source.get(key)
                if value in (None, "", [], {}):
                    continue
                if merged_input.get(key) in (None, "", [], {}):
                    merged_input[key] = _jsonable(value)

        if not _derive_shell_command(merged_input):
            for source in (
                getattr(message, "content", None),
                merged_input.get("output"),
            ):
                if isinstance(source, str):
                    command_hint = _extract_shell_command_from_text(source)
                    if command_hint:
                        merged_input["command"] = command_hint
                        break

    return merged_input


def _merge_tool_call_args(existing_args: Any, new_args: Any) -> Any:
    if new_args is None:
        return existing_args

    if isinstance(new_args, dict):
        if isinstance(existing_args, dict):
            return {**existing_args, **new_args}
        if isinstance(existing_args, str):
            try:
                parsed_existing = json.loads(existing_args)
            except json.JSONDecodeError:
                return new_args if new_args else existing_args
            if isinstance(parsed_existing, dict):
                return {**parsed_existing, **new_args}
        return new_args

    return new_args


def _normalize_child_tool_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    records: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        records.append(dict(_jsonable(item)))
    return records


def _find_child_tool_index(
    child_tools: list[dict[str, Any]],
    *,
    tool_id: str | None = None,
    tool_name: str | None = None,
) -> int | None:
    normalized_tool_name = _normalize_tool_name(tool_name)
    sanitized_tool_id = _sanitize_tool_call_id(tool_id) if tool_id else ""

    for index, child_tool in enumerate(child_tools):
        existing_id = child_tool.get("id")
        if isinstance(existing_id, str) and tool_id and existing_id == tool_id:
            return index
        if (
            isinstance(existing_id, str)
            and sanitized_tool_id
            and _sanitize_tool_call_id(existing_id) == sanitized_tool_id
        ):
            return index

    if normalized_tool_name:
        running_matches = [
            index
            for index, child_tool in enumerate(child_tools)
            if (
                str(child_tool.get("status")) == "running"
                and _normalize_tool_name(child_tool.get("tool_name")) == normalized_tool_name
            )
        ]
        if len(running_matches) == 1:
            return running_matches[0]

    return None


def _upsert_child_tool_record(
    child_tools: list[dict[str, Any]],
    *,
    tool_id: str,
    tool_name: str,
    status: str,
    tool_input: Any = _UNSET,
    tool_output: Any = _UNSET,
    error: Any = _UNSET,
) -> list[dict[str, Any]]:
    next_child_tools = [dict(item) for item in _normalize_child_tool_records(child_tools)]
    index = _find_child_tool_index(next_child_tools, tool_id=tool_id, tool_name=tool_name)
    existing = next_child_tools[index] if index is not None else {}

    record = {
        **existing,
        "id": tool_id or existing.get("id") or f"tool_{uuid.uuid4().hex}",
        "tool_name": tool_name or existing.get("tool_name") or "tool",
        "status": status or existing.get("status") or "running",
    }

    if tool_input is not _UNSET:
        record["tool_input"] = _jsonable(tool_input)
    elif "tool_input" in existing:
        record["tool_input"] = existing["tool_input"]

    if tool_output is not _UNSET:
        record["tool_output"] = _jsonable(tool_output)
    elif "tool_output" in existing:
        record["tool_output"] = existing["tool_output"]

    if error is not _UNSET:
        if error in (None, ""):
            record.pop("error", None)
        else:
            record["error"] = _stringify(error)
    elif "error" in existing:
        record["error"] = existing["error"]

    if index is None:
        next_child_tools.append(record)
    else:
        next_child_tools[index] = record

    return next_child_tools


def _normalize_tool_call_args(raw_args: Any, tool_name: str = "") -> dict[str, Any] | None:
    if raw_args is None:
        logger.debug(f"_normalize_tool_call_args: raw_args is None for tool {tool_name}")
        return None

    parsed_args = raw_args
    if isinstance(parsed_args, str):
        logger.debug(f"_normalize_tool_call_args: raw_args is string: {repr(parsed_args[:100])} for tool {tool_name}")
        try:
            parsed_args = json.loads(parsed_args)
            logger.debug(f"_normalize_tool_call_args: successfully parsed JSON for tool {tool_name}")
        except json.JSONDecodeError:
            # 对于 shell 工具，如果是无法解析的字符串，尝试作为命令处理
            normalized_tool_name = _normalize_tool_name(tool_name)
            logger.debug(f"_normalize_tool_call_args: JSON parse failed, normalized_tool_name={normalized_tool_name}, is_shell={normalized_tool_name in SHELL_TOOL_NAMES}")
            if normalized_tool_name in SHELL_TOOL_NAMES and parsed_args.strip():
                result = {"command": parsed_args.strip()}
                logger.info(f"_normalize_tool_call_args: Converting string to command dict for shell tool: {result}")
                return result
            logger.debug(f"_normalize_tool_call_args: Returning None for non-shell tool or empty string")
            return None

    if not isinstance(parsed_args, dict):
        logger.debug(f"_normalize_tool_call_args: parsed_args is not dict, wrapping in value for tool {tool_name}")
        return {"value": parsed_args}

    logger.debug(f"_normalize_tool_call_args: returning dict with keys {list(parsed_args.keys())} for tool {tool_name}")
    return parsed_args


def _extract_shell_payload(message: ToolMessage, tool_input: dict[str, Any]) -> dict[str, Any]:
    def parse_combined_shell_output(output: str) -> dict[str, Any]:
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        exit_code: int | None = None

        for raw_line in output.splitlines():
            line = raw_line.rstrip()
            if line.startswith("[stderr] "):
                stderr_lines.append(line[len("[stderr] ") :])
                continue
            if line.startswith("Exit code: "):
                try:
                    exit_code = int(line[len("Exit code: ") :].strip())
                except ValueError:
                    pass
                continue
            if line.startswith("[Command failed with exit code"):
                continue
            if line == "<no output>":
                continue
            stdout_lines.append(line)

        return {
            "stdout": "\n".join(stdout_lines).strip(),
            "stderr": "\n".join(stderr_lines).strip(),
            "exit_code": exit_code,
            "output": output,
        }

    payload: dict[str, Any] = {}

    artifact = getattr(message, "artifact", None)
    if isinstance(artifact, dict):
        payload.update(_jsonable(artifact))

    content = getattr(message, "content", None)
    if isinstance(content, dict):
        payload.update(_jsonable(content))
    elif isinstance(content, str) and content:
        parsed_output = parse_combined_shell_output(content)
        if parsed_output["stdout"]:
            payload.setdefault("stdout", parsed_output["stdout"])
        if parsed_output["stderr"]:
            payload.setdefault("stderr", parsed_output["stderr"])
        if parsed_output["exit_code"] is not None:
            payload.setdefault("exit_code", parsed_output["exit_code"])
        payload.setdefault("output", parsed_output["output"])

    command = ""
    raw_command = payload.get("command")
    if isinstance(raw_command, str) and raw_command.strip():
        command = raw_command.strip()

    if not command:
        command = _derive_shell_command(tool_input)

    if not command:
        for source in (payload.get("stderr"), payload.get("output"), payload.get("stdout")):
            if isinstance(source, str):
                command = _extract_shell_command_from_text(source)
                if command:
                    break

    payload["command"] = command
    if "exit_code" not in payload:
        payload["exit_code"] = 0 if getattr(message, "status", "success") == "success" else None
    payload.setdefault("stderr", "")
    if "stdout" not in payload:
        payload["stdout"] = "" if payload.get("stderr") else payload.get("output", "")
    return payload


def _flatten_namespace_parts(namespace: tuple[Any, ...]) -> list[str]:
    parts: list[str] = []

    def visit(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                visit(item)
            return
        parts.append(str(value))

    visit(namespace)
    return [part for part in parts if part]


def _normalize_subagent_namespace(namespace: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(
        part
        for part in _flatten_namespace_parts(namespace)
        if not (part == "tools" or part.startswith("tools:"))
    )


def _collect_embedded_stream_messages(payload: Any) -> list[AIMessage | ToolMessage]:
    messages: list[AIMessage | ToolMessage] = []
    seen_ids: set[int] = set()

    def visit(value: Any) -> None:
        if isinstance(value, (AIMessage, ToolMessage)):
            object_id = id(value)
            if object_id in seen_ids:
                return
            seen_ids.add(object_id)
            messages.append(value)
            return

        if isinstance(value, dict):
            embedded_messages = value.get("messages")
            if isinstance(embedded_messages, list):
                for embedded_message in embedded_messages:
                    visit(embedded_message)
            for child in value.values():
                if child is embedded_messages:
                    continue
                visit(child)
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    visit(payload)
    return messages


def _subagent_debug_enabled() -> bool:
    return os.getenv(SUBAGENT_DEBUG_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _subagent_debug_summary(value: Any) -> Any:
    if isinstance(value, dict):
        summary: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, dict):
                summary[key] = list(item.keys())
            elif isinstance(item, list):
                summary[key] = f"list[{len(item)}]"
            else:
                summary[key] = type(item).__name__
        return summary
    if isinstance(value, list):
        return f"list[{len(value)}]"
    return type(value).__name__


def _serialize_tool_call(tool_call: ClawToolCall) -> dict[str, Any]:
    return {
        "id": tool_call.id,
        "tool_name": tool_call.tool_name,
        "tool_input": tool_call.tool_input,
        "tool_output": tool_call.tool_output,
        "status": tool_call.status.value,
        "duration": tool_call.duration,
        "error": tool_call.error,
    }


def _serialize_process_event(process_event: ClawProcessEvent) -> dict[str, Any]:
    return {
        "id": process_event.id,
        "kind": process_event.kind,
        "title": process_event.title,
        "status": process_event.status,
        "sequence": process_event.sequence,
        "data": process_event.data or {},
        "created_at": process_event.created_at,
        "updated_at": process_event.updated_at,
    }


def _normalize_user_message(content: str) -> str:
    return " ".join(content.split()).strip()


def _find_recent_duplicate_reply(
    conv_id: UUID,
    user_message: str,
    selected_skill: str | None,
    selected_skill_revision: str | None,
    db: Session,
) -> ClawMessage | None:
    normalized_message = _normalize_user_message(user_message)
    if not normalized_message:
        return None

    recent_messages = (
        db.query(ClawMessage)
        .filter_by(conversation_id=str(conv_id))
        .order_by(ClawMessage.created_at.desc())
        .limit(2)
        .all()
    )
    if len(recent_messages) < 2:
        return None

    latest_message, previous_message = recent_messages[0], recent_messages[1]
    if latest_message.role != MessageRole.ASSISTANT or previous_message.role != MessageRole.USER:
        return None
    if _normalize_user_message(previous_message.content) != normalized_message:
        return None
    previous_selected_skill = (previous_message.extra_data or {}).get("selected_skill")
    if previous_selected_skill != selected_skill:
        return None
    previous_selected_skill_revision = (previous_message.extra_data or {}).get(
        "selected_skill_revision"
    )
    if previous_selected_skill_revision != selected_skill_revision:
        return None
    if not latest_message.content.strip():
        return None
    if datetime.utcnow() - latest_message.created_at > REPEAT_QUERY_CACHE_WINDOW:
        return None

    return latest_message


def _fingerprint_selected_skill_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _build_selected_skill_turn_instruction(skill: dict[str, Any]) -> str:
    description = str(skill.get("description") or "").strip()
    declared_name = str(skill.get("declared_name") or "").strip()
    skill_content = str(skill.get("content") or "").strip()
    skill_path = str(skill.get("skill_file_path") or skill.get("path") or "").strip()
    aliases = [
        str(alias).strip()
        for alias in skill.get("aliases", [])
        if str(alias).strip()
    ]
    label = skill["name"]
    if declared_name and declared_name.lower() != label.lower():
        label = f"{label} ({declared_name})"

    lines = [
        "# User-requested Skill For This Turn",
        f"The user explicitly requested that you use the enabled skill `{label}` for this turn.",
    ]
    if aliases:
        lines.append(f"Requested via slash alias: `/{aliases[0]}`.")
    if description:
        lines.append(f"Skill summary: {description}")
    if skill_path:
        lines.append(f"The full contents of `{skill_path}` are preloaded below.")
    lines.extend(
        [
            "Treat the preloaded skill file as authoritative instructions for this turn.",
            "You do not need to read the main `SKILL.md` again unless you need to verify or inspect supporting files referenced by it.",
        ]
    )
    if skill_content:
        lines.extend(
            [
                "",
                "<preloaded_skill_file>",
                skill_content,
                "</preloaded_skill_file>",
            ]
        )
    lines.append("This instruction applies only to the current user turn.")
    return "\n".join(lines)


def _build_selected_skill_metadata(skill: dict[str, Any] | None) -> dict[str, Any]:
    if skill is None:
        return {}

    aliases = [
        str(alias).strip()
        for alias in skill.get("aliases", [])
        if str(alias).strip()
    ]
    skill_content = str(skill.get("content") or "")
    skill_path = str(skill.get("skill_file_path") or skill.get("path") or "").strip()
    return {
        "selected_skill": skill["name"],
        "selected_skill_alias": aliases[0] if aliases else skill["name"],
        "selected_skill_file_path": skill_path,
        "selected_skill_preloaded": bool(skill_content.strip()),
        "selected_skill_revision": _fingerprint_selected_skill_content(skill_content),
    }


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
async def get_messages(conv_id: UUID, db: Session = Depends(get_db)):
    conversation = db.query(ClawConversation).filter_by(id=str(conv_id)).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(ClawMessage)
        .filter_by(conversation_id=str(conv_id))
        .order_by(ClawMessage.created_at)
        .all()
    )

    result = []
    for message in messages:
        tool_calls = sorted(message.tool_calls, key=lambda item: item.created_at)
        process_events = sorted(message.process_events, key=lambda item: item.sequence)
        result.append(
            {
                "id": message.id,
                "role": message.role.value,
                "content": message.content,
                "metadata": message.extra_data or {},
                "tool_calls": [_serialize_tool_call(tool_call) for tool_call in tool_calls],
                "process_events": [
                    _serialize_process_event(process_event) for process_event in process_events
                ],
                "created_at": message.created_at,
            }
        )

    return result


async def chat_event_generator(
    conv_id: UUID,
    user_message: str,
    conversation: ClawConversation,
    db: Session,
    selected_skill_name: str | None = None,
) -> AsyncGenerator[str, None]:
    user_record: ClawMessage | None = None
    assistant_message: ClawMessage | None = None
    assistant_fragments: list[str] = []
    timeline_entries: list[dict[str, Any]] = []
    tool_call_buffers: dict[str | int, dict[str, Any]] = {}
    subagent_tool_call_buffers: dict[str, dict[str, Any]] = {}
    tool_records: dict[str, ClawToolCall] = {}
    process_events: dict[str, ClawProcessEvent] = {}
    pending_subagent_tool_ids: list[str] = []
    namespace_to_subagent_id: dict[tuple[str, ...], str] = {}
    planning_item_id: str | None = None
    process_sequence = 0
    next_text_timeline_index = 1
    current_text_timeline_id: str | None = None
    selected_skill = (
        get_skill_detail(resolve_skill_reference(selected_skill_name, enabled_only=True)["name"])
        if selected_skill_name
        else None
    )
    selected_skill_metadata = _build_selected_skill_metadata(selected_skill)
    selected_skill_turn_instruction = (
        _build_selected_skill_turn_instruction(selected_skill)
        if selected_skill is not None
        else None
    )
    should_capture_prompt_debug = (
        db.query(ClawMessage.id)
        .filter_by(conversation_id=str(conv_id))
        .first()
        is None
    )
    prompt_debug_snapshot: dict[str, Any] | None = None
    prompt_debug_persisted = False
    prompt_debug_emitted = False

    def touch_conversation() -> None:
        conversation.updated_at = datetime.utcnow()

    def persist_prompt_debug_snapshot() -> None:
        nonlocal prompt_debug_persisted
        if prompt_debug_persisted or prompt_debug_snapshot is None or user_record is None:
            return

        metadata = dict(user_record.extra_data or {})
        metadata["prompt_debug"] = prompt_debug_snapshot
        user_record.extra_data = metadata
        db.commit()
        prompt_debug_persisted = True

    def persist_stream_snapshot(stream_in_progress: bool = True) -> None:
        if assistant_message is None:
            return

        assistant_message.content = "".join(assistant_fragments)
        metadata: dict[str, Any] = {
            "stream_protocol": "claw.v2",
            "tool_call_count": len(tool_records),
            "process_event_count": len(process_events),
            "timeline": _jsonable(timeline_entries),
        }
        if stream_in_progress:
            metadata["stream_in_progress"] = True
        assistant_message.extra_data = metadata
        touch_conversation()
        db.commit()

    def append_timeline_text(text: str) -> None:
        nonlocal current_text_timeline_id, next_text_timeline_index
        if not text:
            return

        if current_text_timeline_id is None:
            current_text_timeline_id = f"text:{assistant_message.id}:{next_text_timeline_index}"
            next_text_timeline_index += 1
            timeline_entries.append(
                {
                    "kind": "text",
                    "item_id": current_text_timeline_id,
                    "content": text,
                }
            )
            return

        for entry in reversed(timeline_entries):
            if entry.get("item_id") == current_text_timeline_id:
                entry["content"] = f"{entry.get('content', '')}{text}"
                return

    def append_timeline_item(
        kind: str,
        *,
        item_id: str | None = None,
        tool_id: str | None = None,
    ) -> None:
        nonlocal current_text_timeline_id
        current_text_timeline_id = None

        for entry in timeline_entries:
            if entry.get("kind") != kind:
                continue

            if item_id is not None and entry.get("item_id") == item_id:
                if tool_id is not None and not entry.get("tool_id"):
                    entry["tool_id"] = tool_id
                return

            if tool_id is not None and entry.get("tool_id") == tool_id:
                if item_id is not None and not entry.get("item_id"):
                    entry["item_id"] = item_id
                return

        entry: dict[str, Any] = {"kind": kind}
        if item_id is not None:
            entry["item_id"] = item_id
        if tool_id is not None:
            entry["tool_id"] = tool_id
        timeline_entries.append(entry)

    def upsert_process_event(
        item_id: str,
        *,
        kind: str,
        title: str,
        status: str,
        data: dict[str, Any] | None = None,
    ) -> ClawProcessEvent:
        nonlocal process_sequence
        payload = _jsonable(data or {})
        process_event = process_events.get(item_id)

        if process_event is None:
            process_sequence += 1
            process_event = ClawProcessEvent(
                id=item_id,
                message_id=assistant_message.id,
                sequence=process_sequence,
                kind=kind,
                title=title,
                status=status,
                data=payload,
            )
            db.add(process_event)
            process_events[item_id] = process_event
        else:
            process_event.kind = kind
            process_event.title = title
            process_event.status = status
            process_event.data = payload

        db.flush()
        return process_event

    def ensure_tool_record(
        tool_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> ClawToolCall:
        tool_record = tool_records.get(tool_id)
        payload = _jsonable(tool_input)

        if tool_record is None:
            tool_record = ClawToolCall(
                id=tool_id,
                message_id=assistant_message.id,
                tool_name=tool_name,
                tool_input=payload,
                status=ToolCallStatus.RUNNING,
            )
            db.add(tool_record)
            tool_records[tool_id] = tool_record
        else:
            tool_record.tool_name = tool_name
            tool_record.tool_input = payload

        db.flush()
        return tool_record

    def ensure_subagent_binding(namespace: tuple[Any, ...]) -> tuple[ClawProcessEvent, bool]:
        created = False
        normalized_namespace = _normalize_subagent_namespace(namespace)
        item_id = resolve_subagent_item_id_for_namespace(namespace, allow_pending=True)

        if item_id is None:
            if pending_subagent_tool_ids:
                tool_id = pending_subagent_tool_ids.pop(0)
                item_id = f"subagent:{tool_id}"
            else:
                item_id = f"subagent:{uuid.uuid4().hex}"
                created = True
            namespace_to_subagent_id[normalized_namespace] = item_id

        process_event = process_events.get(item_id)
        if process_event is None:
            title = " / ".join(normalized_namespace) or "Subagent"
            process_event = upsert_process_event(
                item_id,
                kind="subagent",
                title=title,
                status="running",
                data={
                    "namespace": list(normalized_namespace),
                    "transcript": "",
                    "child_tools": [],
                },
            )
            created = True
        else:
            data = dict(process_event.data or {})
            data["namespace"] = list(normalized_namespace)
            process_event = upsert_process_event(
                item_id,
                kind="subagent",
                title=process_event.title,
                status=process_event.status,
                data=data,
            )

        return process_event, created

    def resolve_tool_id(tool_message: ToolMessage) -> str:
        tool_id = getattr(tool_message, "tool_call_id", None)
        tool_name = getattr(tool_message, "name", None)
        normalized_tool_name = _normalize_tool_name(tool_name)
        if tool_id:
            normalized_tool_id = str(tool_id)
            if normalized_tool_id in tool_records:
                return normalized_tool_id

            sanitized_tool_id = _sanitize_tool_call_id(normalized_tool_id)
            sanitized_matches = [
                existing_id
                for existing_id, tool_record in tool_records.items()
                if (
                    tool_record.status == ToolCallStatus.RUNNING
                    and (
                        existing_id == sanitized_tool_id
                        or _sanitize_tool_call_id(existing_id) == normalized_tool_id
                        or _sanitize_tool_call_id(existing_id) == sanitized_tool_id
                    )
                    and (
                        not normalized_tool_name
                        or _normalize_tool_name(tool_record.tool_name) == normalized_tool_name
                    )
                )
            ]
            if len(sanitized_matches) == 1:
                return sanitized_matches[0]

        if normalized_tool_name:
            running_name_matches = [
                existing_id
                for existing_id, tool_record in tool_records.items()
                if (
                    tool_record.status == ToolCallStatus.RUNNING
                    and _normalize_tool_name(tool_record.tool_name) == normalized_tool_name
                )
            ]
            if len(running_name_matches) == 1:
                return running_name_matches[0]

        if tool_id:
            return str(tool_id)

        return f"tool_{uuid.uuid4().hex}"

    def should_track_subagent_namespace(namespace: tuple[Any, ...]) -> bool:
        return resolve_subagent_item_id_for_namespace(namespace, allow_pending=True) is not None

    def resolve_subagent_child_tool_id(
        process_event: ClawProcessEvent,
        tool_message: ToolMessage,
    ) -> str:
        raw_tool_id = getattr(tool_message, "tool_call_id", None)
        tool_name = getattr(tool_message, "name", None)
        child_tools = _normalize_child_tool_records((process_event.data or {}).get("child_tools"))

        if raw_tool_id:
            tool_id = str(raw_tool_id)
            index = _find_child_tool_index(child_tools, tool_id=tool_id, tool_name=tool_name)
            if index is not None:
                existing_id = child_tools[index].get("id")
                if isinstance(existing_id, str) and existing_id:
                    return existing_id
            return tool_id

        index = _find_child_tool_index(child_tools, tool_name=tool_name)
        if index is not None:
            existing_id = child_tools[index].get("id")
            if isinstance(existing_id, str) and existing_id:
                return existing_id

        return f"tool_{uuid.uuid4().hex}"

    def get_active_subagent_item_ids() -> list[str]:
        return [
            item_id
            for item_id, process_event in process_events.items()
            if process_event.kind == "subagent"
            and not _is_terminal_process_status(process_event.status)
        ]

    def resolve_subagent_item_id_for_namespace(
        namespace: tuple[Any, ...],
        *,
        allow_pending: bool,
    ) -> str | None:
        normalized_namespace = _normalize_subagent_namespace(namespace)
        if normalized_namespace in namespace_to_subagent_id:
            return namespace_to_subagent_id[normalized_namespace]

        if normalized_namespace:
            matched_ids = {
                item_id
                for existing_namespace, item_id in namespace_to_subagent_id.items()
                if existing_namespace
                and (
                    existing_namespace[: len(normalized_namespace)] == normalized_namespace
                    or normalized_namespace[: len(existing_namespace)] == existing_namespace
                )
            }
            if len(matched_ids) == 1:
                return next(iter(matched_ids))

        active_item_ids = get_active_subagent_item_ids()
        if len(active_item_ids) == 1:
            return active_item_ids[0]

        if allow_pending and len(pending_subagent_tool_ids) == 1:
            return f"subagent:{pending_subagent_tool_ids[0]}"

        return None

    def log_subagent_debug(
        *,
        namespace: tuple[Any, ...],
        stream_mode: str,
        stage: str,
        data: Any,
        resolved_item_id: str | None = None,
    ) -> None:
        if not _subagent_debug_enabled():
            return

        logger.warning(
            "Subagent debug [%s]: namespace=%s normalized=%s stream_mode=%s resolved_item_id=%s data_summary=%s",
            stage,
            _flatten_namespace_parts(namespace),
            _normalize_subagent_namespace(namespace),
            stream_mode,
            resolved_item_id,
            _subagent_debug_summary(data),
        )

    def build_subagent_message_events(
        process_event: ClawProcessEvent,
        *,
        created: bool,
        message: AIMessage | ToolMessage,
    ) -> tuple[ClawProcessEvent, bool, list[str]]:
        events: list[str] = []
        start_emitted = False

        def maybe_append_started(event_data: dict[str, Any]) -> None:
            nonlocal created, start_emitted
            if not created or start_emitted:
                return

            events.append(
                _sse_event(
                    "subagent_started",
                    item_id=process_event.id,
                    title=process_event.title,
                    tool_id=event_data.get("tool_id"),
                    status=process_event.status,
                )
            )
            start_emitted = True
            created = False

        if isinstance(message, AIMessage):
            content_blocks = _iter_content_blocks(message)
            tool_call_chunk_blocks = _tool_call_chunk_blocks_from_message(
                message,
                content_blocks,
            )
            tool_call_blocks = _tool_call_blocks_from_message(
                message,
                [*content_blocks, *tool_call_chunk_blocks],
            )
            additional_tool_call_blocks = _tool_call_blocks_from_additional_kwargs(
                message,
                [*content_blocks, *tool_call_chunk_blocks, *tool_call_blocks],
            )

            for block in content_blocks:
                if block.get("type") != "text":
                    continue
                text = block.get("text", "")
                if not text:
                    continue

                event_data = dict(process_event.data or {})
                transcript = f"{event_data.get('transcript', '')}{text}"
                event_data["transcript"] = transcript
                process_event = upsert_process_event(
                    process_event.id,
                    kind="subagent",
                    title=process_event.title,
                    status=_preserve_terminal_status(process_event.status, "running"),
                    data=event_data,
                )
                persist_stream_snapshot()
                maybe_append_started(event_data)
                events.append(
                    _sse_event(
                        "subagent_updated",
                        item_id=process_event.id,
                        tool_id=event_data.get("tool_id"),
                        status=process_event.status,
                        delta=text,
                        transcript=transcript,
                        child_tools=event_data.get("child_tools"),
                    )
                )

            for block in [
                *content_blocks,
                *tool_call_chunk_blocks,
                *tool_call_blocks,
                *additional_tool_call_blocks,
            ]:
                if block.get("type") not in {"tool_call", "tool_call_chunk"}:
                    continue

                tool_id = str(
                    block.get("id")
                    if block.get("id") is not None
                    else f"buffer:{len(subagent_tool_call_buffers)}"
                )
                buffer_key = f"{process_event.id}:{tool_id}"
                buffer = subagent_tool_call_buffers.setdefault(
                    buffer_key,
                    {
                        "id": tool_id,
                        "name": block.get("name"),
                        "args": None,
                        "started": False,
                    },
                )

                raw_args = block.get("args")
                if block.get("name"):
                    buffer["name"] = block.get("name")

                if isinstance(raw_args, str):
                    buffer["args"] = _merge_tool_call_arg_text(buffer.get("args", ""), raw_args)
                elif raw_args is not None:
                    buffer["args"] = _merge_tool_call_args(buffer.get("args"), raw_args)

                tool_name = str(buffer.get("name") or "").strip()
                parsed_args = _normalize_partial_tool_call_args(buffer.get("args"), tool_name)
                if parsed_args is None and isinstance(raw_args, dict):
                    parsed_args = raw_args
                if not tool_name or parsed_args is None:
                    continue

                buffer["args"] = parsed_args
                buffer["started"] = True

                event_data = dict(process_event.data or {})
                event_data["child_tools"] = _upsert_child_tool_record(
                    event_data.get("child_tools", []),
                    tool_id=tool_id,
                    tool_name=tool_name,
                    status="running",
                    tool_input=parsed_args,
                )
                process_event = upsert_process_event(
                    process_event.id,
                    kind="subagent",
                    title=process_event.title,
                    status=_preserve_terminal_status(process_event.status, "running"),
                    data=event_data,
                )
                persist_stream_snapshot()
                maybe_append_started(event_data)
                events.append(
                    _sse_event(
                        "subagent_updated",
                        item_id=process_event.id,
                        tool_id=event_data.get("tool_id"),
                        status=process_event.status,
                        child_tools=event_data.get("child_tools"),
                    )
                )

            return process_event, created, events

        current_data = dict(process_event.data or {})
        existing_child_tools = _normalize_child_tool_records(current_data.get("child_tools"))
        child_tool_id = resolve_subagent_child_tool_id(process_event, message)
        child_index = _find_child_tool_index(
            existing_child_tools,
            tool_id=child_tool_id,
            tool_name=getattr(message, "name", None),
        )
        existing_child_tool = existing_child_tools[child_index] if child_index is not None else {}
        tool_name = str(
            getattr(message, "name", None)
            or existing_child_tool.get("tool_name")
            or "tool"
        )
        tool_input = _merge_tool_input_from_message(
            tool_name,
            existing_child_tool.get("tool_input"),
            message,
        )
        tool_output = _extract_tool_output(message)
        tool_status = "success" if getattr(message, "status", "success") == "success" else "failed"
        normalized_tool_name = _normalize_tool_name(tool_name)
        if normalized_tool_name in SHELL_TOOL_NAMES:
            shell_payload = _extract_shell_payload(message, tool_input)
            exit_code = shell_payload.get("exit_code")
            if isinstance(exit_code, int) and exit_code != 0:
                tool_status = "failed"

        current_data["child_tools"] = _upsert_child_tool_record(
            existing_child_tools,
            tool_id=child_tool_id,
            tool_name=tool_name,
            status=tool_status,
            tool_input=tool_input,
            tool_output=tool_output,
            error=None if tool_status == "success" else tool_output,
        )
        process_event = upsert_process_event(
            process_event.id,
            kind="subagent",
            title=process_event.title,
            status=process_event.status,
            data=current_data,
        )
        persist_stream_snapshot()
        maybe_append_started(current_data)
        events.append(
            _sse_event(
                "subagent_updated",
                item_id=process_event.id,
                tool_id=current_data.get("tool_id"),
                status=process_event.status,
                child_tools=current_data.get("child_tools"),
            )
        )
        return process_event, created, events

    try:
        cached_reply = _find_recent_duplicate_reply(
            conv_id,
            user_message,
            selected_skill_name,
            selected_skill_metadata.get("selected_skill_revision"),
            db,
        )
        if cached_reply is not None:
            _img_count_cached = _count_images(user_message)
            user_record = ClawMessage(
                conversation_id=str(conv_id),
                role=MessageRole.USER,
                content=_extract_text_content(user_message),
                extra_data={
                    **selected_skill_metadata,
                    **({"has_images": True, "image_count": _img_count_cached} if _img_count_cached > 0 else {}),
                },
            )
            assistant_message = ClawMessage(
                conversation_id=str(conv_id),
                role=MessageRole.ASSISTANT,
                content=cached_reply.content,
                extra_data={
                    "cache_hit": True,
                    "cached_from_message_id": cached_reply.id,
                    "cache_window_seconds": int(REPEAT_QUERY_CACHE_WINDOW.total_seconds()),
                },
            )
            db.add(user_record)
            db.add(assistant_message)
            touch_conversation()
            db.commit()
            db.refresh(assistant_message)

            yield _sse_event(
                "text",
                message_id=assistant_message.id,
                content=cached_reply.content,
            )
            yield _sse_event("done")
            return

        _img_count = _count_images(user_message)
        user_record = ClawMessage(
            conversation_id=str(conv_id),
            role=MessageRole.USER,
            content=_extract_text_content(user_message),
            extra_data={
                **selected_skill_metadata,
                **({"has_images": True, "image_count": _img_count} if _img_count > 0 else {}),
            },
        )
        assistant_message = ClawMessage(
            conversation_id=str(conv_id),
            role=MessageRole.ASSISTANT,
            content="",
            extra_data={},
        )
        db.add(user_record)
        db.add(assistant_message)
        touch_conversation()
        db.commit()
        db.refresh(assistant_message)

        prompt_bundle = _ensure_conversation_prompt_snapshot(conversation, db)

        def capture_prompt_debug_request(captured_request: dict[str, Any]) -> None:
            nonlocal prompt_debug_snapshot
            prompt_debug_snapshot = build_prompt_debug_snapshot(
                conversation_id=str(conv_id),
                llm_model=conversation.llm_model,
                working_directory=conversation.working_directory,
                prompt_bundle=prompt_bundle,
                selected_skill=selected_skill,
                turn_instruction=selected_skill_turn_instruction,
                captured_request=captured_request,
            )

        agent = await create_claw_agent(
            working_directory=conversation.working_directory,
            llm_model=conversation.llm_model,
            conversation_id=str(conv_id),
            custom_system_prompt=(
                get_system_prompt_from_bundle(prompt_bundle)
                or conversation.system_prompt
            ),
            prompt_overrides=build_deep_agent_prompt_overrides(prompt_bundle),
            turn_instruction=selected_skill_turn_instruction,
            debug_capture_callback=(
                capture_prompt_debug_request if should_capture_prompt_debug else None
            ),
        )

        input_data = {"messages": [{"role": "user", "content": user_message}]}

        async for chunk in agent.astream(
            input_data,
            stream_mode=["messages", "updates"],
            subgraphs=True,
            config={"configurable": {"thread_id": str(conv_id)}},
        ):
            if prompt_debug_snapshot is not None and not prompt_debug_persisted:
                persist_prompt_debug_snapshot()
            if (
                prompt_debug_snapshot is not None
                and user_record is not None
                and not prompt_debug_emitted
            ):
                prompt_debug_emitted = True
                yield _sse_event(
                    "prompt_debug",
                    user_message_id=user_record.id,
                    prompt_debug=prompt_debug_snapshot,
                )

            if not isinstance(chunk, tuple) or len(chunk) != 3:
                continue

            namespace, stream_mode, data = chunk
            namespace_key = tuple(namespace) if namespace else ()
            if namespace_key:
                log_subagent_debug(
                    namespace=namespace_key,
                    stream_mode=stream_mode,
                    stage="chunk",
                    data=data,
                    resolved_item_id=resolve_subagent_item_id_for_namespace(
                        namespace_key,
                        allow_pending=True,
                    ),
                )

            if stream_mode == "updates":
                if namespace_key and should_track_subagent_namespace(namespace_key):
                    process_event, created = ensure_subagent_binding(namespace_key)
                    embedded_messages = _collect_embedded_stream_messages(data)
                    if embedded_messages:
                        log_subagent_debug(
                            namespace=namespace_key,
                            stream_mode=stream_mode,
                            stage="embedded_messages",
                            data={
                                "count": len(embedded_messages),
                                "message_types": [
                                    type(embedded_message).__name__
                                    for embedded_message in embedded_messages
                                ],
                            },
                            resolved_item_id=process_event.id,
                        )
                        for embedded_message in embedded_messages:
                            process_event, created, subagent_events = build_subagent_message_events(
                                process_event,
                                created=created,
                                message=embedded_message,
                            )
                            for subagent_event in subagent_events:
                                yield subagent_event
                    current_data = dict(process_event.data or {})
                    current_data["state"] = _jsonable(data)
                    todos = _find_todos(data)
                    if todos is not None:
                        child_tool_status = (
                            "success"
                            if _derive_planning_status(todos) == "completed"
                            else "running"
                        )
                        current_data["child_tools"] = _upsert_child_tool_record(
                            current_data.get("child_tools", []),
                            tool_id=f"{process_event.id}:write_todos",
                            tool_name="write_todos",
                            status=child_tool_status,
                            tool_input={"todos": todos},
                            tool_output=todos,
                        )
                        current_data["subagent_todos"] = _jsonable(todos)
                    process_event = upsert_process_event(
                        process_event.id,
                        kind="subagent",
                        title=process_event.title,
                        status=process_event.status,
                        data=current_data,
                    )
                    persist_stream_snapshot()
                    if created:
                        yield _sse_event(
                            "subagent_started",
                            item_id=process_event.id,
                            title=process_event.title,
                            tool_id=current_data.get("tool_id"),
                            status=process_event.status,
                        )
                    yield _sse_event(
                        "subagent_updated",
                        item_id=process_event.id,
                        tool_id=current_data.get("tool_id"),
                        status=process_event.status,
                        state=current_data.get("state"),
                        child_tools=current_data.get("child_tools"),
                    )
                    continue

                todos = _find_todos(data)
                if todos is not None:
                    item_id = planning_item_id or f"planning:{uuid.uuid4().hex}"
                    current_event = process_events.get(item_id)
                    current_data = dict(current_event.data or {}) if current_event else {}
                    merged_todos = _merge_todos(current_data.get("todos"), todos)
                    planning_status = _derive_planning_status(merged_todos)
                    if (
                        current_event is not None
                        and _is_terminal_process_status(current_event.status)
                        and not _is_terminal_process_status(planning_status)
                    ):
                        continue
                    process_event = upsert_process_event(
                        item_id,
                        kind="planning",
                        title="Planning",
                        status=planning_status,
                        data={
                            **current_data,
                            "todos": merged_todos,
                        },
                    )
                    if planning_item_id is None:
                        planning_item_id = item_id
                        append_timeline_item(
                            "planning",
                            item_id=process_event.id,
                            tool_id=current_data.get("tool_id"),
                        )
                        persist_stream_snapshot()
                        yield _sse_event(
                            "planning_started",
                            item_id=process_event.id,
                            title=process_event.title,
                            status=process_event.status,
                            todos=merged_todos,
                        )
                    else:
                        persist_stream_snapshot()
                    yield _sse_event(
                        "planning_updated",
                        item_id=process_event.id,
                        status=process_event.status,
                        todos=merged_todos,
                    )
                    continue

                if namespace_key:
                    bound_item_id = namespace_to_subagent_id.get(
                        _normalize_subagent_namespace(namespace_key)
                    )
                    process_event = process_events.get(bound_item_id) if bound_item_id else None
                    if process_event is not None:
                        current_data = dict(process_event.data or {})
                        current_data["state"] = _jsonable(data)
                        process_event = upsert_process_event(
                            process_event.id,
                            kind="subagent",
                            title=process_event.title,
                            status=process_event.status,
                            data=current_data,
                        )
                        persist_stream_snapshot()
                        yield _sse_event(
                            "subagent_updated",
                            item_id=process_event.id,
                            tool_id=current_data.get("tool_id"),
                            status=process_event.status,
                            state=current_data.get("state"),
                        )
                continue

            if stream_mode != "messages":
                continue

            if not isinstance(data, tuple) or len(data) != 2:
                continue

            message, _metadata = data

            if namespace_key:
                if not should_track_subagent_namespace(namespace_key):
                    log_subagent_debug(
                        namespace=namespace_key,
                        stream_mode=stream_mode,
                        stage="skipped_untracked_namespace",
                        data=data,
                    )
                    continue

                process_event, created = ensure_subagent_binding(namespace_key)
                if not isinstance(message, (AIMessage, ToolMessage)):
                    log_subagent_debug(
                        namespace=namespace_key,
                        stream_mode=stream_mode,
                        stage="skipped_unsupported_message",
                        data={"message_type": type(message).__name__},
                        resolved_item_id=process_event.id,
                    )
                    continue
                process_event, _created, subagent_events = build_subagent_message_events(
                    process_event,
                    created=created,
                    message=message,
                )
                for subagent_event in subagent_events:
                    yield subagent_event
                continue

            if isinstance(message, AIMessage):
                content_blocks = _iter_content_blocks(message)
                tool_call_chunk_blocks = _tool_call_chunk_blocks_from_message(
                    message,
                    content_blocks,
                )
                tool_call_blocks = _tool_call_blocks_from_message(
                    message,
                    [*content_blocks, *tool_call_chunk_blocks],
                )
                additional_tool_call_blocks = _tool_call_blocks_from_additional_kwargs(
                    message,
                    [*content_blocks, *tool_call_chunk_blocks, *tool_call_blocks],
                )
                for block in [
                    *content_blocks,
                    *tool_call_chunk_blocks,
                    *tool_call_blocks,
                    *additional_tool_call_blocks,
                ]:
                    block_type = block.get("type")

                    if block_type == "text":
                        text = block.get("text", "")
                        if not text:
                            continue
                        assistant_fragments.append(text)
                        append_timeline_text(text)
                        persist_stream_snapshot()
                        yield _sse_event(
                            "text",
                            message_id=assistant_message.id,
                            content=text,
                        )
                        continue

                    if block_type not in {"tool_call_chunk", "tool_call"}:
                        continue

                    buffer_key = (
                        block.get("index")
                        if block.get("index") is not None
                        else block.get("id") or f"buffer:{len(tool_call_buffers)}"
                    )
                    buffer = tool_call_buffers.setdefault(
                        buffer_key,
                        {"id": None, "name": None, "args": None, "raw_args": "", "started": False},
                    )

                    if block.get("id"):
                        buffer["id"] = block["id"]
                    if block.get("name"):
                        buffer["name"] = block["name"]

                    chunk_args = block.get("args")
                    tool_id = str(buffer.get("id") or buffer_key)

                    logger.debug(f"Processing tool_call chunk: tool_name={buffer.get('name')}, chunk_args type={type(chunk_args)}, chunk_args={repr(chunk_args) if isinstance(chunk_args, str) else chunk_args}")

                    if isinstance(chunk_args, str):
                        if chunk_args:
                            parsed_chunk_args = _parse_tool_call_args_dict(chunk_args)
                            if parsed_chunk_args is not None:
                                buffer["args"] = _merge_tool_call_args(
                                    buffer.get("args"),
                                    parsed_chunk_args,
                                )
                                buffer["raw_args"] = ""
                            else:
                                raw_args = _merge_tool_call_arg_text(
                                    str(buffer.get("raw_args") or ""),
                                    chunk_args,
                                )
                                buffer["raw_args"] = raw_args
                                partial_args = _normalize_partial_tool_call_args(
                                    raw_args,
                                    buffer.get("name") or "",
                                )
                                if partial_args is not None:
                                    buffer["args"] = _merge_tool_call_args(
                                        buffer.get("args"),
                                        partial_args,
                                    )
                            logger.debug(
                                "Accumulated string args: %r",
                                repr(buffer.get("raw_args") or buffer.get("args"))[:200],
                            )
                            yield _sse_event(
                                "tool_call_delta",
                                tool_id=tool_id,
                                tool_name=buffer.get("name"),
                                delta=chunk_args,
                            )
                    elif chunk_args is not None:
                        logger.debug(f"Merging dict args: existing={buffer.get('args')}, new={chunk_args}")
                        buffer["args"] = _merge_tool_call_args(buffer.get("args"), chunk_args)

                    tool_name = buffer.get("name")
                    normalized_tool_name = _normalize_tool_name(tool_name)
                    parsed_args = _normalize_tool_call_args(buffer.get("args"), tool_name)
                    raw_args = buffer.get("raw_args")
                    if isinstance(raw_args, str) and raw_args.strip():
                        raw_parsed_args = _normalize_partial_tool_call_args(raw_args, tool_name)
                        if raw_parsed_args is not None:
                            parsed_args = (
                                _merge_tool_call_args(parsed_args, raw_parsed_args)
                                if parsed_args is not None
                                else raw_parsed_args
                            )
                    if parsed_args is None and normalized_tool_name in SHELL_TOOL_NAMES:
                        parsed_args = _extract_shell_input_from_raw_args(buffer.get("args"))
                    if parsed_args is None and normalized_tool_name in SHELL_TOOL_NAMES:
                        parsed_args = _extract_shell_input_from_raw_args(raw_args)
                    if not tool_name or parsed_args is None:
                        continue
                    buffer["id"] = tool_id
                    buffer["args"] = parsed_args

                    if buffer.get("started"):
                        tool_record = tool_records.get(tool_id)
                        normalized_args = _jsonable(parsed_args)
                        if tool_record is None or tool_record.tool_input == normalized_args:
                            continue

                        tool_record = ensure_tool_record(tool_id, tool_name, parsed_args)

                        if normalized_tool_name in SHELL_TOOL_NAMES:
                            item_id = f"shell:{tool_record.id}"
                            current_event = process_events.get(item_id)
                            if current_event is not None:
                                command = _derive_shell_command(parsed_args)
                                current_data = dict(current_event.data or {})
                                current_data.update(
                                    {
                                        "tool_id": tool_record.id,
                                        "tool_name": tool_name,
                                        "input": tool_record.tool_input,
                                    }
                                )
                                if command:
                                    current_data["command"] = command

                                current_event = upsert_process_event(
                                    item_id,
                                    kind="shell",
                                    title=command or current_event.title or tool_name,
                                    status=current_event.status,
                                    data=current_data,
                                )
                                persist_stream_snapshot()
                                yield _sse_event(
                                    "shell_started",
                                    item_id=current_event.id,
                                    tool_id=tool_record.id,
                                    tool_name=tool_name,
                                    command=current_data.get("command", ""),
                                    tool_input=tool_record.tool_input,
                                )
                        elif (
                            normalized_tool_name not in PLANNING_TOOL_NAMES
                            and normalized_tool_name not in SUBAGENT_TOOL_NAMES
                        ):
                            persist_stream_snapshot()
                            yield _sse_event(
                                "tool_call_started",
                                tool_id=tool_record.id,
                                tool_name=tool_record.tool_name,
                                tool_input=tool_record.tool_input,
                            )
                        continue

                    buffer["started"] = True

                    tool_record = ensure_tool_record(tool_id, tool_name, parsed_args)

                    if normalized_tool_name in SHELL_TOOL_NAMES:
                        command = _derive_shell_command(parsed_args)
                        process_event = upsert_process_event(
                            f"shell:{tool_record.id}",
                            kind="shell",
                            title=command or tool_name,
                            status="running",
                            data={
                                "tool_id": tool_record.id,
                                "tool_name": tool_name,
                                "input": tool_record.tool_input,
                                "command": command,
                                "stdout": "",
                                "stderr": "",
                            },
                        )
                        append_timeline_item("shell", item_id=process_event.id, tool_id=tool_record.id)
                    elif normalized_tool_name in PLANNING_TOOL_NAMES:
                        todos = _jsonable(parsed_args.get("todos", []))
                        planning_item_id = planning_item_id or f"planning:{tool_record.id}"
                        process_event = upsert_process_event(
                            planning_item_id,
                            kind="planning",
                            title="Planning",
                            status=_derive_planning_status(todos),
                            data={"tool_id": tool_record.id, "todos": todos},
                        )
                        append_timeline_item("planning", item_id=process_event.id, tool_id=tool_record.id)
                    elif normalized_tool_name in SUBAGENT_TOOL_NAMES:
                        item_id = f"subagent:{tool_record.id}"
                        pending_subagent_tool_ids.append(tool_record.id)
                        process_event = upsert_process_event(
                            item_id,
                            kind="subagent",
                            title=_derive_subagent_title(parsed_args),
                            status="running",
                            data={
                                "tool_id": tool_record.id,
                                "tool_name": tool_name,
                                "input": tool_record.tool_input,
                                "transcript": "",
                                "result": None,
                                "child_tools": [],
                            },
                        )
                        append_timeline_item("subagent", item_id=process_event.id, tool_id=tool_record.id)
                    else:
                        append_timeline_item("tool", tool_id=tool_record.id)

                    persist_stream_snapshot()
                    yield _sse_event(
                        "tool_call_started",
                        tool_id=tool_record.id,
                        tool_name=tool_record.tool_name,
                        tool_input=tool_record.tool_input,
                    )

                    if normalized_tool_name in SHELL_TOOL_NAMES:
                        yield _sse_event(
                            "shell_started",
                            item_id=process_event.id,
                            tool_id=tool_record.id,
                            tool_name=tool_name,
                            command=command,
                            tool_input=tool_record.tool_input,
                        )
                    elif normalized_tool_name in PLANNING_TOOL_NAMES:
                        yield _sse_event(
                            "planning_started",
                            item_id=process_event.id,
                            title=process_event.title,
                            status=process_event.status,
                            todos=todos,
                        )
                    elif normalized_tool_name in SUBAGENT_TOOL_NAMES:
                        yield _sse_event(
                            "subagent_started",
                            item_id=process_event.id,
                            tool_id=tool_record.id,
                            title=process_event.title,
                            status=process_event.status,
                        )

                continue

            if not isinstance(message, ToolMessage):
                continue

            tool_id = resolve_tool_id(message)
            tool_name = getattr(message, "name", None) or tool_records.get(tool_id, None)
            tool_name = tool_name.tool_name if isinstance(tool_name, ClawToolCall) else tool_name or "tool"
            normalized_tool_name = _normalize_tool_name(tool_name)
            tool_record = tool_records.get(tool_id) or ensure_tool_record(tool_id, tool_name, {})
            tool_input = _merge_tool_input_from_message(tool_name, tool_record.tool_input, message)
            tool_output = _extract_tool_output(message)
            tool_status = "success" if getattr(message, "status", "success") == "success" else "failed"
            shell_payload = None

            if normalized_tool_name in SHELL_TOOL_NAMES:
                shell_payload = _extract_shell_payload(message, tool_input)
                exit_code = shell_payload.get("exit_code")
                if isinstance(exit_code, int) and exit_code != 0:
                    tool_status = "failed"
                if not _derive_shell_command(tool_input):
                    shell_command = shell_payload.get("command")
                    if isinstance(shell_command, str) and shell_command:
                        tool_input = {**tool_input, "command": shell_command}
                if not _derive_shell_command(tool_input):
                    warning_payload = {
                        "tool_id": tool_id,
                        "tool_name": tool_name,
                        "tool_input": _jsonable(tool_input),
                        "message_additional_kwargs": _jsonable(
                            getattr(message, "additional_kwargs", None)
                        ),
                        "message_artifact": _jsonable(getattr(message, "artifact", None)),
                        "message_content_preview": _stringify(getattr(message, "content", None))[:500],
                    }
                    logger.warning(
                        "Shell tool completed without captured command: %s",
                        json.dumps(warning_payload, ensure_ascii=False),
                    )

            tool_record.tool_name = tool_name
            tool_record.tool_input = tool_input
            tool_record.tool_output = tool_output
            tool_record.status = (
                ToolCallStatus.SUCCESS if tool_status == "success" else ToolCallStatus.FAILED
            )
            tool_record.error = None if tool_status == "success" else _stringify(tool_output)
            db.flush()

            if normalized_tool_name in SHELL_TOOL_NAMES:
                item_id = f"shell:{tool_record.id}"
                current_event = process_events.get(item_id)
                current_data = dict(current_event.data or {}) if current_event else {}
                shell_payload = shell_payload or _extract_shell_payload(message, tool_input)
                current_data.update(shell_payload)
                current_data["tool_id"] = tool_record.id
                current_data["tool_name"] = tool_name
                current_data["input"] = tool_record.tool_input
                current_event = upsert_process_event(
                    item_id,
                    kind="shell",
                    title=current_data.get("command") or tool_name,
                    status=tool_status,
                    data=current_data,
                )
                persist_stream_snapshot()
                yield _sse_event(
                    "tool_call_completed",
                    tool_id=tool_record.id,
                    tool_name=tool_record.tool_name,
                    tool_input=tool_record.tool_input,
                    status=tool_status,
                    output=tool_output,
                    error=tool_record.error,
                )

                stdout = _stringify(current_data.get("stdout"))
                stderr = _stringify(current_data.get("stderr"))
                if stdout:
                    yield _sse_event(
                        "shell_output",
                        item_id=current_event.id,
                        tool_id=tool_record.id,
                        stream="stdout",
                        output=stdout,
                        command=current_data.get("command"),
                    )
                if stderr:
                    yield _sse_event(
                        "shell_output",
                        item_id=current_event.id,
                        tool_id=tool_record.id,
                        stream="stderr",
                        output=stderr,
                        command=current_data.get("command"),
                    )
                yield _sse_event(
                    "shell_completed",
                    item_id=current_event.id,
                    tool_id=tool_record.id,
                    status=tool_status,
                    exit_code=current_data.get("exit_code"),
                    command=current_data.get("command"),
                    tool_input=tool_record.tool_input,
                    output=tool_output,
                    error=tool_record.error,
                )
                continue

            if normalized_tool_name in PLANNING_TOOL_NAMES:
                item_id = planning_item_id or f"planning:{tool_record.id}"
                current_event = process_events.get(item_id)
                current_data = dict(current_event.data or {}) if current_event else {}
                todos = _merge_todos(current_data.get("todos"), _find_todos(tool_output))
                planning_status = (
                    _derive_planning_status(todos)
                    if todos
                    else current_event.status if current_event else "pending"
                )
                if (
                    current_event is not None
                    and _is_terminal_process_status(current_event.status)
                    and not _is_terminal_process_status(planning_status)
                ):
                    todos = current_data.get("todos") if isinstance(current_data.get("todos"), list) else todos
                    planning_status = current_event.status
                current_data["tool_id"] = tool_record.id
                current_data["todos"] = _jsonable(todos)
                current_data["tool_output"] = tool_output
                current_event = upsert_process_event(
                    item_id,
                    kind="planning",
                    title=current_event.title if current_event else "Planning",
                    status=planning_status,
                    data=current_data,
                )
                planning_item_id = item_id
                persist_stream_snapshot()
                yield _sse_event(
                    "tool_call_completed",
                    tool_id=tool_record.id,
                    tool_name=tool_record.tool_name,
                    tool_input=tool_record.tool_input,
                    status=tool_status,
                    output=tool_output,
                    error=tool_record.error,
                )
                yield _sse_event(
                    "planning_updated",
                    item_id=current_event.id,
                    status=current_event.status,
                    todos=current_data["todos"],
                )
                continue

            if normalized_tool_name in SUBAGENT_TOOL_NAMES:
                item_id = f"subagent:{tool_record.id}"
                current_event = process_events.get(item_id)
                current_data = dict(current_event.data or {}) if current_event else {}
                current_data["tool_id"] = tool_record.id
                current_data["tool_output"] = tool_output
                current_data["result"] = _stringify(tool_output)
                current_event = upsert_process_event(
                    item_id,
                    kind="subagent",
                    title=current_event.title if current_event else "Subagent",
                    status=tool_status,
                    data=current_data,
                )
                persist_stream_snapshot()
                yield _sse_event(
                    "tool_call_completed",
                    tool_id=tool_record.id,
                    tool_name=tool_record.tool_name,
                    tool_input=tool_record.tool_input,
                    status=tool_status,
                    output=tool_output,
                    error=tool_record.error,
                )
                yield _sse_event(
                    "subagent_completed",
                    item_id=current_event.id,
                    tool_id=tool_record.id,
                    status=current_event.status,
                    result=current_data["result"],
                    child_tools=current_data.get("child_tools"),
                )
                continue

            persist_stream_snapshot()
            yield _sse_event(
                "tool_call_completed",
                tool_id=tool_record.id,
                tool_name=tool_record.tool_name,
                tool_input=tool_record.tool_input,
                status=tool_status,
                output=tool_output,
                error=tool_record.error,
            )

        if prompt_debug_snapshot is not None and not prompt_debug_persisted:
            persist_prompt_debug_snapshot()
        if (
            prompt_debug_snapshot is not None
            and user_record is not None
            and not prompt_debug_emitted
        ):
            prompt_debug_emitted = True
            yield _sse_event(
                "prompt_debug",
                user_message_id=user_record.id,
                prompt_debug=prompt_debug_snapshot,
            )

        assistant_message.content = "".join(assistant_fragments)
        assistant_message.extra_data = {
            "stream_protocol": "claw.v2",
            "tool_call_count": len(tool_records),
            "process_event_count": len(process_events),
            "timeline": _jsonable(timeline_entries),
        }
        touch_conversation()
        db.commit()

        yield _sse_event("done")
    except Exception as exc:
        logger.error("Chat error", exc_info=True)
        db.rollback()
        error_msg = str(exc).lower()
        vision_keywords = ["vision", "image", "multimodal", "does not support", "unsupported"]
        if any(kw in error_msg for kw in vision_keywords) and _count_images(user_message) > 0:
            friendly_msg = (
                "当前模型不支持图片识别，请在对话设置中切换到支持视觉的模型"
                "（如 claude-3-5-sonnet、gpt-4o）"
            )
            yield _sse_event("error", message=friendly_msg)
        else:
            yield _sse_event("error", message=str(exc))


@router.post("/conversations/{conv_id}/chat")
async def chat_with_agent(
    conv_id: UUID,
    message: MessageCreate,
    db: Session = Depends(get_db),
):
    conversation = db.query(ClawConversation).filter_by(id=str(conv_id)).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message_content = message.content.strip()
    selected_skill_name: str | None = None

    if message.selected_skill:
        try:
            selected_skill_name = resolve_skill_reference(
                message.selected_skill,
                enabled_only=True,
            )["name"]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=exc.args[0]) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        try:
            selected_skill, message_content = extract_slash_skill_command(
                message_content,
                enabled_only=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if selected_skill is not None:
            selected_skill_name = selected_skill["name"]

    if not message_content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")

    return StreamingResponse(
        chat_event_generator(
            conv_id,
            message_content,
            conversation,
            db,
            selected_skill_name=selected_skill_name,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
