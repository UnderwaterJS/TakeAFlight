from config import settings

def main():
    print("✅ Конфигурация загружена успешно!")
    print(f"Bot token: {settings.bot_token[:10]}... (первые 10 символов)")
    print(f"Search interval: {settings.search_interval_minutes} мин")
    print(f"API timeout: {settings.api_request_timeout} сек")
    print(f"Database URL: {settings.database_url}")
    print(f"Debug mode: {settings.debug_mode}")
    print(f"Travelata API URL: {settings.travelata_api_url}")

if __name__ == "__main__":
    main()