from fastapi import FastAPI, Request, Query, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base, engine
from app.api import api_router
from app.config import settings
from app.security import create_access_token
from jose import JWTError, jwt
from typing import Optional
import uvicorn
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_token(token: str) -> Optional[str]:
    """验证token并返回用户ID"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None

# 创建FastAPI应用实例
app = FastAPI(
    title="SmartBookkeeper",
    description="智能记账机器人后端服务",
    version="1.0.0"
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 挂载log目录用于OCR API访问临时图片文件
app.mount("/log", StaticFiles(directory="log"), name="log")

# 配置模板目录
templates = Jinja2Templates(directory="app/templates")

# 挂载API路由
app.include_router(api_router, prefix="")

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的操作"""
    logger.info("Starting up SmartBookkeeper application...")
    
    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的操作"""
    logger.info("Shutting down SmartBookkeeper application...")
    
    # 关闭数据库连接
    await engine.dispose()
    
    logger.info("Database connections closed")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, token: Optional[str] = Query(None)):
    """根路径，返回欢迎页面"""
    if token:
        # 验证token并获取用户ID
        user_id = verify_token(token)
        if user_id:
            # 将用户ID传递给模板
            return templates.TemplateResponse("index.html", {"request": request, "user_id": user_id})
        else:
            # token无效，返回错误页面
            return templates.TemplateResponse("index.html", {"request": request, "error": "无效的访问链接或链接已过期"})
    else:
        # 没有token，返回普通页面
        return templates.TemplateResponse("index.html", {"request": request})

@app.get("/token/{access_token}", response_class=HTMLResponse)
async def token_access(request: Request, access_token: str):
    """通过路径参数验证token并返回管理页面"""
    # 验证token并获取用户ID
    user_id = verify_token(access_token)
    if user_id:
        # 将用户ID传递给模板
        return templates.TemplateResponse("index.html", {"request": request, "user_id": user_id})
    else:
        # token无效，返回错误页面
        return templates.TemplateResponse("index.html", {"request": request, "error": "无效的访问链接或链接已过期"})

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )