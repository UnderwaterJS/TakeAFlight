from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    use_mock_api: bool = False
    
    bot_token: str = Field(..., validation_alias="BOT_TOKEN")
    use_feed: bool = True
    
    search_interval_minutes: int = Field(default=10, validation_alias="SEARCH_INTERVAL_MINUTES")
    api_request_timeout: int = Field(default=30, validation_alias="API_REQUEST_TIMEOUT")
    api_retry_count: int = Field(default=3, validation_alias="API_RETRY_COUNT")

    travelata_api_url: str = Field(default="https://travelata.ru", validation_alias="TRAVELATA_API_URL")

    travelata_login: str = Field(..., validation_alias="TRAVELATA_LOGIN")
    travelata_password: str = Field(..., validation_alias="TRAVELATA_PASSWORD")

    database_url: str = Field(default="sqlite+aiosqlite:///./takeflight.db", validation_alias="DATABASE_URL")

    price_drop_percent: float = Field(default=5.0, validation_alias="PRICE_DROP_PERCENT")

    debug_mode: bool = Field(default=False, validation_alias="DEBUG_MODE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("bot_token")
    @classmethod  # В V2 валидаторы обязательно должны быть classmethod
    def validate_bot_token(cls, v: str) -> str:
        if not v or ":" not in v:
            raise ValueError("BOT_TOKEN must be in a format 'numbers:letters'")
        return v

settings = Settings()