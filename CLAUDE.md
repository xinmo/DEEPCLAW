# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JAVISAGENT 是一个智能工作台，提供三大核心功能模块：
1. **智能解析** — 使用 MinerU API 将文档和网页转换为 Markdown
2. **智能翻译** — 实时语音翻译、声音克隆、会议同传
3. **智能知识库** — RAG 知识库管理与问答系统

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

**文档解析模块：**
- `MINERU_API_TOKEN` — from https://mineru.net
- `DATABASE_URL` — defaults to `sqlite:///./javisagent.db`

**翻译模块：**
- `ELEVENLABS_API_KEY` — ElevenLabs 语音合成/克隆
- `XFYUN_APP_ID`, `XFYUN_API_KEY`, `XFYUN_API_SECRET` — 科大讯飞 ASR/翻译

**知识库模块：**
- `MILVUS_HOST`, `MILVUS_PORT` — Milvus 向量数据库 (默认 localhost:19530)
- `OPENAI_API_KEY`, `OPENAI_BASE_URL` — OpenAI Embedding & LLM
- `ANTHROPIC_API_KEY` — Claude LLM
- `ZHIPU_API_KEY` — 智谱 AI
- `DASHSCOPE_API_KEY` — 阿里通义
- `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` — DeepSeek

## Architecture

### Frontend Structure
```
src/
├── pages/
│   ├── DocumentParsePage.tsx    # 文档解析页面
│   ├── RealtimeTranslatePage.tsx # 实时翻译页面
│   ├── KnowledgeBasePage.tsx    # 知识库管理页面
│   └── KnowledgeChatPage.tsx    # 知识问答页面
├── components/
│   ├── DocumentParse/           # 文档解析组件
│   │   ├── FileUpload.tsx
│   │   ├── FilePreview.tsx
│   │   ├── MarkdownViewer.tsx
│   │   └── TaskList.tsx
│   ├── Translate/               # 翻译组件
│   │   ├── VoiceClone.tsx       # 声音克隆
│   │   ├── TextToSpeech.tsx     # 文字转语音
│   │   └── MeetingMode.tsx      # 会议翻译模式
│   └── Layout/
│       ├── AppLayout.tsx
│       └── SideMenu.tsx
├── services/
│   ├── api.ts                   # 文档解析 API
│   ├── translateApi.ts          # 翻译 API
│   └── knowledgeApi.ts          # 知识库 API
├── hooks/
│   ├── useWebSocket.ts          # WebSocket 连接
│   └── useAudioPlayer.ts        # 音频播放
└── types/
    ├── translate.ts             # 翻译类型定义
    └── knowledge.ts             # 知识库类型定义
```

### Backend Structure
```
src/
├── main.py                      # Entry point
├── app.py                       # FastAPI app, CORS, routers
├── routes/
│   ├── document.py              # 文档解析路由
│   ├── translate/               # 翻译路由
│   │   ├── clone.py             # 声音克隆 API
│   │   └── ws.py                # WebSocket 实时翻译
│   └── knowledge/               # 知识库路由
│       ├── kb.py                # 知识库 CRUD
│       ├── documents.py         # 文档管理
│       └── chat.py              # 问答聊天 (SSE 流式)
├── services/
│   ├── mineru.py                # MinerU API 客户端
│   ├── translate/               # 翻译服务
│   │   ├── config.py            # 翻译配置
│   │   ├── elevenlabs.py        # ElevenLabs TTS/克隆
│   │   ├── xfyun_asr.py         # 讯飞语音识别
│   │   ├── xfyun_translate.py   # 讯飞翻译
│   │   └── meeting.py           # 会议模式逻辑
│   └── knowledge/               # 知识库服务
│       ├── config.py            # 知识库配置
│       ├── embedding.py         # 向量嵌入
│       ├── vector_store.py      # Milvus 向量存储
│       ├── retriever.py         # 检索器
│       ├── llm.py               # LLM 调用
│       └── document_processor.py # 文档处理/切片
├── models/
│   ├── task.py                  # 解析任务模型
│   └── knowledge.py             # 知识库/文档/对话模型
├── schemas/
│   ├── task.py                  # 解析任务 Schema
│   ├── translate.py             # 翻译 Schema
│   └── knowledge.py             # 知识库 Schema
├── audio/
│   ├── vad.py                   # 语音活动检测
│   └── segmenter.py             # 音频分段
└── utils/
    └── file_handler.py          # 文件处理
```

## Module Details

### 1. 智能解析模块

**数据流：**
1. 用户上传文件 → `POST /api/document/upload` → UUID 文件名保存
2. 触发解析 → `POST /api/document/parse` → 创建 MinerU 任务
3. 前端轮询 `GET /api/document/task/{task_id}` 获取进度
4. 解析完成 → Markdown 展示在 `MarkdownViewer`

**MinerU API：**
- Base URL: `https://mineru.net/api/v4`
- 支持 URL 直接解析和文件上传解析两种模式
- 支持格式：PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, HTML
- 限制：200MB/文件，600页/文件，2000页/天

### 2. 智能翻译模块

**功能：**
- **声音克隆** — 上传音频样本，克隆用户声音
- **文字转语音** — 使用克隆声音或预设声音合成语音
- **会议翻译** — 实时中英双向翻译，支持双人会议模式

**技术实现：**
- WebSocket 实时通信
- 科大讯飞 ASR 语音识别 + 翻译
- ElevenLabs TTS 语音合成
- VAD 语音活动检测

### 3. 智能知识库模块

**功能：**
- 知识库 CRUD 管理
- 文档上传与自动切片 (支持 PDF, DOC, DOCX, TXT, MD)
- RAG 检索增强问答
- SSE 流式响应
- 多轮对话持久化

**技术实现：**
- Milvus 向量数据库存储
- 多 Embedding 模型支持 (OpenAI, 智谱等)
- 多 LLM 支持 (GPT-4o, Claude, DeepSeek, 通义等)
- 文档切片：500 字符/块，100 字符重叠

## Key Patterns

- 状态管理：本地 React state (无 Redux/Context)
- 任务状态：`PENDING` → `RUNNING` → `COMPLETED` / `FAILED`
- 前端布局：Ant Design Grid，可折叠侧边栏
- 实时通信：WebSocket (翻译)，SSE (知识问答)
- 文件命名：UUID-based
