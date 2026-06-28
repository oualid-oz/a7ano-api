from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Organization Management Platform"
    debug: bool = False
    environment: str = "development"

    secret_key: str
    database_url: str
    async_database_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"

    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 1

    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"

    vault_master_key: str | None = None

    max_login_attempts: int = 5
    login_lockout_minutes: int = 30
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def build_async_database_url(self) -> Self:
        if self.async_database_url is None:
            self.async_database_url = self.database_url.replace(
                "postgresql://", "postgresql+psycopg_async://"
            )
        return self


settings = Settings()
