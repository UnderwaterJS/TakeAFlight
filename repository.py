import logging
from datetime import datetime, date
from symtable import Class
from typing import Optional, List

from models import SearchCriteria, FeedTour
from sqlalchemy import (Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text, JSON, Index, Date)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, selectinload
from sqlalchemy import select, update, delete

from config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    registered_at = Column(DateTime, default=datetime.now())
    is_active = Column(Boolean, default=True)

    subscriptions = relationship("SubscriptionORM", back_populates="user", cascade="all, delete-orphan")
    search_criteria = relationship("SearchCriteriaORM", back_populates="user", cascade="all, delete-orphan")

class SearchCriteriaORM(Base):
    __tablename__ = "search_criteria"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    country_id = Column(Integer, nullable=True)
    departure_city_id = Column(Integer, nullable=False)
    checkin_date_from = Column(DateTime, nullable=False)
    checkin_date_to = Column(DateTime, nullable=False)
    nights_min = Column(Integer, nullable=True)
    nights_max = Column(Integer, nullable=True)
    adults = Column(Integer, default=2)
    kids = Column(Integer, default=0)
    infants = Column(Integer, default=0)
    hotel_categories = Column(JSON, default=[])  # список ID категорий
    resorts = Column(JSON, default=[])  # список ID курортов
    max_price = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("UserORM", back_populates="search_criteria")
    subscriptions = relationship("SubscriptionORM", back_populates="criteria")

class SubscriptionORM(Base):
    __tablename__ = "subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    criteria_id = Column(Integer, ForeignKey("search_criteria.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_notified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_price = Column(Integer, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    user = relationship("UserORM", back_populates="subscriptions")
    criteria = relationship("SearchCriteriaORM", back_populates="subscriptions")

class PriceHistoryORM(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    tour_identity = Column(String, nullable=False, index=True)
    price = Column(Integer, nullable=False)
    checked_at = Column(DateTime, default=datetime.now, index=True)

class FeedTourORM(Base):
    __tablename__ = "feed_tours"
    id = Column(String, primary_key=True, index=True)
    price = Column(Integer)
    nights = Column(Integer)
    hotel_name = Column(String)
    hotel_stars = Column(Integer, default=0)
    country = Column(String, index=True)
    region = Column(String)
    departure_city = Column(String, index=True)
    departure_date = Column(Date, index=True)
    operator_name = Column(String)
    picture_hotel = Column(String)
    picture_hotel_800x600 = Column(String)
    picture_seo_800x620 = Column(String)
    hotel_url = Column(String)
    region_url = Column(String)
    country_url = Column(String)
    min_country_price_url = Column(String)
    min_region_price_url = Column(String)
    feed_updated_at = Column(DateTime, default=datetime.now)
    __table_args__ = (
        Index('idx_feed_departure_city_country', 'departure_city', 'country'),
        Index('idx_feed_departure_date', 'departure_date'),
        Index('idx_feed_hotel_stars_price', 'hotel_stars', 'price'),
    )

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("База данных инициализирована (таблицы созданы)")

async def create_user(telegram_id: int,
                      username: str = None,
                      first_name: str = None,
                      last_name: str = None) -> UserORM:
    async with AsyncSessionLocal() as session:
        user = UserORM(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

async def get_user_by_telegram_id(telegram_id: int) -> Optional[UserORM]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

async def get_or_create_user(telegram_id: int, **kwargs) -> UserORM:
    user = await get_user_by_telegram_id(telegram_id)
    if user is None:
        user = await create_user(telegram_id, **kwargs)
    return user

async def create_search_criteria(data: dict) -> SearchCriteriaORM:
    async with AsyncSessionLocal() as session:
        criteria = SearchCriteriaORM(**data)
        session.add(criteria)
        await session.commit()
        await session.refresh(criteria)
        return criteria


async def get_criteria_by_id(criteria_id: int) -> Optional[SearchCriteriaORM]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SearchCriteriaORM).where(SearchCriteriaORM.id == criteria_id)
        )
        return result.scalar_one_or_none()


async def get_criteria_by_user(telegram_id: int) -> List[SearchCriteriaORM]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SearchCriteriaORM)
            .join(UserORM)
            .where(UserORM.telegram_id == telegram_id)
            .order_by(SearchCriteriaORM.created_at.desc())
        )
        return result.scalars().all()

