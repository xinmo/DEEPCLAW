# Claw - 对话龙虾功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Claw（对话龙虾）功能，为用户提供与 Deep Agents 进行对话的编程助手界面。

**Architecture:** FastAPI 后端直接集成 Deep Agents SDK，使用 SSE 流式响应。前端复用 KnowledgeChatPage 的布局结构，采用 CLI 风格的统一聊天流界面，实时展示工具调用、子智能体和规划任务。

**Tech Stack:** React 18 + TypeScript, Ant Design 5.x, FastAPI, Deep Agents SDK, SQLAlchemy, SSE

---

## 任务概览

1. **后端基础架构** - 数据库模型、基础 API 端点
2. **Deep Agents 集成** - Agent 创建、工具配置
3. **SSE 流式响应** - 聊天端点、事件处理
4. **前端页面结构** - 路由、菜单、主页面组件
5. **对话管理功能** - 对话列表、创建、删除、切换
6. **聊天界面** - 消息展示、输入框、SSE 连接
7. **工具调用展示** - 工具卡片组件
8. **子智能体展示** - 子智能体卡片、并行池
9. **规划任务展示** - 规划卡片组件
10. **文件树组件** - 工作目录文件浏览
11. **错误处理与优化** - 错误提示、性能优化
12. **集成测试** - 端到端测试

---

## Task 1: 后端数据库模型

**Files:**
- Create: `javisagent/backend/src/models/claw.py`
- Modify: `javisagent/backend/src/models/__init__.py`

**Step 1: 创建 Claw 数据模型**

创建 `javisagent/backend/src/models/claw.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models import Base
import enum


class ClawConversation(Base):
    """Claw 对话会话"""
    __tablename__ = "claw_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, default="新对话")
    working_directory = Column(String(512), nullable=False)
    llm_model = Column(String(100), nullable=False, default="claude-opus-4-6")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    messages = relationship("ClawMessage", back_populates="conversation", cascade="all, delete-orphan")


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ClawMessage(Base):
    """Claw 消息记录"""
    __tablename__ = "claw_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("claw_conversations.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default={})  # 存储工具调用、子智能体等信息
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    conversation = relationship("ClawConversation", back_populates="messages")
    tool_calls = relationship("ClawToolCall", back_populates="message", cascade="all, delete-orphan")


class ToolCallStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ClawToolCall(Base):
    """工具调用记录"""
    __tablename__ = "claw_tool_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("claw_messages.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    tool_input = Column(JSON, nullable=False)
    tool_output = Column(JSON)
    status = Column(Enum(ToolCallStatus), nullable=False, default=ToolCallStatus.RUNNING)
    duration = Column(Float)  # 执行时长（秒）
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    message = relationship("ClawMessage", back_populates="tool_calls")
```

**Step 2: 更新 models __init__.py**

修改 `javisagent/backend/src/models/__init__.py`，添加导入：

```python
from .claw import ClawConversation, ClawMessage, ClawToolCall, MessageRole, ToolCallStatus
```

**Step 3: 创建数据库迁移**

运行：
```bash
cd javisagent/backend
python -c "from src.models import Base, engine; Base.metadata.create_all(bind=engine)"
```

预期：数据库中创建 `claw_conversations`, `claw_messages`, `claw_tool_calls` 表

**Step 4: 提交**

```bash
git add javisagent/backend/src/models/claw.py javisagent/backend/src/models/__init__.py
git commit -m "feat(backend): add Claw database models

- Add ClawConversation, ClawMessage, ClawToolCall models
- Support conversation management and tool call tracking

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 后端 Schema 定义

**Files:**
- Create: `javisagent/backend/src/schemas/claw.py`

**Step 1: 创建 Pydantic Schema**

创建 `javisagent/backend/src/schemas/claw.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


