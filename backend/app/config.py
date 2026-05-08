from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SUIT API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./suit_api.db"
    redis_url: str = "redis://localhost:6379/0"
    timezone: str = "Asia/Shanghai"
    debug: bool = False
    auto_create_tables: bool = True
    gpu_metrics_retention_days: int = 7
    node_heartbeat_timeout_seconds: int = 60
    gpu_metrics_interval_seconds: int = 30
    gpu_hour_rate: float = 1.0
    api_input_rate_per_1k_tokens: float = 0.001
    api_output_rate_per_1k_tokens: float = 0.002
    cors_allow_origins: str = "*"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    agent_timeout: int = 30
    agent_request_timeout: int = 30
    model_health_timeout: int = 60
    model_health_interval: float = 2.0
    default_agent_port: int = 9000
    default_model_container_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
