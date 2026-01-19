from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # 从 .env 读取；extra ignore 表示 .env 里多余字段不报错
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PIPELINE_HOST: str = "0.0.0.0"
    PIPELINE_PORT: int = 9002

    # ✅ 关键修复：必须有类型注解，否则 Pydantic v2 会报 non-annotated attribute
    # 并且支持从环境变量 PIPELINE_DATA_DIR 覆盖
    PIPELINE_DATA_DIR: str = Field(
        default=r"D:\AICreama\booth\data",
        validation_alias="PIPELINE_DATA_DIR",
    )

    PUBLIC_BASE_URL: str = "http://localhost:9002"
    MAX_SEGMENT_CONCURRENCY: int = 1
    MAX_BG_CONCURRENCY: int = 1


settings = Settings()
