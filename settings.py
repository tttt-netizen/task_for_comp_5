from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "leads_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_stream_name: str = "leads_stream"
    redis_consumer_group: str = "core_workers"
    redis_consumer_name: str = "worker_1"
    redis_dedup_ttl_seconds: int = 600
    redis_pending_idle_ms: int = 60000
    redis_read_count: int = 10
    redis_read_block_ms: int = 5000
    redis_dead_letter_stream: str = "leads_dead_letter"

    jwt_secret: str = "super-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 120
    token_issuer_secret: str = "issue-token-secret"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
