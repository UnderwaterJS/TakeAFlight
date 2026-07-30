import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from repository import Base
from models import Country, DepartureCity, FeedTour
from cache import DirectoryCache

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Очистка после теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(db_engine):
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture(scope="function")
def cache():
    c = DirectoryCache()
    c._loaded = True
    c.country_name_to_id = {"египет": 1, "турция": 2, "китай": 3}
    c.departure_city_name_to_id = {"казань": 101, "москва": 102}
    c.countries = {
        1: Country(id=1, name="Египет", disabled=False),
        2: Country(id=2, name="Турция", disabled=False),
        3: Country(id=3, name="Китай", disabled=False)
    }
    c.departure_cities = {
        101: DepartureCity(id=101, name="Казань", disabled=False),
        102: DepartureCity(id=102, name="Москва", disabled=False)
    }
    return c

@pytest.fixture
def sample_tour():
    return FeedTour(
        id="test1",
        price=100000,
        nights=7,
        hotel_name="Test Hotel",
        hotel_stars=4,
        country="Египет",
        region="Хургада",
        departure_city="Казань",
        departure_date=date(2026, 12, 16),
        operator_name="Test",
        picture_hotel="",
        picture_hotel_800x600="",
        picture_seo_800x620="",
        hotel_url="",
        region_url="",
        country_url="",
        min_country_price_url="",
        min_region_price_url=""
    )