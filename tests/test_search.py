import pytest
from datetime import date
from repository import search_feed_tours, save_feed_tours

@pytest.mark.asyncio
async def test_search_feed_tours_found(db_session, sample_tour):
    await save_feed_tours([sample_tour])
    tours = await search_feed_tours(
        departure_city="Казань",
        country="Египет",
        date_from=date(2026, 12, 16),
        date_to=date(2026, 12, 16),
        nights_min=7,
        nights_max=7,
        stars=[3, 4, 5],
        max_price=150000,
        limit=10
    )
    assert len(tours) == 1
    assert tours[0].id == "test1"

@pytest.mark.asyncio
async def test_search_feed_tours_not_found(db_session, sample_tour):
    await save_feed_tours([sample_tour])
    tours = await search_feed_tours(
        departure_city="Москва",
        country="Египет",
        date_from=date(2026, 12, 16),
        date_to=date(2026, 12, 16),
        nights_min=7,
        nights_max=7,
        stars=[3, 4, 5],
        max_price=150000,
        limit=10
    )
    assert len(tours) == 0