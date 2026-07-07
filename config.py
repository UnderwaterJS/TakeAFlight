from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    use_mock_api: bool = False
    #general bot`s options
    bot_token: str = Field(..., env="BOT_TOKEN")

    #search options
    search_interval_minutes: int = Field(default=10, env="SEARCH_INTERVAL_MINUTES")
    api_request_timeout: int = Field(default=30, env="API_REQUEST_TIMEOUT")
    api_retry_count: int = Field(default=3, env="API_RETRY_COUNT")

    # API Travelata
    travelata_api_url: str = Field(default="https://api-gateway.travelata.ru", env="TRAVELATA_API_URL")

    # API Travelata credentials
    travelata_login: str = Field(..., env="TRAVELATA_LOGIN")  # обязательное поле
    travelata_password: str = Field(..., env="TRAVELATA_PASSWORD")

    #database
    database_url: str = Field(default="sqlite+aiosqlite:///./takeflight.db", env="DATABASE_URL")

    #notifications
    price_drop_percent: float = Field(default=5.0, env="PRICE_DROP_PERCENT")

    debug_mode: bool = Field(default=False, env="DEBUG_MODE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False # for API_TIMEOUT

    @validator("bot_token")
    def validate_bot_token(cls, v):
        if not v or ":" not in v:
            raise ValueError("BOT_TKORN must be i na format 'numbers:letters'")
        return v

settings = Settings()