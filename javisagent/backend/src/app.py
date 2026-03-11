from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.models import Base, engine
# 确保所有模型都被导入
from src.models.claw import ClawConversation, ClawMessage, ClawToolCall
from src.models.task import Task
from src.models.knowledge import KnowledgeBase, KBDocument, Conversation, Message

from src.routes import document
from src.routes.translate import clone_router, ws_router
from src.routes.knowledge import kb_router, documents_router, chat_router, graph_router
from src.routes.claw import conversations_router, chat_router as claw_chat_router
from src.routes.claw.prompts import router as claw_prompts_router

# 创建数据库表（在所有模型导入之后）
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="JAVISAGENT API",
    description="智能解析工作台 API",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
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

@app.get('/')
async def root():
    """根路径"""
    return {"message": "JAVISAGENT API is running"}

@app.get('/health')
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
