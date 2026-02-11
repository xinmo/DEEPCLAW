# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JAVISAGENT is an intelligent document parsing workbench that converts documents and web pages into Markdown using the MinerU API (https://mineru.net). Full-stack app with a React frontend and Python FastAPI backend.

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
- `MINERU_API_TOKEN` — from https://mineru.net
- `DATABASE_URL` — defaults to `sqlite:///./javisagent.db`

## Architecture

### Frontend (React + TypeScript + Vite + Ant Design)
- `pages/DocumentParsePage.tsx` — Main page, orchestrates the parsing workflow
- `components/DocumentParse/` — Feature components: `FileUpload`, `FilePreview`, `MarkdownViewer`, `TaskList`
- `components/Layout/` — `AppLayout` and `SideMenu`
- `services/api.ts` — Centralized axios client for all backend calls

### Backend (FastAPI + SQLAlchemy + SQLite)
- `src/main.py` — Entry point, starts uvicorn
- `src/app.py` — FastAPI app setup, CORS config, router registration
- `src/routes/document.py` — All document parsing endpoints
- `src/services/mineru.py` — MinerU API client (task creation, status polling, result fetching)
- `src/models/task.py` — SQLAlchemy `Task` model
- `src/schemas/task.py` — Pydantic request/response schemas
- `src/utils/file_handler.py` — File upload handling with UUID-based IDs

### Data Flow
1. User uploads a file → `POST /api/document/upload` → saved with UUID filename
2. User triggers parse → `POST /api/document/parse` → creates MinerU task via their API
3. Frontend polls `GET /api/document/task/{task_id}` every 2 seconds for progress
4. MinerU returns parsed Markdown → displayed in `MarkdownViewer`

### MinerU API Integration (see API.txt for full reference)
- Base URL: `https://mineru.net/api/v4`
- Auth: `Authorization: Bearer {token}` header on all requests

**Two parsing flows:**

1. **URL 直接解析** (for publicly accessible URLs):
   - `POST /extract/task` with `{"url": "...", "model_version": "vlm"}` → returns `task_id`
   - `GET /extract/task/{task_id}` → poll until `state=done`, then get `full_zip_url`
   - For HTML URLs, `model_version` must be `"MinerU-HTML"`

2. **文件上传解析** (for local files):
   - `POST /file-urls/batch` with `{"files": [{"name": "file.pdf", "data_id": "..."}], "model_version": "vlm"}` → returns `batch_id` + `file_urls` (pre-signed upload URLs)
   - `PUT file_url` with raw file bytes (no Content-Type header needed)
   - System auto-submits parse task after upload — do NOT call `/extract/task` again
   - `GET /extract-results/batch/{batch_id}` → poll until `state=done`, then get `full_zip_url`

**Task states:** `pending` → `running` → `done` / `failed` (also: `waiting-file`, `converting`)

**Result:** `full_zip_url` points to a ZIP containing Markdown + images. Download and extract to get the parsed content.

**Limits:** 200MB per file, 600 pages max, 2000 pages/day at high priority

**model_version options:** `pipeline` (default), `vlm`, `MinerU-HTML` (required for HTML files)

### Key Patterns
- State management is local React state (no Redux/Context)
- Task statuses: `PENDING` → `RUNNING` → `COMPLETED` / `FAILED`
- Frontend uses Ant Design's grid system with 6-18 column layout split
- Supported formats: PDF, DOC, DOCX, PPT, PPTX, PNG, JPG, HTML
