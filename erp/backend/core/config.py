from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./erp.db"
    SECRET_KEY: str = "dev-secret-troque-em-producao"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480   # 8h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost"]
    FERNET_KEY: str = ""  # base64 Fernet key para CPF/CNPJ

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
