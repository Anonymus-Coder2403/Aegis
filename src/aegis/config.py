import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""

    database_url: str = "postgresql://aegis:aegis@localhost:5432/aegis"

    redis_url: str = "redis://localhost:6379"

    opensearch_url: str = "https://localhost:9200"
    opensearch_username: str = "admin"
    opensearch_password: str = "admin123"

    s3_endpoint_url: str = ""
    s3_bucket_name: str = "aegis-documents"
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_use_ssl: bool = True

    storage_mode: str = "local"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    default_chunk_size: int = 512
    default_chunk_overlap: int = 50

    default_top_k: int = 5
    bm25_weight: float = 0.5
    rrf_k: int = 60

    llm_model: str = "gemini-2.0-flash"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
