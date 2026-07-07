from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from models import Country, Resort, Hotel, HotelCategory, Meal, DepartureCity, Tour

class ITravelataClient(ABC):
    """Абстрактный интерфейс для клиента API Travelata"""
    
    @abstractmethod
    async def get_countries(self) -> List[Country]:
        """Получить список стран"""
        pass

    @abstractmethod
    async def get_resorts(self, country_id: Optional[int] = None,
                          disabled: Optional[bool] = None,
                          limit: int = 100,
                          offset: int = 0) -> List[Resort]:
        """Получить курорты (города) с возможностью фильтрации по стране"""
        pass

    @abstractmethod
    async def get_hotels(self, resort_ids: Optional[List[int]] = None,
                         disabled: Optional[bool] = None,
                         hotel_id: Optional[int] = None,
                         limit: int = 100,
                         offset: int = 0) -> List[Hotel]:
        """Получить отели"""
        pass

    @abstractmethod
    async def get_hotel_categories(self) -> List[HotelCategory]:
        """Получить категории отелей (звёздность)"""
        pass

    @abstractmethod
    async def get_meals(self) -> List[Meal]:
        """Получить типы питания"""
        pass

    @abstractmethod
    async def get_departure_cities(self) -> List[DepartureCity]:
        """Получить города вылета"""
        pass

    @abstractmethod
    async def get_cheapest_tours(self,
                                 country_ids: List[int],
                                 departure_city: int,
                                 checkin_date_from: date,
                                 checkin_date_to: date,
                                 adults: int = 2,
                                 kids: int = 0,
                                 infants: int = 0,
                                 nights_min: Optional[int] = None,
                                 nights_max: Optional[int] = None,
                                 resorts: Optional[List[int]] = None,
                                 meals: Optional[List[int]] = None,
                                 hotel_categories: Optional[List[int]] = None) -> List[Tour]:
        """Получить список самых дешёвых туров по заданным критериям"""
        pass