# 对话相关 Schema
class ConversationCreate(BaseModel):
    title: Optional[str] = "新对话"
    working_directory: str
    llm_model: str = "claude-opus-4-6"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    working_directory: Optional[str] = None
    llm_model: Optional[str] = None


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    working_directory: str
    llm_model: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 消息相关 Schema
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class ToolCallInfo(BaseModel):
    id: UUID
    tool_name: str
    tool_input: Any
    tool_output: Optional[Any] = None
    status: str
    duration: Optional[float] = None
    error: Optional[str] = None


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    metadata: dict
    tool_calls: List[ToolCallInfo] = []
    created_at: datetime

    class Config:
        from_attributes = True


# 工具验证 Schema
class DirectoryValidation(BaseModel):
    path: str


class DirectoryValidationResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None


# 模型列表 Schema
class ModelInfo(BaseModel):
    model_id: str
    name: str
    provider: str


class ModelsResponse(BaseModel):
    models: List[ModelInfo]
```

**Step 2: 提交**

```bash
git add javisagent/backend/src/schemas/claw.py
git commit -m "feat(backend): add Claw Pydantic schemas

- Add conversation, message, and tool call schemas
- Add validation schemas for directory and models

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Deep Agents 服务集成

**Files:**
- Create: `javisagent/backend/src/services/claw/__init__.py`
- Create: `javisagent/backend/src/services/claw/agent.py`
- Modify: `javisagent/backend/requirements.txt`

**Step 1: 添加 Deep Agents 依赖**

修改 `javisagent/backend/requirements.txt`，添加：

```
deepagents>=0.1.0
langgraph>=0.2.0
```

**Step 2: 创建 Agent 服务**

创建 `javisagent/backend/src/services/claw/agent.py`:

```python
import os
from typing import Optional
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
import logging

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """你是一个专业的编程助手，可以帮助用户完成各种编程任务。

你可以使用以下工具：
- 文件系统工具：读取、写入、编辑、搜索文件
- Shell 命令：执行任何命令行操作
- 规划工具：分解复杂任务为可执行步骤
- 子智能体：创建专门的子任务智能体

工作目录：{working_directory}

请始终：
1. 在执行操作前说明你的计划
2. 使用工具时提供清晰的描述
3. 遇到错误时提供解决方案
4. 完成任务后总结结果

注意：
- 所有文件操作都相对于工作目录进行
- Shell 命令在工作目录中执行
- 请确保操作的安全性
"""


def create_claw_agent(
    working_directory: str,
    llm_model: str = "claude-opus-4-6",
    conversation_id: Optional[str] = None
):
    """
    创建 Claw Deep Agent 实例

    Args:
        working_directory: 工作目录路径
        llm_model: LLM 模型名称
        conversation_id: 对话 ID（用于会话持久化）

    Returns:
        Deep Agent 实例
    """
    try:
        # 验证工作目录
        if not os.path.exists(working_directory):
            raise ValueError(f"工作目录不存在: {working_directory}")

        if not os.path.isdir(working_directory):
            raise ValueError(f"路径不是目录: {working_directory}")

        # 配置系统提示词
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            working_directory=working_directory
        )

        # 创建 Agent
        agent = create_deep_agent(
            model=llm_model,
            system_prompt=system_prompt,
            checkpointer=MemorySaver(),
            # 启用所有工具
            enable_filesystem=True,
            enable_shell=True,
            enable_planning=True,
            enable_subagents=True,
            # 设置工作目录
            working_directory=working_directory,
        )

        logger.info(f"Created Claw agent for directory: {working_directory}")
        return agent

    except Exception as e:
        logger.error(f"Failed to create Claw agent: {e}")
        raise


def validate_working_directory(path: str) -> tuple[bool, Optional[str]]:
    """
    验证工作目录是否有效

    Args:
        path: 目录路径

    Returns:
        (是否有效, 错误原因)
    """
    if not path:
        return False, "路径不能为空"

    if not os.path.exists(path):
        return False, "目录不存在"

    if not os.path.isdir(path):
        return False, "路径不是目录"

    if not os.access(path, os.R_OK):
        return False, "没有读取权限"

    return True, None
```

**Step 3: 创建 __init__.py**

