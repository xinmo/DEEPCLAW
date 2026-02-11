from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import Base, engine
from routes import document

# 创建数据库表
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

@app.get('/')
async def root():
    """根路径"""
    return {"message": "JAVISAGENT API is running"}

@app.get('/health')
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
