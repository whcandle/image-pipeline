from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PIPELINE_HOST: str = "0.0.0.0"
    PIPELINE_PORT: int = 9002
    PIPELINE_DATA_DIR: str = "./app/data"
    PUBLIC_BASE_URL: str = "http://localhost:9002"

    MAX_SEGMENT_CONCURRENCY: int = 1
    MAX_BG_CONCURRENCY: int = 1


settings = Settings()
