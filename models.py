from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

class Tour(BaseModel):
    tourIdentity: str
    price: int
    publishedAt: datetime
    checkinDate: date
    nights: int
    hotelId: int
    mealId: int
    expired: datetime
    operatorId: int
    resortId: int
    tourPageUrl: str
    searchPageUrl: str
    hotelName: str
    hotelCategory: int
    hotelCategoryName: str
    hotelRating: Optional[float]
    hotelPreview: Optional[str]

class User(BaseModel):
    id: Optional[int] = None
    telegramId: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    registerAt: datetime = datetime.now()
    is_active: bool = True

class SearchCriteria(BaseModel):
    id: Optional[int] = None
    user_id: int
    country_id: Optional[int] = None
    departure_city_id: int  # обязательный
    checkin_date_from: date
    checkin_date_to: date
    nights_min: Optional[int] = None
    nights_max: Optional[int] = None
    adults: int = 2
    kids: int = 0
    infants: int = 0
    hotel_categories: List[int] = []  # список ID категорий
    resorts: List[int] = []  # список ID курортов
    max_price: Optional[int] = None
    created_at: datetime = datetime.now()

class Subscription(BaseModel):
    id: Optional[int] = None
    user_id: int
    criteria_id: int                   # ссылка на SearchCriteria
    is_active: bool = True
    last_notified_at: Optional[datetime] = None
    created_at: datetime = datetime.now()

class PriceHistory(BaseModel):
    id: Optional[int] = None
    tour_identity: str
    price: int
    checked_at: datetime = datetime.now()

class Country(BaseModel):
    id: int
    name: str
    disabled: bool

class Resort(BaseModel):
    id: int
    name: str
    country: int
    isPopular: bool
    disabled: bool

class Hotel(BaseModel):
    id: int
    name: str
    resort: int
    country: int
    hotelCategory: int
    coords: Optional[dict]  # можно уточнить структуру
    attributes: List[int]
    rating: Optional[float]
    beachLine: Optional[int]
    distances: Optional[dict]  # airport, beach, beachMax, lift, center
    disabled: bool

class Meal(BaseModel):
    id: int
    code: str
    name: str

class HotelCategory(BaseModel):
    id: int
    name: str  # например "5*"

class DepartureCity(BaseModel):
    id: int
    name: str
    disabled: bool