创建 `javisagent/backend/src/services/claw/__init__.py`:

```python
from .agent import create_claw_agent, validate_working_directory

__all__ = ["create_claw_agent", "validate_working_directory"]
```

**Step 4: 安装依赖**

运行：
```bash
cd javisagent/backend
pip install -r requirements.txt
```

预期：成功安装 deepagents 和 langgraph

**Step 5: 提交**

```bash
git add javisagent/backend/src/services/claw/ javisagent/backend/requirements.txt
git commit -m "feat(backend): integrate Deep Agents SDK

- Add create_claw_agent function with full tool support
- Add working directory validation
- Install deepagents and langgraph dependencies

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 基础 API 路由

**Files:**
- Create: `javisagent/backend/src/routes/claw/__init__.py`
- Create: `javisagent/backend/src/routes/claw/conversations.py`
- Modify: `javisagent/backend/src/app.py`

**Step 1: 创建对话管理路由**

创建 `javisagent/backend/src/routes/claw/conversations.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import os

from src.models import get_db
from src.models.claw import ClawConversation
from src.schemas.claw import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    DirectoryValidation,
    DirectoryValidationResponse,
    ModelInfo,
    ModelsResponse
)
from src.services.claw import validate_working_directory

router = APIRouter(prefix="/api/claw", tags=["claw"])


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db)
):
    """创建新对话"""
    # 验证工作目录
    valid, reason = validate_working_directory(data.working_directory)
    if not valid:
        raise HTTPException(status_code=400, detail=f"无效的工作目录: {reason}")

    # 创建对话
    conversation = ClawConversation(
        title=data.title,
        working_directory=data.working_directory,
        llm_model=data.llm_model
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(db: Session = Depends(get_db)):
    """获取对话列表"""
    conversations = db.query(ClawConversation).order_by(
        ClawConversation.updated_at.desc()
    ).all()
    return conversations


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(
    conv_id: UUID,
    db: Session = Depends(get_db)
):
    """获取对话详情"""
    conversation = db.query(ClawConversation).filter_by(id=conv_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conversation


@router.put("/conversations/{conv_id}", response_model=ConversationResponse)
async def update_conversation(
    conv_id: UUID,
    data: ConversationUpdate,
    db: Session = Depends(get_db)
):
    """更新对话"""
    conversation = db.query(ClawConversation).filter_by(id=conv_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 如果更新工作目录，需要验证
    if data.working_directory:
        valid, reason = validate_working_directory(data.working_directory)
        if not valid:
            raise HTTPException(status_code=400, detail=f"无效的工作目录: {reason}")
        conversation.working_directory = data.working_directory

    if data.title is not None:
        conversation.title = data.title

    if data.llm_model:
        conversation.llm_model = data.llm_model

    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: UUID,
    db: Session = Depends(get_db)
):
    """删除对话"""
    conversation = db.query(ClawConversation).filter_by(id=conv_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    db.delete(conversation)
    db.commit()
    return {"message": "删除成功"}


@router.post("/validate-directory", response_model=DirectoryValidationResponse)
async def validate_directory(data: DirectoryValidation):
    """验证工作目录"""
    valid, reason = validate_working_directory(data.path)
    return DirectoryValidationResponse(valid=valid, reason=reason)


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """获取可用模型列表"""
    models = [
        ModelInfo(model_id="claude-opus-4-6", name="Claude Opus 4.6", provider="Anthropic"),
        ModelInfo(model_id="claude-sonnet-4-6", name="Claude Sonnet 4.6", provider="Anthropic"),
        ModelInfo(model_id="gpt-4o", name="GPT-4o", provider="OpenAI"),
        ModelInfo(model_id="gpt-4o-mini", name="GPT-4o Mini", provider="OpenAI"),
    ]
    return ModelsResponse(models=models)
```

**Step 2: 创建 __init__.py**

创建 `javisagent/backend/src/routes/claw/__init__.py`:

```python
from .conversations import router as conversations_router

__all__ = ["conversations_router"]
```

**Step 3: 注册路由到 app**

修改 `javisagent/backend/src/app.py`，添加导入和注册：

```python
from src.routes.claw import conversations_router

# 在现有路由注册后添加
app.include_router(conversations_router)
```

**Step 4: 测试 API**

运行后端服务：
```bash
cd javisagent/backend
python src/main.py
```

测试创建对话：
```bash
curl -X POST http://localhost:8000/api/claw/conversations \
  -H "Content-Type: application/json" \
  -d '{"working_directory": "/tmp", "title": "测试对话"}'
```

预期：返回创建的对话 JSON

**Step 5: 提交**

```bash
git add javisagent/backend/src/routes/claw/ javisagent/backend/src/app.py
git commit -m "feat(backend): add Claw conversation management API

- Add CRUD endpoints for conversations
- Add directory validation endpoint
- Add models list endpoint

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: SSE 流式聊天端点（第一部分）

**Files:**
- Create: `javisagent/backend/src/routes/claw/chat.py`
- Modify: `javisagent/backend/src/routes/claw/__init__.py`

**Step 1: 创建聊天路由基础结构**

创建 `javisagent/backend/src/routes/claw/chat.py`:

```python
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
    conversation = db.query(ClawConversation).filter_by(id=conv_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = db.query(ClawMessage).filter_by(
        conversation_id=conv_id
    ).order_by(ClawMessage.created_at).all()

    return [MessageResponse.from_orm(msg) for msg in messages]


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
            conversation_id=conv_id,
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
            conversation_id=conv_id,
            role=MessageRole.ASSISTANT,
            content=assistant_content or "Agent 响应",
            metadata={"tool_calls": tool_calls_data}
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
    conversation = db.query(ClawConversation).filter_by(id=conv_id).first()
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
```

**Step 2: 更新 __init__.py**

修改 `javisagent/backend/src/routes/claw/__init__.py`:

```python
from .conversations import router as conversations_router
from .chat import router as chat_router

__all__ = ["conversations_router", "chat_router"]
```

**Step 3: 注册聊天路由**

修改 `javisagent/backend/src/app.py`:

```python
from src.routes.claw import conversations_router, chat_router

# 注册路由
app.include_router(conversations_router)
app.include_router(chat_router)
```

**Step 4: 测试基础 SSE**

运行后端并测试：
```bash
curl -N -X POST http://localhost:8000/api/claw/conversations/{conv_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello"}'
```

预期：收到 SSE 流响应

**Step 5: 提交**

```bash
git add javisagent/backend/src/routes/claw/
git commit -m "feat(backend): add SSE chat endpoint (基础结构)

- Add chat endpoint with SSE streaming
- Add message history endpoint
- Prepare for Deep Agents integration

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 前端类型定义和 API 客户端

**Files:**
- Create: `javisagent/frontend/src/types/claw.ts`
- Create: `javisagent/frontend/src/services/clawApi.ts`

**Step 1: 创建 TypeScript 类型定义**

创建 `javisagent/frontend/src/types/claw.ts`:

```typescript
export interface ClawConversation {
  id: string;
  title: string;
  working_directory: string;
  llm_model: string;
  created_at: string;
  updated_at: string;
}

export interface ClawMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  subAgents?: SubAgent[];
  planningTasks?: PlanningTask[];
  isStreaming?: boolean;
  timestamp: Date;
}

export interface ToolCall {
  id: string;
  toolName: string;
  status: 'running' | 'success' | 'failed';
  input: any;
  output?: any;
  duration?: number;
  error?: string;
}

export interface SubAgent {
  id: string;
  name: string;
  task: string;
  status: 'running' | 'success' | 'failed';
  progress?: number;
  result?: any;
  duration?: number;
}

export interface PlanningTask {
  id: string;
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
}

export interface ConversationCreate {
  title?: string;
  working_directory: string;
  llm_model?: string;
}

export interface ConversationUpdate {
  title?: string;
  working_directory?: string;
  llm_model?: string;
}

export interface MessageCreate {
  content: string;
}

export interface ModelInfo {
  model_id: string;
  name: string;
  provider: string;
}

export interface SSEEvent {
  type: 'text' | 'tool_call' | 'tool_result' | 'subagent_start' |
        'subagent_progress' | 'subagent_complete' | 'planning' | 'done' | 'error';
  [key: string]: any;
}
```

**Step 2: 创建 API 客户端**

创建 `javisagent/frontend/src/services/clawApi.ts`:

```typescript
import type {
  ClawConversation,
  ClawMessage,
  ConversationCreate,
  ConversationUpdate,
  MessageCreate,
  ModelInfo,
  SSEEvent
} from '../types/claw';

const API_BASE = '/api/claw';

export const clawApi = {
  // 对话管理
  async createConversation(data: ConversationCreate): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('创建对话失败');
    return response.json();
  },

  async listConversations(): Promise<ClawConversation[]> {
    const response = await fetch(`${API_BASE}/conversations`);
    if (!response.ok) throw new Error('获取对话列表失败');
    return response.json();
  },

  async getConversation(id: string): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations/${id}`);
    if (!response.ok) throw new Error('获取对话失败');
    return response.json();
  },

  async updateConversation(id: string, data: ConversationUpdate): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('更新对话失败');
    return response.json();
  },

  async deleteConversation(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('删除对话失败');
  },

  // 消息管理
  async getMessages(convId: string): Promise<ClawMessage[]> {
    const response = await fetch(`${API_BASE}/conversations/${convId}/messages`);
    if (!response.ok) throw new Error('获取消息失败');
    return response.json();
  },

  // SSE 聊天
  async sendMessage(
    convId: string,
    message: MessageCreate,
    onEvent: (event: SSEEvent) => void,
    onError?: (error: Error) => void
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/conversations/${convId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(message)
    });

    if (!response.ok) {
      throw new Error('发送消息失败');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('无法读取响应流');
    }

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      if (onError) {
        onError(error as Error);
      }
      throw error;
    }
  },

  // 工具方法
  async validateDirectory(path: string): Promise<{ valid: boolean; reason?: string }> {
    const response = await fetch(`${API_BASE}/validate-directory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    if (!response.ok) throw new Error('验证目录失败');
    return response.json();
  },

  async listModels(): Promise<ModelInfo[]> {
    const response = await fetch(`${API_BASE}/models`);
    if (!response.ok) throw new Error('获取模型列表失败');
    const data = await response.json();
    return data.models;
  }
};
```

**Step 3: 提交**

```bash
git add javisagent/frontend/src/types/claw.ts javisagent/frontend/src/services/clawApi.ts
git commit -m "feat(frontend): add Claw TypeScript types and API client

