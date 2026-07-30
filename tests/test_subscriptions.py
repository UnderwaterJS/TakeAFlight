import pytest
from datetime import date
from repository import (
    get_or_create_user, create_search_criteria, create_subscription,
    get_user_active_subscriptions, deactivate_subscription
)

@pytest.mark.asyncio
async def test_create_subscription(db_session):
    user = await get_or_create_user(telegram_id=123, username="test")
    criteria_data = {
        "user_id": user.id,
        "country_id": 1,
        "departure_city_id": 101,
        "checkin_date_from": date(2026, 12, 16),
        "checkin_date_to": date(2026, 12, 16),
        "nights_min": 7,
        "nights_max": 7,
        "adults": 2,
        "kids": 0,
        "infants": 0,
        "hotel_categories": [4, 5],
        "max_price": 150000
    }
    criteria = await create_search_criteria(criteria_data)
    sub = await create_subscription(user.id, criteria.id)
    assert sub.id is not None
    assert sub.is_active is True

    subs = await get_user_active_subscriptions(user.id)
    assert len(subs) == 1
    assert subs[0].id == sub.id

    await deactivate_subscription(sub.id)
    subs_after = await get_user_active_subscriptions(user.id)
    assert len(subs_after) == 0