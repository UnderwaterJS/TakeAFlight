import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from repository import (
    get_active_subscriptions,
    get_criteria_by_id,
    search_feed_tours,
    update_subscription_price,
    update_subscription_notified_at
)
from cache import cache
from level_feed_loader import refresh_all_feeds

logger = logging.getLogger(__name__)

class PriceMonitor:
    def __init__(self, bot, last_feed_update: Optional[datetime] = None):
        self.bot = bot
        self.interval = settings.search_interval_minutes * 60  # из конфига
        self.drop_threshold = settings.price_drop_percent / 100.0
        self.feed_update_interval = 30 * 60  # обновлять фиды каждые 30 минут
        # Если не передано, используем текущее время (чтобы не обновлять сразу при старте)
        self.last_feed_update = last_feed_update or datetime.now()

    async def run(self):
        logger.info("Мониторинг цен запущен (интервал %d сек)", self.interval)
        while True:
            try:
                # Обновляем фиды, если пришло время
                await self._maybe_update_feeds()
                # Проверяем все подписки
                await self.check_all_subscriptions()
            except Exception as e:
                logger.exception("Ошибка в цикле мониторинга: %s", e)
            await asyncio.sleep(self.interval)

    async def _maybe_update_feeds(self):
        """Обновляет фиды, если прошло более feed_update_interval секунд."""
        now = datetime.now()
        if (now - self.last_feed_update).total_seconds() >= self.feed_update_interval:
            logger.info("Обновление фидов Level.Travel")
            try:
                await refresh_all_feeds()
                self.last_feed_update = now
            except Exception as e:
                logger.exception("Ошибка при обновлении фидов: %s", e)

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

    async def check_subscription(self, subscription):
        criteria = await get_criteria_by_id(subscription.criteria_id)
        if not criteria:
            logger.warning("Критерии не найдены для подписки %d", subscription.id)
            return

        country_name = cache.get_country_name(criteria.country_id) if criteria.country_id else None
        departure_city_name = cache.get_departure_city_name(criteria.departure_city_id) if criteria.departure_city_id else None

        if not country_name or not departure_city_name:
            logger.warning("Не удалось определить страну или город вылета для подписки %d", subscription.id)
            return

        stars = criteria.hotel_categories if criteria.hotel_categories else []
        date_from = criteria.checkin_date_from.date()
        date_to = criteria.checkin_date_to.date()

        tours = await search_feed_tours(
            departure_city=departure_city_name,
            country=country_name,
            date_from=date_from,
            date_to=date_to,
            nights_min=criteria.nights_min or 1,
            nights_max=criteria.nights_max or 30,
            stars=stars,
            max_price=criteria.max_price or 9999999,
            limit=10
        )

        if not tours:
            logger.debug("Туры не найдены для подписки %d", subscription.id)
            return

        min_price = min(t.price for t in tours)

        if subscription.last_price is None:
            await update_subscription_price(subscription.id, min_price)
            logger.debug("Установлена начальная цена %d для подписки %d", min_price, subscription.id)
            return

        old_price = subscription.last_price
        if min_price < old_price:
            drop = old_price - min_price
            drop_percent = drop / old_price
            if drop_percent >= self.drop_threshold:
                await self.notify_user(
                    user_id=subscription.user.telegram_id,
                    old_price=old_price,
                    new_price=min_price,
                    criteria=criteria,
                    tour=tours[0]
                )
                await update_subscription_notified_at(subscription.id)
            await update_subscription_price(subscription.id, min_price)

    async def notify_user(self, user_id: int, old_price: int, new_price: int, criteria, tour):
        message = (
            f"🔔 Цена снизилась!\n"
            f"📍 {cache.get_country_name(criteria.country_id) if criteria.country_id else 'Любая'}, "
            f"вылет из {cache.get_departure_city_name(criteria.departure_city_id) if criteria.departure_city_id else 'Любой'}\n"
            f"📅 {criteria.checkin_date_from.date()} – {criteria.checkin_date_to.date()}\n"
            f"🏨 {tour.hotel_name} ({tour.hotel_stars}★)\n"
            f"💰 Было: {old_price:,} ₽ → Стало: {new_price:,} ₽\n"
            f"⬇️ Снижение на {((old_price - new_price) / old_price * 100):.1f}%\n"
            f"🔗 [Смотреть тур]({tour.hotel_url})"
        )
        try:
            await self.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
            logger.info("Уведомление отправлено пользователю %d", user_id)
        except Exception as e:
            logger.error("Не удалось отправить уведомление пользователю %d: %s", user_id, e)