- Add comprehensive type definitions
- Add API client with SSE support
- Add conversation and message management methods

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 前端菜单和路由

**Files:**
- Modify: `javisagent/frontend/src/components/Layout/SideMenu.tsx`
- Modify: `javisagent/frontend/src/App.tsx`
- Create: `javisagent/frontend/src/pages/ClawChatPage.tsx` (空文件)

**Step 1: 添加 Claw 菜单项**

修改 `javisagent/frontend/src/components/Layout/SideMenu.tsx`，在 `items` 数组中添加：

```typescript
import { Crab } from 'lucide-react';  // 添加到顶部导入

// 在 items 数组中，settings 之前添加：
{
  key: 'claw',
  label: collapsed ? '' : 'Claw',
  icon: <Crab size={16} />,
  children: [
    {
      key: 'claw-chat',
      label: collapsed ? '' : '对话龙虾',
      icon: <MessageSquare size={16} />
    }
  ]
},
```

**Step 2: 创建空的页面组件**

创建 `javisagent/frontend/src/pages/ClawChatPage.tsx`:

```typescript
import React from 'react';

const ClawChatPage: React.FC = () => {
  return (
    <div>
      <h1>Claw - 对话龙虾</h1>
      <p>功能开发中...</p>
    </div>
  );
};

export default ClawChatPage;
```

