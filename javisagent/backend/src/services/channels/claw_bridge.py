from __future__ import annotations

import inspect
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage

from src.models.base import SessionLocal
from src.models.channels import ChannelSession
from src.models.claw import ClawConversation, ClawMessage, MessageRole
from src.services.claw import create_claw_agent
from src.services.claw.skill_registry import extract_slash_skill_command, get_skill_detail

try:
    from src.services.claw import cleanup_claw_agent, resolve_claw_agent
except ImportError:
    async def resolve_claw_agent(agent_or_awaitable: Any) -> Any:
        if inspect.isawaitable(agent_or_awaitable):
            return await agent_or_awaitable
        return agent_or_awaitable

    async def cleanup_claw_agent(agent: Any) -> None:
        cleanup = getattr(agent, "cleanup", None)
        if not callable(cleanup):
            return

        result = cleanup()
        if inspect.isawaitable(result):
            await result

logger = logging.getLogger(__name__)

DEFAULT_EXTERNAL_WORKDIR = str(Path(__file__).resolve().parents[4])
DEFAULT_EXTERNAL_MODEL = "deepseek-chat"


def _iter_text_blocks(message: AIMessage) -> list[str]:
    blocks = getattr(message, "content_blocks", None)
    if not blocks:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return [content]
        if isinstance(content, list):
            blocks = [block for block in content if isinstance(block, dict)]
        else:
            blocks = []

    fragments: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = str(block.get("text") or "")
        if text:
            fragments.append(text)
    return fragments


