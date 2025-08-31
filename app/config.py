from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./smart_bookkeeper.db"
    
    # WeChat Work Configuration
    WECOM_CORP_ID: str
    WECOM_SECRET: str
    WECOM_TOKEN: str
    WECOM_AES_KEY: str
    WECOM_AGENT_ID: str
    
    # AI Service Configuration
    AI_API_KEY: str
    AI_API_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL_NAME: str = "gpt-3.5-turbo"
    
    # OCR API Configuration
    OCR_API_KEY: str
    OCR_API_BASE_URL: str = "https://v2.xxapi.cn/api/ocr"
    
    # Penetration URL Configuration
    PENETRATE_URL: str = "http://localhost:8000"
    
    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()