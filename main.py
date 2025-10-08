# main.py - ScienceOS-2API (v1.1.0)

import traceback
import time
import logging
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.providers.scienceos_provider import ScienceOSProvider

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI 应用初始化 ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.DESCRIPTION
)

# --- 实例化 Provider ---
# 唯一的 Provider，处理所有逻辑
provider = ScienceOSProvider()

# --- 认证依赖项 ---
async def verify_api_key(authorization: Optional[str] = Header(None)):
    """
    检查 API 密钥的依赖项。
    如果设置了 API_MASTER_KEY，则请求头中必须包含正确的密钥。
    """
    if not settings.API_MASTER_KEY:
        # 如果未配置主密钥，则允许所有请求通过 (不推荐在生产环境中使用)
        logger.warning("警告：未配置 API_MASTER_KEY，服务将对所有请求开放。")
        return

    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing Authorization header.",
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication scheme. Use 'Bearer <your_api_key>'.",
        )
    
    if token != settings.API_MASTER_KEY:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid API Key.",
        )

# --- API 路由 ---

@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request):
    """
    核心路由：将所有聊天补全请求转发给 Provider 处理。
    在处理前会先通过 verify_api_key 进行认证。
    """
    try:
        request_data = await request.json()
        logger.info("接收到聊天请求，认证通过，路由到 ScienceOSProvider...")
        return await provider.chat_completion(request_data)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": {"message": f"Internal Server Error: {str(e)}", "type": "api_error"}}
        )

# --- 新增的模型列表路由 ---
@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    """
    新增的路由，用于返回兼容OpenAI格式的模型列表。
    客户端应用可以通过这个端点发现可用的模型。
    """
    logger.info("接收到模型列表请求，认证通过...")
    
    # 从配置文件读取支持的模型名称列表
    model_names: List[str] = settings.SUPPORTED_MODELS
    
    # 构建符合 OpenAI API 规范的返回格式
    model_data: List[Dict[str, Any]] = []
    for name in model_names:
        model_data.append({
            "id": name,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "system"  # 或 "ScienceOS"
        })
        
    return {
        "object": "list",
        "data": model_data
    }

@app.get("/", include_in_schema=False)
def root():
    """根路由，提供服务基本信息，无需认证。"""
    return {"message": f"Welcome to {settings.APP_NAME}", "version": settings.APP_VERSION}

logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 已启动。")
