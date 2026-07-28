import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from datetime import datetime

from config import settings
from repository import init_db
from travelata_api import TravelataAPIClient
from price_monitor import PriceMonitor
from handlers import start_router, search_router, subscribe_router, callback_router
from cache import cache
from level_feed_loader import refresh_all_feeds
import handlers.state as app_state

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    await init_db()
    logger.info("База данных инициализирована")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        request_timeout=60
    )
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(search_router)
    dp.include_router(subscribe_router)
    dp.include_router(callback_router)

    client = TravelataAPIClient(settings.travelata_login, settings.travelata_password)
    logger.info("Клиент Travelata API создан")

    try:
        await cache.load(client)
        logger.info("Справочники загружены")
    except Exception as e:
        logger.error(f"Не удалось загрузить справочники: {e}")

    feed_loaded_at = None
    if settings.use_feed:
        logger.info("Загрузка фидов при старте...")
        try:
            await refresh_all_feeds()
            app_state.feeds_loaded = True
            feed_loaded_at = datetime.now()
            logger.info("Фиды успешно загружены, поиск доступен")
        except Exception as e:
            logger.exception("Ошибка при загрузке фидов")
            app_state.feeds_loaded = False
    else:
        logger.warning("Использование фидов отключено в настройках")

    monitor = PriceMonitor(bot, last_feed_update=feed_loaded_at)
    asyncio.create_task(monitor.run())
    logger.info("Мониторинг цен запущен")

    logger.info("Бот запущен, начинаем поллинг...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")