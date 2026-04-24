# DEEPCLAW Workspace

An intelligent AI workspace, powered by Large Language Models (LLM) for code assistance and task automation.

## Features

- **Claw Agent** — LLM-powered intelligent assistant with multi-turn conversations, streaming responses, and tool calling
- **Prompt Management** — Create, edit, and manage system prompts
- **Skills System** — Register and manage AI skills to extend agent capabilities
- **MCP Tool Integration** — Connect to external tool servers via Model Context Protocol
- **Document Parsing** — Convert PDF, DOC, images to Markdown using MinerU API
- **Channel Access** — QQ bot channel support

## Tech Stack

- **Frontend**: React + TypeScript + Vite + Ant Design + Lucide React
- **Backend**: Python + FastAPI + SQLAlchemy + SQLite
- **AI**: OpenAI GPT-4o, Anthropic Claude, DeepSeek, Zhipu GLM, Tongyi

## Quick Start

### Prerequisites

- Node.js 16+
- Python 3.10+
- pip
- npm

### Installation

1. **Clone the project**

2. **Install frontend dependencies**
   ```bash
   cd javisagent/frontend
   npm install
   ```

3. **Install backend dependencies**
   ```bash
   cd javisagent/backend
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Copy `javisagent/backend/.env.example` to `.env` and fill in your API keys

5. **Start backend server**
   ```bash
   cd javisagent/backend
   python src/main.py
   ```

6. **Start frontend server**
   ```bash
   cd javisagent/frontend
   npm run dev
   ```

7. **Access the app**
   Open browser at `http://localhost:5173`

## Project Structure

```
javisagent/
├── frontend/                    # Frontend code
│   ├── src/
│   │   ├── pages/              # Page components
│   │   │   ├── ClawChatPage.tsx     # AI chat page
│   │   │   ├── ClawMcpPage.tsx      # MCP tool management
│   │   │   ├── ClawSkillsPage.tsx    # Skills management
│   │   │   ├── PromptManagementPage.tsx # Prompt management
│   │   │   └── ChannelsPage.tsx      # Channel access
│   │   ├── components/         # Components
│   │   │   ├── Claw/           # Claw-related components
│   │   │   └── Layout/         # Layout components
│   │   ├── services/           # API services
│   │   └── types/              # Type definitions
│   └── package.json
├── backend/                     # Backend code
│   ├── src/
│   │   ├── app.py              # FastAPI app
│   │   ├── main.py             # Entry point
│   │   ├── models/             # Data models
│   │   ├── routes/             # API routes
│   │   │   ├── claw/           # Claw Agent routes
│   │   │   ├── document.py     # Document parsing
│   │   │   └── channels.py     # Channel access
│   │   ├── services/           # Service layer
│   │   │   ├── claw/           # Claw Agent core
│   │   │   ├── mineru.py       # MinerU client
│   │   │   └── channels/       # Channel services
│   │   ├── schemas/            # Data schemas
│   │   └── utils/              # Utilities
│   └── requirements.txt
├── config/                      # Configuration files
├── docker-compose.milvus.yml    # Milvus vector database config
└── README.md
```

## Built-in Tools

Claw Agent provides the following built-in tools:

- **file_write** — Write file content
- **file_read** — Read file content
- **bash** — Execute shell commands
- **web_search** — Web search (requires TAVILY_API_KEY)
- **fetch_url** — Fetch web page content

## MCP Support

DEEPCLAW supports connecting to external tool servers via MCP (Model Context Protocol). Once MCP servers are configured, these tools will automatically appear in Claw Agent's tool list.

## API Documentation

After starting the backend server, visit `http://localhost:8000/docs` for auto-generated API documentation.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API Key |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API Key (Claude) |
| `MINERU_API_TOKEN` | No | MinerU document parsing |
| `TAVILY_API_KEY` | No | Tavily web search |

## License

MIT


thanks to : 
https://docs.langchain.com/oss/python/deepagents/overview
https://github.com/langchain-ai/deepagents

nanobot: https://github.com/nanobotai/nanobot