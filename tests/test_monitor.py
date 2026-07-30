import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date
from price_monitor import PriceMonitor

@pytest.mark.asyncio
async def test_price_drop_detection():
    bot_mock = AsyncMock()
    monitor = PriceMonitor(bot_mock)
    monitor.drop_threshold = 0.05

    sub = MagicMock()
    sub.id = 1
    sub.last_price = 100000
    sub.criteria_id = 1
    sub.user = MagicMock()
    sub.user.telegram_id = 123456

    criteria = MagicMock()
    criteria.id = 1
    criteria.country_id = 1
    criteria.departure_city_id = 101
    criteria.checkin_date_from = date(2026, 12, 16)  # уже date
    criteria.checkin_date_to = date(2026, 12, 16)
    criteria.nights_min = 7
    criteria.nights_max = 7
    criteria.hotel_categories = [4, 5]
    criteria.max_price = 150000

    with patch('price_monitor.get_criteria_by_id', new_callable=AsyncMock) as mock_get_criteria:
        mock_get_criteria.return_value = criteria

        with patch('price_monitor.cache') as mock_cache:
            mock_cache.get_country_name.return_value = "Египет"
            mock_cache.get_departure_city_name.return_value = "Казань"

            with patch('price_monitor.search_feed_tours', new_callable=AsyncMock) as mock_search:
                mock_tour = MagicMock()
                mock_tour.price = 90000
                mock_tour.hotel_name = "Test Hotel"
                mock_tour.hotel_stars = 4
                mock_tour.hotel_url = "http://test.com"
                mock_search.return_value = [mock_tour]

                with patch('price_monitor.update_subscription_price', new_callable=AsyncMock) as mock_update_price, \
                     patch('price_monitor.update_subscription_notified_at', new_callable=AsyncMock) as mock_update_notified:

                    await monitor.check_subscription(sub)

                    bot_mock.send_message.assert_called_once()
                    mock_update_price.assert_called_once_with(1, 90000)
                    mock_update_notified.assert_called_once_with(1)