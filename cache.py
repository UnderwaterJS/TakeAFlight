import logging
from typing import Dict, List, Optional
from models import Country, DepartureCity

logger = logging.getLogger(__name__)

class DirectoryCache:
    """Кеш справочников (страны, города вылета и др.)"""
    def __init__(self):
        self.countries: Dict[int, Country] = {}
        self.country_name_to_id: Dict[str, int] = {}
        self.departure_cities: Dict[int, DepartureCity] = {}
        self.departure_city_name_to_id: Dict[str, int] = {}
        self._loaded = False

    async def load(self, client):
        """Загружает справочники из API"""
        if self._loaded:
            return
        try:
            countries = await client.get_countries()
            for c in countries:
                self.countries[c.id] = c
                self.country_name_to_id[c.name.lower()] = c.id
            logger.info(f"Загружено {len(countries)} стран")

            cities = await client.get_departure_cities()
            for c in cities:
                self.departure_cities[c.id] = c
                self.departure_city_name_to_id[c.name.lower()] = c.id
            logger.info(f"Загружено {len(cities)} городов вылета")

            self._loaded = True
        except Exception as e:
            logger.exception("Ошибка загрузки справочников")
            raise

    def get_country_id(self, name: str) -> Optional[int]:
        return self.country_name_to_id.get(name.lower())

    def get_country_name(self, country_id: int) -> str:
        c = self.countries.get(country_id)
        return c.name if c else str(country_id)

    def get_departure_city_id(self, name: str) -> Optional[int]:
        return self.departure_city_name_to_id.get(name.lower())

    def get_departure_city_name(self, city_id: int) -> str:
        c = self.departure_cities.get(city_id)
        return c.name if c else str(city_id)

# Глобальный экземпляр
cache = DirectoryCache()