async def create_subscription(user_id: int, criteria_id: int) -> SubscriptionORM:
    async with AsyncSessionLocal() as session:
        sub = SubscriptionORM(
            user_id=user_id,
            criteria_id=criteria_id,
            is_active=True
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub


async def get_active_subscriptions() -> List[SubscriptionORM]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SubscriptionORM)
            .where(SubscriptionORM.is_active == True)
            .options(
                selectinload(SubscriptionORM.criteria),
                selectinload(SubscriptionORM.user)
            )
        )
        return result.scalars().all()

async def get_subscription_by_id(sub_id: int) -> Optional[SubscriptionORM]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SubscriptionORM).where(SubscriptionORM.id == sub_id)
        )
        return result.scalar_one_or_none()

async def get_subscription_with_criteria(sub_id: int) -> Optional[SubscriptionORM]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SubscriptionORM)
            .where(SubscriptionORM.id == sub_id)
            .options(selectinload(SubscriptionORM.criteria))
        )
        return result.scalar_one_or_none()        

async def update_subscription_notified_at(sub_id: int):
    """Обновляет время последнего уведомления для подписки."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(SubscriptionORM)
            .where(SubscriptionORM.id == sub_id)
            .values(last_notified_at=datetime.now())
        )
        await session.commit()

async def deactivate_subscription(sub_id: int):
    """Отключает подписку."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(SubscriptionORM)
            .where(SubscriptionORM.id == sub_id)
            .values(is_active=False)
        )
        await session.commit()

async def get_last_price(tour_identity: str) -> Optional[int]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PriceHistoryORM.price)
            .where(PriceHistoryORM.tour_identity == tour_identity)
            .order_by(PriceHistoryORM.checked_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def save_price_history(tour_identity: str, price: int):
    async with AsyncSessionLocal() as session:
        history = PriceHistoryORM(
            tour_identity=tour_identity,
            price=price,
            checked_at=datetime.now()
        )
        session.add(history)
        await session.commit()

async def find_subscription_by_user_and_criteria(user_id: int, criteria_id: int) -> Optional[SubscriptionORM]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SubscriptionORM)
            .where(
                SubscriptionORM.user_id == user_id,
                SubscriptionORM.criteria_id == criteria_id
            )
        )
        return result.scalar_one_or_none()


async def deactivate_subscription_by_criteria(user_id: int, criteria_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        sub = await find_subscription_by_user_and_criteria(user_id, criteria_id)
        if not sub:
            return False
        sub.is_active = False
        await session.commit()
        return True


async def deactivate_all_user_subscriptions(user_id: int) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(SubscriptionORM)
            .where(
                SubscriptionORM.user_id == user_id,
                SubscriptionORM.is_active == True
            )
            .values(is_active=False)
        )
        await session.commit()
        return result.rowcount

async def save_feed_tours(tours: List[FeedTour]) -> int:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(FeedTourORM))
            orm_objects = []
            for t in tours:
                orm_obj = FeedTourORM(
                    id=t.id,
                    price=t.price,
                    nights=t.nights,
                    hotel_name=t.hotel_name,
                    hotel_stars=t.hotel_stars,
                    country=t.country,
                    region=t.region,
                    departure_city=t.departure_city,
                    departure_date=t.departure_date,
                    operator_name=t.operator_name,
                    picture_hotel=t.picture_hotel,
                    picture_hotel_800x600=t.picture_hotel_800x600,
                    picture_seo_800x620=t.picture_seo_800x620,
                    hotel_url=t.hotel_url,
                    region_url=t.region_url,
                    country_url=t.country_url,
                    min_country_price_url=t.min_country_price_url,
                    min_region_price_url=t.min_region_price_url,
                    feed_updated_at=datetime.now()
                )
                orm_objects.append(orm_obj)
            session.add_all(orm_objects)
        return len(orm_objects)

async def search_feed_tours(
    departure_city: str,
    country: str,
    date_from: date,
    date_to: date,
    nights_min: int,
    nights_max: int,
    stars: List[int],
    max_price: int,
    limit: int = 20
) -> List[FeedTourORM]:
    async with AsyncSessionLocal() as session:
        query = select(FeedTourORM).where(
            FeedTourORM.departure_city == departure_city,
            FeedTourORM.country == country,
            FeedTourORM.departure_date.between(date_from, date_to),
            FeedTourORM.nights.between(nights_min, nights_max),
            FeedTourORM.hotel_stars.in_(stars) if stars else True,
            FeedTourORM.price <= max_price
        ).order_by(FeedTourORM.price).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

async def update_subscription_price(sub_id: int, price: int):
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(SubscriptionORM)
            .where(SubscriptionORM.id == sub_id)
            .values(last_price=price, last_checked_at=datetime.now())
        )
        await session.commit()