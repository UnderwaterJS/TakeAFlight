import random
from datetime import date, datetime, timedelta
from typing import List, Optional
from interfaces import ITravelataClient
from models import Country, Resort, Hotel, HotelCategory, Meal, DepartureCity, Tour

class MockTravelataClient(ITravelataClient):
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.countries = [
            Country(id=1, name="Турция", disabled=False),
            Country(id=2, name="Египет", disabled=False),
            Country(id=3, name="ОАЭ", disabled=False),
        ]
        self.resorts = {
            1: [Resort(id=11, name="Анталья", country=1, isPopular=True, disabled=False),
                Resort(id=12, name="Стамбул", country=1, isPopular=False, disabled=False)],
            2: [Resort(id=21, name="Хургада", country=2, isPopular=True, disabled=False),
                Resort(id=22, name="Шарм-эль-Шейх", country=2, isPopular=True, disabled=False)],
            3: [Resort(id=31, name="Дубай", country=3, isPopular=True, disabled=False),
                Resort(id=32, name="Абу-Даби", country=3, isPopular=False, disabled=False)],
        }
        self.hotels = {
            11: [Hotel(id=111, name="Sunny Hotel", resort=11, country=1, hotelCategory=4,
                       coords=None, attributes=[], rating=4.2, beachLine=0, distances=None, disabled=False),
                 Hotel(id=112, name="Sea View", resort=11, country=1, hotelCategory=3,
                       coords=None, attributes=[], rating=3.8, beachLine=0, distances=None, disabled=False)],
            12: [Hotel(id=121, name="Istanbul Palace", resort=12, country=1, hotelCategory=5,
                       coords=None, attributes=[], rating=4.9, beachLine=0, distances=None, disabled=False)],
            21: [Hotel(id=211, name="Coral Beach", resort=21, country=2, hotelCategory=4,
                       coords=None, attributes=[], rating=4.5, beachLine=0, distances=None, disabled=False)],
            22: [Hotel(id=221, name="Sinai Star", resort=22, country=2, hotelCategory=5,
                       coords=None, attributes=[], rating=4.7, beachLine=0, distances=None, disabled=False)],
            31: [Hotel(id=311, name="Burj Al Arab", resort=31, country=3, hotelCategory=5,
                       coords=None, attributes=[], rating=4.9, beachLine=0, distances=None, disabled=False)],
            32: [Hotel(id=321, name="Grand Mosque", resort=32, country=3, hotelCategory=4,
                       coords=None, attributes=[], rating=4.3, beachLine=0, distances=None, disabled=False)],
        }
        self.hotel_categories = [
            HotelCategory(id=1, name="2 звезды"),
            HotelCategory(id=2, name="3 звезды"),
            HotelCategory(id=3, name="4 звезды"),
            HotelCategory(id=4, name="5 звезд"),
        ]
        self.meals = [
            Meal(id=1, code="RO", name="Без питания"),
            Meal(id=2, code="BB", name="Завтрак"),
            Meal(id=3, code="HB", name="Полупансион"),
            Meal(id=4, code="FB", name="Полный пансион"),
            Meal(id=5, code="AI", name="Все включено"),
        ]
        self.departure_cities = [
            DepartureCity(id=1, name="Москва", disabled=False),
            DepartureCity(id=2, name="Санкт-Петербург", disabled=False),
            DepartureCity(id=3, name="Екатеринбург", disabled=False),
            DepartureCity(id=4, name="Казань", disabled=False),
        ]

    # Остальные методы (get_countries, get_resorts и т.д.) оставляем без изменений
    # ...

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
        # Генерируем от 5 до 15 туров, чтобы всегда был результат
        count = random.randint(5, 15)
        tours = []

        # Определяем страну из переданных country_ids
        if country_ids:
            possible = [c for c in self.countries if c.id in country_ids]
            country = random.choice(possible) if possible else random.choice(self.countries)
        else:
            country = random.choice(self.countries)

        # Получаем курорты для этой страны
        resorts_for_country = self.resorts.get(country.id, [])
        if not resorts_for_country:
            # Если нет курортов, создаём фиктивный
            resort = Resort(id=999, name="Фиктивный курорт", country=country.id, isPopular=False, disabled=False)
        else:
            resort = random.choice(resorts_for_country)

        # Отели для курорта
        hotel_list = self.hotels.get(resort.id, [])
        if not hotel_list:
            hotel = Hotel(id=9999, name="Фиктивный отель", resort=resort.id, country=country.id,
                          hotelCategory=4, coords=None, attributes=[], rating=4.0,
                          beachLine=0, distances=None, disabled=False)
        else:
            hotel = random.choice(hotel_list)

        # Определяем допустимые звёзды
        if hotel_categories:
            possible_stars = hotel_categories
        else:
            possible_stars = [2, 3, 4, 5]

        for i in range(count):
            # Цена от 30k до 200k
            price = random.randint(30000, 200000)
            # Старая цена может быть выше
            old_price = price + random.randint(0, 30000)
            # Количество ночей
            if nights_min is not None and nights_max is not None:
                nights = random.randint(nights_min, nights_max)
            elif nights_min is not None:
                nights = random.randint(nights_min, nights_min + 5)
            elif nights_max is not None:
                nights = random.randint(max(1, nights_max - 5), nights_max)
            else:
                nights = random.randint(5, 14)

            departure_date = checkin_date_from + timedelta(days=random.randint(0, 5))
            # Убедимся, что выезд не раньше заезда
            if departure_date > checkin_date_to:
                departure_date = checkin_date_from

            stars = random.choice(possible_stars)

            tour = Tour(
                tourIdentity=f"mock_{i}_{int(datetime.now().timestamp())}",
                price=price,
                publishedAt=datetime.now(),
                checkinDate=departure_date,
                nights=nights,
                hotelId=hotel.id,
                mealId=random.choice([m.id for m in self.meals]) if meals is None else random.choice(meals),
                expired=datetime.now() + timedelta(days=30),
                operatorId=random.randint(1, 5),
                resortId=resort.id,
                tourPageUrl=f"https://example.com/tour/mock_{i}",
                searchPageUrl=f"https://example.com/search?mock={i}",
                hotelName=hotel.name,
                hotelCategory=stars,
                hotelCategoryName=f"{stars}★",
                hotelRating=random.uniform(3.0, 5.0),
                hotelPreview=None
            )
            tours.append(tour)

        return tours