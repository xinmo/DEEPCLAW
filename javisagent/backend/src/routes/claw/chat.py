import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import AsyncGenerator

from src.models import get_db
from src.models.claw import ClawConversation, ClawMessage, MessageRole
from src.schemas.claw import MessageCreate, MessageResponse
from src.services.claw import create_claw_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/claw", tags=["claw-chat"])


@router.get("/conversations/{conv_id}/messages")
async def get_messages(
    conv_id: UUID,
    db: Session = Depends(get_db)
):
    """获取对话消息历史"""
    conversation = db.query(ClawConversation).filter_by(id=str(conv_id)).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = db.query(ClawMessage).filter_by(
        conversation_id=str(conv_id)
    ).order_by(ClawMessage.created_at).all()

    # 转换消息格式
    result = []
    for msg in messages:
        # 获取关联的工具调用
        tool_calls_info = []
        for tc in msg.tool_calls:
            tool_calls_info.append({
                "id": tc.id,
                "tool_name": tc.tool_name,
                "tool_input": tc.tool_input,
                "tool_output": tc.tool_output,
                "status": tc.status.value,
                "duration": tc.duration,
                "error": tc.error
            })

        result.append({
            "id": msg.id,
            "role": msg.role.value,
            "content": msg.content,
            "metadata": msg.extra_data or {},
            "tool_calls": tool_calls_info,
            "created_at": msg.created_at
        })

    return result


async def chat_event_generator(
    conv_id: UUID,
    user_message: str,
    conversation: ClawConversation,
    db: Session
) -> AsyncGenerator[str, None]:
    """
    SSE 事件生成器

    生成的事件类型：
    - text: 文本内容
    - tool_call: 工具调用开始
    - tool_result: 工具调用结果
    - subagent_start: 子智能体启动
    - subagent_progress: 子智能体进度
    - subagent_complete: 子智能体完成
    - planning: 规划任务
    - done: 响应完成
    - error: 错误
    """
    try:
        # 保存用户消息
        user_msg = ClawMessage(
            conversation_id=str(conv_id),
            role=MessageRole.USER,
            content=user_message
        )
        db.add(user_msg)
        db.commit()

        # 创建 Agent
        agent = create_claw_agent(
            working_directory=conversation.working_directory,
            llm_model=conversation.llm_model,
            conversation_id=str(conv_id)
        )

        # 流式执行 Agent
        assistant_content = ""
        tool_calls_data = []

        # TODO: 实现 Agent 流式执行逻辑
        # 这里先返回一个简单的响应
        yield f"data: {json.dumps({'type': 'text', 'content': '收到消息，Agent 集成进行中...'})}\n\n"

        # 保存 Assistant 消息
        assistant_msg = ClawMessage(
            conversation_id=str(conv_id),
            role=MessageRole.ASSISTANT,
            content=assistant_content or "Agent 响应",
            extra_data={"tool_calls": tool_calls_data}
        )
        db.add(assistant_msg)
        db.commit()

        # 发送完成信号
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("/conversations/{conv_id}/chat")
async def chat_with_agent(
    conv_id: UUID,
    message: MessageCreate,
    db: Session = Depends(get_db)
):
    """与 Deep Agent 对话（SSE 流式）"""
    # 获取对话
    conversation = db.query(ClawConversation).filter_by(id=str(conv_id)).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 返回 SSE 流
    return StreamingResponse(
        chat_event_generator(conv_id, message.content, conversation, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )
