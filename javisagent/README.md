# DEEPCLAW 工作台

DEEPCLAW 是一个智能 AI 工作台，基于大语言模型（LLM）的代码助手与任务自动化平台。

## 功能特性

- **Claw Agent** — 基于 LLM 的智能助手，支持多轮对话、流式响应和工具调用
- **Prompt 管理** — 创建、编辑和管理系统提示词
- **技能系统** — 注册和管理 AI 技能，扩展 Agent 能力
- **MCP 工具接入** — 通过 Model Context Protocol 接入外部工具服务器
- **文档解析** — 使用 MinerU API 将 PDF、DOC、图片等转换为 Markdown
- **渠道接入** — QQ 机器人频道支持

## 技术栈

- **前端**：React + TypeScript + Vite + Ant Design + Lucide React
- **后端**：Python + FastAPI + SQLAlchemy + SQLite
- **AI**：OpenAI GPT-4o, Anthropic Claude, DeepSeek, 智谱 GLM, 通义

## 快速开始

### 前置条件

- Node.js 16+
- Python 3.10+
- pip
- npm

### 安装步骤

1. **克隆项目**

2. **安装前端依赖**
   ```bash
   cd javisagent/frontend
   npm install
   ```

3. **安装后端依赖**
   ```bash
   cd javisagent/backend
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   复制 `javisagent/backend/.env.example` 文件为 `.env`，填写必要的 API Key

5. **启动后端服务**
   ```bash
   cd javisagent/backend
   python src/main.py
   ```

6. **启动前端服务**
   ```bash
   cd javisagent/frontend
   npm run dev
   ```

7. **访问应用**
   打开浏览器访问 `http://localhost:5173`

## 项目结构

```
javisagent/
├── frontend/                    # 前端代码
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   │   ├── ClawChatPage.tsx     # AI 对话页面
│   │   │   ├── ClawMcpPage.tsx      # MCP 工具管理
│   │   │   ├── ClawSkillsPage.tsx    # 技能管理
│   │   │   ├── PromptManagementPage.tsx # Prompt 管理
│   │   │   └── ChannelsPage.tsx      # 渠道接入
│   │   ├── components/         # 组件
│   │   │   ├── Claw/           # Claw 相关组件
│   │   │   └── Layout/         # 布局组件
│   │   ├── services/           # API 服务
│   │   └── types/              # 类型定义
│   └── package.json
├── backend/                     # 后端代码
│   ├── src/
│   │   ├── app.py              # FastAPI 应用
│   │   ├── main.py             # 入口点
│   │   ├── models/             # 数据模型
│   │   ├── routes/             # API 路由
│   │   │   ├── claw/           # Claw Agent 路由
│   │   │   ├── document.py     # 文档解析
│   │   │   └── channels.py     # 渠道接入
│   │   ├── services/           # 服务层
│   │   │   ├── claw/           # Claw Agent 核心
│   │   │   ├── mineru.py       # MinerU 客户端
│   │   │   └── channels/       # 渠道服务
│   │   ├── schemas/            # 数据 Schema
│   │   └── utils/              # 工具函数
│   └── requirements.txt
├── config/                      # 配置文件
├── docker-compose.milvus.yml    # Milvus 向量数据库配置
└── README.md
```

## 内置工具

Claw Agent 提供以下内置工具：

- **file_write** — 写入文件内容
- **file_read** — 读取文件内容
- **bash** — 执行 Shell 命令
- **web_search** — 网络搜索 (需要 TAVILY_API_KEY)
- **fetch_url** — 获取网页内容

## MCP 支持

DEEPCLAW 支持通过 MCP (Model Context Protocol) 接入外部工具服务器。配置 MCP 服务器后，这些工具会自动出现在 Claw Agent 的工具列表中。

## API 文档

启动后端服务后，可访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `OPENAI_API_KEY` | 是 | OpenAI API Key |
| `ANTHROPIC_API_KEY` | 是 | Anthropic API Key (Claude) |
| `MINERU_API_TOKEN` | 否 | MinerU 文档解析 |
| `TAVILY_API_KEY` | 否 | Tavily 网络搜索 |

## 许可证

MIT