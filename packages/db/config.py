from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_policy"
    TAXONOMY_COVERAGE_THRESHOLD: float = 0.35

    @model_validator(mode="after")
    def normalize_db_url(self):
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            self.DATABASE_URL = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self


settings = DBSettings()
