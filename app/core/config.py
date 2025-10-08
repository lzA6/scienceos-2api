# app/core/config.py

from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    """
    应用配置模型
    - 从 .env 文件自动加载环境变量
    """
    # --- 服务元数据 ---
    APP_NAME: str = "ScienceOS-2API"
    APP_VERSION: str = "1.1.0" # 版本升级
    DESCRIPTION: str = "一个将 ScienceOS 网页版聊天功能封装为 OpenAI 兼容 API 的高性能代理服务。"

    # --- 认证与安全 ---
    # 保护 API 的主密钥，客户端需在 Authorization Header 中提供
    API_MASTER_KEY: Optional[str] = None
    # ScienceOS 网站的认证令牌
    SCIENCEOS_AUTH_TOKEN: str = ""

    # --- 服务配置 ---
    LISTEN_PORT: int = 8082
    APP_PORT: int = 8080

    # --- 新增：模型列表 ---
    # 定义客户端可见的模型名称列表
    SUPPORTED_MODELS: List[str] = [
        "scienceos-gemini",
        "scienceos-deep-research" # 您可以根据需要添加更多别名
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

# 创建全局配置实例
settings = Settings()
