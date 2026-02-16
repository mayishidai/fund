from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# 配置
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 创建 FastAPI 应用实例
app = FastAPI()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保static目录存在
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# 挂载静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 导入API路由
from app.api import auth, funds, gold

# 注册路由
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(funds.router, prefix="/api", tags=["funds"])
app.include_router(gold.router, prefix="/api", tags=["gold"])
