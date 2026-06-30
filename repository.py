import logging
from datetime import datetime
from symtable import Class
from typing import Optional, List

from TakeAFlight.models import SearchCriteria
from sqlalchemy import (Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text, JSON)
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

    subscriptions = relationship("SubscriptionORM", back_populates="user", cascade="all, delete=orphan")

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

    user = relationship("UserORM", back_populates="subscriptions")
    criteria = relationship("SearchCriteriaORM", back_populates="subscriptions")

class PriceHistoryORM(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    tour_identity = Column(String, nullable=False, index=True)
    price = Column(Integer, nullable=False)
    checked_at = Column(DateTime, default=datetime.now, index=True)


engine = create_async_engine(
    settings.database_url,
    echo=False,
    expire_on_commit=True
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
                      last_name: str = None) -> UserORM
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