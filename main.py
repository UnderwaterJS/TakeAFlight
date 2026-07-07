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
from handlers.search import set_travelata_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    await init_db()
    logger.info("База данных инициализирована")

    bot = Bot(token=settings.bot_token,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(search_router)
    dp.include_router(subscribe_router)
    dp.include_router(callback_router)

    if settings.use_mock_api:
        logger.info("Используется МОК-клиент (без реального API)")
        client = TravelataClient()  # MockTravelataClient
    else:
        logger.info("Используется реальный клиент Travelata API")
        client = TravelataClient(settings.travelata_login, settings.travelata_password)

    set_travelata_client(client)

    monitor = PriceMonitor(bot, client)
    asyncio.create_task(monitor.run())

    logger.info("Бот запущен, начинаем поллинг...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")