**Step 3: 添加路由**

修改 `javisagent/frontend/src/App.tsx`:

```typescript
// 添加导入
import ClawChatPage from './pages/ClawChatPage';

// 在 renderPage 函数中添加 case:
case 'claw-chat':
  return <ClawChatPage />;
```

**Step 4: 测试路由**

运行前端：
```bash
cd javisagent/frontend
npm run dev
```

访问 http://localhost:5173，点击 Claw → 对话龙虾

预期：显示"功能开发中..."页面

**Step 5: 提交**

```bash
git add javisagent/frontend/src/components/Layout/SideMenu.tsx \
        javisagent/frontend/src/App.tsx \
        javisagent/frontend/src/pages/ClawChatPage.tsx
git commit -m "feat(frontend): add Claw menu and routing

- Add Claw menu item with Crab icon
- Add claw-chat route
- Create placeholder ClawChatPage component

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: ClawChatPage 主页面结构

**Files:**
- Modify: `javisagent/frontend/src/pages/ClawChatPage.tsx`

**Step 1: 实现页面基础结构**

修改 `javisagent/frontend/src/pages/ClawChatPage.tsx`:

```typescript
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Select,
  Input,
  Button,
  Empty,
  Spin,
  message,
  Menu,
  Popconfirm,
  Typography,
  Tooltip,
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  EditOutlined,
  FolderOutlined,
  SearchOutlined,
  MenuOutlined,
  CheckOutlined,
  CloseOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { clawApi } from '../services/clawApi';
