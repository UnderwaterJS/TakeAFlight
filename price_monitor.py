import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from config import settings
from models import Subscription, SearchCriteria, PriceHistory, Tour
from travelata_api import TravelataAPIClient
# Временно используем заглушку для БД (позже заменим на реальный репозиторий)
from repository import (
    get_active_subscriptions,
    get_criteria_by_id,
    get_last_price,
    save_price_history,
    update_subscription_notified_at
)

logger = logging.getLogger(__name__)

class PriceMonitor:
    # Фоновый мониторинг цен. Запускается как асинхронная задача.
    def __init__(self, bot, api_client: TravelataAPIClient):
        self.bot = bot
        self.api = api_client
        self.interval = settings.search_interval_minutes * 60
        self.drop_threshold = settings.price_drop_percent / 100.0

    async def run(self):
        logger.info("Мониторинг цен запущен (интервал %d сек)", self.interval)
        while True:
            try:
                await self.check_all_subscriptions()
            except Exception as e:
                logger.exception("ОШибка в цикле мониторинга: %s", e)
            await asyncio.sleep(self.interval)

    async def check_all_subscriptions(self):
        subscriptions = await get_active_subscriptions()
        if not subscriptions:
            logger.debug("Нет активных подписок")
            return

        logger.info("Проверка %d подписок", len(subscriptions))
        for sub in subscriptions:
            try:
                await self.check_subscription(sub)
            except Exception as e:
                logger.exception("Ошибка при проверке подписки %d: %s", sub.id, e)

    async def check_subscription(self, subscription: Subscription):
        criteria = await get_criteria_by_id(subscription.criteria_id)
        if not criteria:
            logger.warning("Критерии не найдены для подписки %d", subscription.id)
            return

        tours = await self.api.get_cheapest_tours(
            country_ids=[criteria.country_id] if criteria.country_id else [],
            departure_city=criteria.departure_city_id,
            checkin_date_from=criteria.checkin_date_from,
            checkin_date_to=criteria.checkin_date_to,
            adults=criteria.adults,
            kids=criteria.kids,
            infants=criteria.infants,
            nights_min=criteria.nights_min,
            nights_max=criteria.nights_max,
            resorts=criteria.resorts,
            hotel_categories=criteria.hotel_categories
        )
        if not tours:
            logger.debug("Туры не найдены для подписки %d", subscription.id)
            return

        for tour in tours[:10]:
            last_price = await get_last_price(tour.tourIdentity)
            if last_price is None:
                await save_price_history(tour.tourIdentity, tour.price)
                continue

            if tour.price < last_price:
                price_diff = last_price - tour.price
                price_diff_percent = price_diff / last_price
                if price_diff_percent >= self.drop_threshold:
                    await self.notify_user(
                        subscription.user_id,
                        tour,
                        old_price = last_price,
                        new_price = tour.price
                    )

                    await update_subscription_notified_at(subscription.id)

            await save_price_history(tour.tourIdentity, tour.price)

    async def notify_user(self, user_id: int, tour: Tour, old_price: int, new_price: int):
        message = (
            f"🔔 Цена снизилась!\n"
            f"🏨 {tour.hotelName} ({tour.hotelCategoryName})\n"
            f"📅 Заезд: {tour.checkinDate} на {tour.nights} ночей\n"
            f"💰 Было: {old_price:,} ₽ → Стало: {new_price:,} ₽\n"
            f"⬇️ Снижение на {((old_price - new_price) / old_price * 100):.1f}%\n"
            f"🔗 [Смотреть тур]({tour.tourPageUrl})"
        )
        try:
            await self.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
            logger.info("Уведомление отправлено пользователю %d", user_id)
        except Exception as e:
            logger.error("Не удалось отправить уведомление пользователю %d: %s", user_id, e)