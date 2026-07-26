import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from repository import init_db
from interfaces import ITravelataClient

if settings.use_mock_api:
    from mock_travelata import MockTravelataClient as TravelataClient
else:
    from travelata_api import TravelataAPIClient as TravelataClient

from price_monitor import PriceMonitor
from handlers import start_router, search_router, subscribe_router, callback_router
from handlers.search import set_travelata_client, set_cache
from cache import cache
from level_feed_loader import refresh_all_feeds, FEED_URLS
import handlers.state as app_state

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    await init_db()
    logger.info("База данных инициализирована")

    bot = Bot(token=settings.bot_token,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML),
              request_timeout=60)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(search_router)
    dp.include_router(subscribe_router)
    dp.include_router(callback_router)

    if settings.use_mock_api:
        logger.info("Используется МОК-клиент (без реального API)")
        client = TravelataClient()
    else:
        logger.info("Используется реальный клиент Travelata API")
        client = TravelataClient(settings.travelata_login, settings.travelata_password)

    try:
        await cache.load(client)
        logger.info("Справочники загружены")
    except Exception as e:
        logger.error(f"Не удалось загрузить справочники: {e}")

    if settings.use_feed:
        logger.info("Загрузка фидов при старте...")
        try:
            await refresh_all_feeds()
            app_state.feeds_loaded = True
            logger.info("Фиды успешно загружены, поиск доступен")
        except Exception as e:
            logger.exception("Ошибка при загрузке фидов")
            app_state.feeds_loaded = False

        async def periodic_feed_update():
            await asyncio.sleep(1800)  # ждём 30 минут
            while True:
                try:
                    await refresh_all_feeds()
                    app_state.feeds_loaded = True
                    logger.info("Фиды обновлены")
                except Exception as e:
                    logger.exception("Ошибка при обновлении фидов")
                await asyncio.sleep(1800)

        asyncio.create_task(periodic_feed_update())
        logger.info("Запущено периодическое обновление фидов (каждые 30 минут)")

    set_travelata_client(client)
    set_cache(cache)

    monitor = PriceMonitor(bot, client)
    asyncio.create_task(monitor.run())

    logger.info("Бот запущен, начинаем поллинг...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")