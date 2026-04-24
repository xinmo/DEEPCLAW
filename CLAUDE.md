# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DEEPCLAW 是一个智能工作台，基于 AI 大语言模型（LLM）的代码助手与任务自动化平台。

技术栈：React + TypeScript + Vite + Ant Design 前端，Python FastAPI + SQLAlchemy 后端。

## Development Commands

### Frontend (from `javisagent/frontend/`)
```bash
npm install          # Install dependencies
npm run dev          # Dev server on http://localhost:5173
npm run build        # Production build
npm run lint         # ESLint
npm run preview      # Preview production build
```

### Backend (from `javisagent/backend/`)
```bash
pip install -r requirements.txt   # Install dependencies
python src/main.py                # Start server on http://localhost:8000
```

Vite proxies `/api` requests to `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Environment Setup
Backend requires a `.env` file in `javisagent/backend/` with:

**Claw Agent 模块：**
- `OPENAI_API_KEY`, `OPENAI_BASE_URL` — OpenAI API
- `ANTHROPIC_API_KEY` — Anthropic Claude API
- `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` — DeepSeek API
- `ZHIPU_API_KEY` — 智谱 GLM API
- `DASHSCOPE_API_KEY` — 阿里通义 API
- `DATABASE_URL` — defaults to `sqlite:///./javisagent.db`
- `TAVILY_API_KEY` — Tavily 网络搜索 (可选)

**文档解析模块：**
- `MINERU_API_TOKEN` — from https://mineru.net

**渠道接入模块：**
- `QQ_BOT_TOKEN`, `QQ_BOT_SECRET` — QQ 机器人配置

## Architecture

### Frontend Structure
```
src/
├── pages/
│   ├── ClawChatPage.tsx         # Claw AI 对话页面
│   ├── ClawMcpPage.tsx          # MCP 工具管理
│   ├── ClawSkillsPage.tsx       # 技能管理
│   ├── PromptManagementPage.tsx  # Prompt 管理
│   ├── ChannelsPage.tsx          # 渠道接入 (QQ)
│   └── FileWriteDrawerPrototype.html # 文件写入抽屉原型
├── components/
│   ├── Claw/
│   │   ├── DirectoryBrowser.tsx   # 目录浏览
│   │   ├── PlanningCard.tsx        # 规划卡片
│   │   ├── PromptDebugPanel.tsx    # Prompt 调试面板
│   │   ├── ShellExecutionCard.tsx  # Shell 执行卡片
│   │   ├── SubAgentCard.tsx        # 子代理卡片
│   │   └── ToolCallCard.tsx        # 工具调用卡片
│   └── Layout/
│       ├── AppLayout.tsx
│       └── SideMenu.tsx
├── services/
│   ├── clawApi.ts               # Claw Agent API
│   ├── promptApi.ts             # Prompt 管理 API
│   └── channelApi.ts            # 渠道 API
├── hooks/
│   └── useWebSocket.ts          # WebSocket 连接
└── types/
    ├── claw.ts                  # Claw 类型定义
    └── channel.ts               # 渠道类型定义
```

### Backend Structure
```
src/
├── main.py                      # Entry point
├── app.py                       # FastAPI app, CORS, routers
├── init_db.py                   # 数据库初始化
├── models/
│   ├── base.py                  # SQLAlchemy Base
│   ├── claw.py                  # Claw 会话/消息/工具调用模型
│   ├── channels.py             # QQ 渠道配置模型
│   └── task.py                  # 解析任务模型
├── schemas/
│   ├── claw.py                  # Claw 请求/响应 Schema
│   ├── channels.py             # 渠道 Schema
│   └── task.py                  # 任务 Schema
├── routes/
│   ├── document.py              # 文档解析路由
│   ├── channels.py             # QQ 渠道路由
│   └── claw/
│       ├── conversations.py    # 会话管理
│       ├── chat.py              # 对话聊天 (流式)
│       ├── prompts.py           # Prompt CRUD
│       ├── skills.py            # 技能注册
│       └── mcp.py              # MCP 工具管理
├── services/
│   ├── mineru.py               # MinerU API 客户端
│   ├── claw/
│   │   ├── agent.py            # Claw Agent 核心
│   │   ├── tools.py            # 内置工具 (web_search, fetch_url, bash, write, read)
│   │   ├── mcp_tools.py       # MCP 工具桥接 (langchain-mcp-adapters)
│   │   ├── prompt_registry.py  # Prompt 注册表
│   │   ├── skill_registry.py  # 技能注册表
│   │   ├── prompt_debug.py     # Prompt 调试
│   │   └── local_context.py   # 本地上下文
│   └── channels/
│       ├── runtime.py          # 渠道运行时
│       ├── registry.py         # 渠道注册表
│       └── claw_bridge.py      # Claw 桥接
├── audio/
│   ├── vad.py                  # 语音活动检测
│   └── segmenter.py            # 音频分段
└── utils/
    └── file_handler.py         # 文件处理
```

## Module Details

### 1. Claw Agent

**核心功能：**
- AI 对话：基于 LLM 的智能助手，支持多轮对话和流式响应
- Prompt 管理：创建、编辑、删除系统提示词
- 技能管理：注册和管理 AI 技能
- MCP 工具：通过 MCP (Model Context Protocol) 接入外部工具服务器
- 文件操作：内置 file_write, file_read, bash, web_search, fetch_url 等工具

**技术实现：**
- 支持多种 LLM：OpenAI GPT-4o, Claude, DeepSeek, 智谱 GLM, 通义
- 流式响应（SSE）
- MCP 工具接入（通过 langchain-mcp-adapters）
- 会话持久化 (SQLite)
- 工具调用记录和展示

### 2. 文档解析模块

**数据流：**
1. 用户上传文件 → `POST /api/document/upload` → UUID 文件名保存
2. 触发解析 → `POST /api/document/parse` → 创建 MinerU 任务
3. 前端轮询 `GET /api/document/task/{task_id}` 获取进度
4. 解析完成 → Markdown 展示

**MinerU API：**
- Base URL: `https://mineru.net/api/v4`
- 支持格式：PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, HTML
- 限制：200MB/文件，600页/文件，2000页/天

### 3. 渠道接入模块

**支持：**
- QQ 机器人：通过 QQ 频道与 Claw Agent 对话

**技术实现：**
- botpy 框架
- 渠道运行时统一管理
- Claw Agent 桥接

## Key Patterns

- 状态管理：本地 React state (无 Redux/Context)
- 任务状态：`PENDING` → `RUNNING` → `COMPLETED` / `FAILED`
- 前端布局：Ant Design Grid，可折叠侧边栏
- 实时通信：SSE (流式对话)
- 文件命名：UUID-based