def _build_selected_skill_turn_instruction(skill: dict[str, Any]) -> str:
    description = str(skill.get("description") or "").strip()
    skill_content = str(skill.get("content") or "").strip()
    skill_path = str(skill.get("skill_file_path") or skill.get("path") or "").strip()
    aliases = [
        str(alias).strip()
        for alias in skill.get("aliases", [])
        if str(alias).strip()
    ]

    lines = [
        "# User-requested Skill For This Turn",
        f"The user explicitly requested the enabled skill `{skill['name']}` for this turn.",
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
            "This instruction applies only to the current user turn.",
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
    return "\n".join(lines)


def _build_selected_skill_metadata(skill: dict[str, Any] | None) -> dict[str, Any]:
    if skill is None:
        return {}

    aliases = [
        str(alias).strip()
        for alias in skill.get("aliases", [])
        if str(alias).strip()
    ]
    return {
        "selected_skill": skill["name"],
        "selected_skill_alias": aliases[0] if aliases else skill["name"],
        "selected_skill_file_path": str(
            skill.get("skill_file_path") or skill.get("path") or ""
        ).strip(),
    }


def _get_or_create_channel_conversation(
    db,
    *,
    channel_name: str,
    chat_id: str,
    sender_id: str,
) -> ClawConversation:
    session = db.query(ChannelSession).filter_by(
        channel_name=channel_name,
        chat_id=chat_id,
    ).first()

    if session is not None:
        conversation = db.query(ClawConversation).filter_by(id=session.conversation_id).first()
        if conversation is not None:
            if session.sender_id != sender_id:
                session.sender_id = sender_id
                session.updated_at = datetime.utcnow()
                db.add(session)
                db.commit()
            return conversation

    conversation = ClawConversation(
        title=f"{channel_name.upper()} - {sender_id}",
        working_directory=DEFAULT_EXTERNAL_WORKDIR,
        llm_model=DEFAULT_EXTERNAL_MODEL,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    if session is None:
        session = ChannelSession(
            channel_name=channel_name,
            chat_id=chat_id,
            sender_id=sender_id,
            conversation_id=conversation.id,
            extra_data={},
        )
    else:
        session.sender_id = sender_id
        session.conversation_id = conversation.id
        session.updated_at = datetime.utcnow()

    db.add(session)
    db.commit()
    return conversation


async def process_inbound_message(message: Any) -> str:
    db = SessionLocal()
    agent: Any | None = None

    try:
        raw_content = str(getattr(message, "content", "") or "").strip()
        if not raw_content:
            return ""

        selected_skill, message_content = extract_slash_skill_command(
            raw_content,
            enabled_only=True,
        )
        if not message_content:
            return "消息内容为空，请重新发送。"

        selected_skill_detail = (
            get_skill_detail(selected_skill["name"])
            if selected_skill is not None
            else None
        )
        selected_skill_metadata = _build_selected_skill_metadata(selected_skill_detail)

        conversation = _get_or_create_channel_conversation(
            db,
            channel_name=str(getattr(message, "channel", "qq") or "qq"),
            chat_id=str(getattr(message, "chat_id", "") or ""),
            sender_id=str(getattr(message, "sender_id", "") or ""),
        )

        user_record = ClawMessage(
            conversation_id=str(conversation.id),
            role=MessageRole.USER,
            content=message_content,
            extra_data={
                "external_channel": str(getattr(message, "channel", "qq") or "qq"),
                "external_chat_id": str(getattr(message, "chat_id", "") or ""),
                "external_sender_id": str(getattr(message, "sender_id", "") or ""),
                "external_message_id": str(
                    (getattr(message, "metadata", {}) or {}).get("message_id", "")
                ).strip(),
                **selected_skill_metadata,
            },
        )
        db.add(user_record)
        conversation.updated_at = datetime.utcnow()
        db.commit()

        agent = await resolve_claw_agent(
            create_claw_agent(
                working_directory=conversation.working_directory,
                llm_model=conversation.llm_model,
                conversation_id=str(conversation.id),
                custom_system_prompt=conversation.system_prompt,
                turn_instruction=(
                    _build_selected_skill_turn_instruction(selected_skill_detail)
                    if selected_skill_detail is not None
                    else None
                ),
            )
        )

        assistant_fragments: list[str] = []
        async for chunk in agent.astream(
            {"messages": [{"role": "user", "content": message_content}]},
            stream_mode=["messages"],
            subgraphs=True,
            config={"configurable": {"thread_id": str(conversation.id)}},
        ):
            if not isinstance(chunk, tuple) or len(chunk) != 3:
                continue

            namespace, stream_mode, data = chunk
            if namespace or stream_mode != "messages":
                continue
            if not isinstance(data, tuple) or len(data) != 2:
                continue

            emitted_message, _metadata = data
            if not isinstance(emitted_message, AIMessage):
                continue

            assistant_fragments.extend(_iter_text_blocks(emitted_message))

        assistant_text = "".join(assistant_fragments).strip()
        if not assistant_text:
            assistant_text = "已收到消息，但当前没有生成可返回的内容，请稍后再试。"

        assistant_record = ClawMessage(
            conversation_id=str(conversation.id),
            role=MessageRole.ASSISTANT,
            content=assistant_text,
            extra_data={
                "external_channel": str(getattr(message, "channel", "qq") or "qq"),
                "external_chat_id": str(getattr(message, "chat_id", "") or ""),
            },
        )
        db.add(assistant_record)
        conversation.updated_at = datetime.utcnow()
        db.commit()
        return assistant_text
    except Exception:
        logger.exception("Failed to process inbound channel message")
        try:
            fallback_conversation = _get_or_create_channel_conversation(
                db,
                channel_name=str(getattr(message, "channel", "qq") or "qq"),
                chat_id=str(getattr(message, "chat_id", "") or ""),
                sender_id=str(getattr(message, "sender_id", "") or ""),
            )
            db.add(
                ClawMessage(
                    conversation_id=str(fallback_conversation.id),
                    role=MessageRole.ASSISTANT,
                    content="渠道消息已收到，但当前处理失败，请稍后再试。",
                    extra_data={
                        "external_channel": str(getattr(message, "channel", "qq") or "qq"),
                        "external_chat_id": str(getattr(message, "chat_id", "") or ""),
                        "error": "channel_processing_failed",
                    },
                )
            )
            fallback_conversation.updated_at = datetime.utcnow()
            db.commit()
        except Exception:
            db.rollback()
        return "渠道消息已收到，但当前处理失败，请稍后再试。"
    finally:
        await cleanup_claw_agent(agent)
        db.close()
