from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_policy"
    REDIS_URL: str = "redis://localhost:6379"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    TAXONOMY_COVERAGE_THRESHOLD: float = 0.25

    @model_validator(mode="after")
    def normalize_db_url(self):
        if self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self


settings = APISettings()
