from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_policy"
    TAXONOMY_COVERAGE_THRESHOLD: float = 0.35


settings = DBSettings()
