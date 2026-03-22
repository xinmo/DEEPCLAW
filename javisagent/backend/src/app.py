from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.models import Base, engine
from src.models.channels import ChannelConfig, ChannelSession
from src.models.claw import ClawConversation, ClawMessage, ClawToolCall
from src.models.knowledge import Conversation, KBDocument, KnowledgeBase, Message
from src.models.task import Task
from src.models.industry_research import DeepResearch, IndustryEdge, IndustryNode, IndustryResearch
from src.routes import document
from src.routes.channels import router as channels_router
from src.routes.industry_research import research_router as industry_research_router, stream_router as industry_stream_router
from src.routes.claw import conversations_router, chat_router as claw_chat_router, skills_router, mcp_router as claw_mcp_router
from src.routes.claw.prompts import router as claw_prompts_router
from src.routes.knowledge import chat_router, documents_router, graph_router, kb_router
from src.routes.translate import clone_router, ws_router
from src.services.channels.runtime import channel_runtime

# Ensure all models are imported before creating tables.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="JAVISAGENT API",
    description="JAVISAGENT backend API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document.router)
app.include_router(clone_router)
app.include_router(ws_router)
app.include_router(kb_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(graph_router)
app.include_router(conversations_router)
app.include_router(claw_chat_router)
app.include_router(claw_prompts_router, prefix="/api/claw", tags=["claw-prompts"])
app.include_router(skills_router, prefix="/api/claw", tags=["claw-skills"])
app.include_router(claw_mcp_router, prefix="/api/claw", tags=["claw-mcp"])
app.include_router(channels_router)
app.include_router(industry_research_router)
app.include_router(industry_stream_router)


@app.on_event("startup")
async def startup_channels() -> None:
    await channel_runtime.initialize()


@app.on_event("shutdown")
async def shutdown_channels() -> None:
    await channel_runtime.shutdown()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "JAVISAGENT API is running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
