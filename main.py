import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from repository import init_db
from travelata_api import TravelataAPIClient
from price_monitor import PriceMonitor
from handlers import start_router, search_router, subscribe_router, callback_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    await init_db()
    logger.info("База данных инициализирована")

    bot = Bot(token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(search_router)
    dp.include_router(subscribe_router)
    dp.include_router(callback_router)

    async with TravelataAPIClient(
        login=settings.travelata_login,
        password=settings.travelata_password
        ) as api_client:
        monitor = PriceMonitor(bot, api_client)
        asyncio.create_task(monitor.run())

        logger.info("Бот запущен, начинаем поллинг...")
        await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")