import type { ClawConversation, ClawMessage, ModelInfo } from '../types/claw';

const ClawChatPage: React.FC = () => {
  // 对话状态
  const [conversations, setConversations] = useState<ClawConversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(() => {
    return localStorage.getItem('claw_chat_conv_id');
  });
  const [convLoading, setConvLoading] = useState(false);

  // 消息状态
  const [messages, setMessages] = useState<ClawMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);

  // 配置状态
  const [workingDirectory, setWorkingDirectory] = useState('');
  const [selectedModel, setSelectedModel] = useState('claude-opus-4-6');
  const [models, setModels] = useState<ModelInfo[]>([]);

  // 编辑状态
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  // 搜索
  const [searchKeyword, setSearchKeyword] = useState('');

  // 响应式
  const [sidebarDrawerOpen, setSidebarDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // 加载对话列表
  const loadConversations = useCallback(async () => {
    setConvLoading(true);
    try {
      const data = await clawApi.listConversations();
      setConversations(data);
    } catch (error) {
      message.error('加载对话列表失败');
    } finally {
      setConvLoading(false);
    }
  }, []);

  // 加载模型列表
  const loadModels = useCallback(async () => {
    try {
      const data = await clawApi.listModels();
      setModels(data);
    } catch (error) {
      message.error('加载模型列表失败');
    }
  }, []);

  // 初始化
  useEffect(() => {
    loadConversations();
    loadModels();
  }, [loadConversations, loadModels]);

  // 保存当前对话 ID
  useEffect(() => {
    if (currentConvId) {
      localStorage.setItem('claw_chat_conv_id', currentConvId);
    } else {
      localStorage.removeItem('claw_chat_conv_id');
    }
  }, [currentConvId]);

  // 响应式监听
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 过滤对话
  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchKeyword.toLowerCase())
  );

  // 对话列表渲染
  const renderConversationList = () => (
    <>
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #f0f0f0' }}>
        <Input
          placeholder="搜索对话..."
          prefix={<SearchOutlined style={{ color: '#999' }} />}
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          allowClear
          size="small"
        />
      </div>
      {convLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin />
        </div>
      ) : filteredConversations.length === 0 ? (
        <Empty description={searchKeyword ? '无匹配对话' : '暂无对话'} style={{ marginTop: 40 }} />
      ) : (
        <Menu
          mode="inline"
          selectedKeys={currentConvId ? [currentConvId] : []}
          style={{ border: 'none' }}
          items={filteredConversations.map((conv) => ({
            key: conv.id,
            icon: <MessageOutlined />,
            label: conv.title,
            onClick: () => setCurrentConvId(conv.id)
          }))}
        />
      )}
    </>
  );

  return (
    <div style={{ display: 'flex', height: '100%', padding: 16, gap: 16 }}>
      {/* 移动端抽屉 */}
      <Drawer
        title="对话历史"
        placement="left"
        open={sidebarDrawerOpen}
        onClose={() => setSidebarDrawerOpen(false)}
        width={280}
        bodyStyle={{ padding: 0 }}
      >
        {renderConversationList()}
      </Drawer>

      {/* 左侧：对话列表（桌面端） */}
      {!isMobile && (
        <Card
          title="对话历史"
          style={{ width: 280, display: 'flex', flexDirection: 'column' }}
          bodyStyle={{ flex: 1, overflow: 'auto', padding: 0 }}
          extra={
            <Tooltip title="新建对话">
              <Button type="primary" icon={<PlusOutlined />} size="small">
                新建
              </Button>
            </Tooltip>
          }
        >
          {renderConversationList()}
        </Card>
      )}

      {/* 右侧：聊天区域 */}
      <Card
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isMobile && <MenuOutlined onClick={() => setSidebarDrawerOpen(true)} />}
            <span>Claw - 对话龙虾</span>
          </div>
        }
        extra={
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <Input
              prefix={<FolderOutlined />}
              placeholder="工作目录"
              value={workingDirectory}
              onChange={(e) => setWorkingDirectory(e.target.value)}
              style={{ width: 200 }}
              size="small"
            />
            <Select
              value={selectedModel}
              onChange={setSelectedModel}
              style={{ width: 160 }}
              size="small"
              options={models.map((m) => ({
                label: m.name,
                value: m.model_id
              }))}
            />
          </div>
        }
      >
        {/* 消息区域 */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {!currentConvId ? (
            <Empty description="选择或创建对话开始聊天" />
          ) : messagesLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
            </div>
          ) : (
            <div>消息列表（待实现）</div>
          )}
        </div>

        {/* 输入区域 */}
        <div style={{ padding: 16, borderTop: '1px solid #f0f0f0' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <Input.TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="输入消息..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={!currentConvId || sending}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => {/* TODO */}}
              disabled={!currentConvId || !inputValue.trim() || sending}
              loading={sending}
            >
              发送
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ClawChatPage;
```

**Step 2: 测试页面**

运行前端并访问 Claw 页面

预期：显示对话列表（空）和聊天区域

**Step 3: 提交**

```bash
git add javisagent/frontend/src/pages/ClawChatPage.tsx
git commit -m "feat(frontend): implement ClawChatPage basic structure

- Add conversation list sidebar
- Add chat area with config panel
- Add responsive layout with drawer
- Prepare for message rendering

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9-12: 剩余前端功能实现

由于篇幅限制，剩余任务包括：

- **Task 9**: 新建对话对话框
- **Task 10**: 消息展示和 SSE 连接
- **Task 11**: 工具调用卡片组件
- **Task 12**: 子智能体和规划卡片组件

这些任务将在执行阶段详细实施。

---

## 执行建议

**推荐执行方式：Subagent-Driven Development**

使用 `superpowers:subagent-driven-development` 技能，为每个任务派发独立的子智能体，在主会话中进行代码审查和迭代。

**优势：**
- 快速并行开发
- 每个任务独立审查
- 灵活调整实施细节

**执行命令：**
```
使用 subagent-driven-development 技能执行此计划
```

---

## 总结

本实施计划将 Claw 功能分解为 12 个可执行任务，每个任务包含详细的步骤、代码示例和测试方法。预计总开发时间 3-5 天。

**关键里程碑：**
- Day 1: 完成后端基础架构（Task 1-5）
- Day 2: 完成前端页面结构（Task 6-8）
- Day 3: 完成消息展示和工具卡片（Task 9-11）
- Day 4: 完成子智能体展示和测试（Task 12）
- Day 5: 优化和 Bug 修复

