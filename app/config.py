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

    # Booth 本地数据根目录（用于 v2 StorageManager，preview/final 输出）
    BOOTH_DATA_DIR: str = Field(
        default=r"D:\AICreama\booth\data",
        validation_alias="BOOTH_DATA_DIR",
    )

    PUBLIC_BASE_URL: str = "http://localhost:9002"
    MAX_SEGMENT_CONCURRENCY: int = 1
    MAX_BG_CONCURRENCY: int = 1
    
    # 模板缓存目录（默认：app/data/_templates）
    TEMPLATE_CACHE_DIR: str = Field(
        default="app/data/_templates",
        validation_alias="TEMPLATE_CACHE_DIR",
    )
    
    # Platform API 配置
    PLATFORM_BASE_URL: str = Field(
        default="http://localhost:8089",
        validation_alias="PLATFORM_BASE_URL",
    )
    PLATFORM_TIMEOUT_MS: int = Field(
        default=5000,
        validation_alias="PLATFORM_TIMEOUT_MS",
    )


settings = Settings()
