from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Standart Reserve"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    database_url: str = "postgresql://postgres:postgres@postgres:5432/standart_reserve"
    backend_cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost",
        "http://127.0.0.1:5173",
        "http://127.0.0.1",
    ]
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 7

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
