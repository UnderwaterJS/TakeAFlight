import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import date

import aiohttp
from aiohttp import ClientTimeout, ClientResponseError

from config import settings
from models import (Country, Tour, Resort, Hotel, Meal, HotelCategory, DepartureCity)
from interfaces import ITravelataClient

logger = logging.getLogger(__name__)


class TravelataAPIClient(ITravelataClient):
    """
    Асинхронный клиент для api Travelata
    """

    def __init__(self,
                 login: str,
                 password: str,
                 base_url: Optional[str] = None,
                 timeout: Optional[int] = None,
                 retry_count: Optional[int] = None
    ):
        self.login = login
        self.password = password
        self.base_url = base_url or settings.travelata_api_url
        self.timeout = timeout or settings.api_request_timeout
        self.retry_count = retry_count or settings.api_retry_count

        self._session: Optional[aiohttp.ClientSession] = None

        self._session = aiohttp.ClientSession(
            timeout=ClientTimeout(total=self.timeout)
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии при выходе из контекста"""
        if self._session:
            await self._session.close()

    # Приватный метод для выполнения запросов
    async def _request(self,
                       endpoint: str,
                       params: Optional[Dict[str, Any]] = None,
                       retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Выполняет GET-запрос к указанному эндпоинту с Basic Auth.
        Возвращает распарсенный JSON (уже извлекая поле 'result').
        При ошибках делает повторные попытки.
        """
        if retries is None:
            retries = self.retry_count
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        params = params or {}

        #Здесь формируется заголовок авторизации
        auth = aiohttp.BasicAuth(self.login, self.password)

        for attempt in range(1, retries + 1):
            try:
                logger.debug(f"Запрос к {url} с параметрами {params}")
                async with self._session.get(url, params=params, auth=auth) as resp:
                    #проверка статуса
                    if resp.status == 429:
                        #Превышен лимит - смотрим заголовок X-RateLimit-Reset
                        reset_after = int(resp.headers.get('X-RateLimit-Reset', 60))
                        logger.warning(f"Превышен лимит запросов. Ждем {reset_after} сек.")
                        await asyncio.sleep(reset_after)
                        continue

                    resp.raise_for_status()

                    data = await resp.json()

                    #Проверка структуры ответа
                    if not data.get('success', False):
                        error_msg = data.get('error', {}).get('message', 'Unknown error')
                        raise RuntimeError(f"API вернул ошибку: {error_msg}")

                    #Извлекаем result (или data для обратной совместимости)
                    result = data.get('result')
                    if result is None:
                        #Если поле result отсутствует, возможно это старая версия
                        result = data.get('data', [])
                    
                    logger.info(f"Ответ от {endpoint}: success={data.get('success')}, count={len(data.get('result', []))}")

                    return result

            except ClientResponseError as e:
                # Обработка специфичных ошибок
                if e.status == 401:
                    raise ValueError("Неверный логин или пароль для API Travelata") from e
                elif e.status == 403:
                    raise  ValueError("Нет доступа к этому эндпоинту. Проверьте права.") from e
                elif e.status == 500:
                    logger.error(f"Внутренняя ошибка сервера (500) при запросе {url}")
                    if attempt < retries:
                        await asyncio.sleep(2 ** attempt) #эспоненцильная задержка
                        continue
                else:
                    logger.error(f"HTTP ошибка {e.status} при запросе {url}: {e}")
                    raise

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Сетевая ошибка при запросе {url}: {e}. Попытка {attempt}/{retries}")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise ConnectionError(f"Не удалось выполнить запрос после {retries} попыток") from e

        # Если все попытки исчерпаны, но мы не вышли через return/raise
        raise RuntimeError("Неизвестная ошибка при выполнении запроса")

    # Публичные методы для работы со справочниками

    async def get_countries(self) -> List[Country]:
        data = await self._request("partners/directory/countries")
        return [Country(**item) for item in data]

    async def get_resorts(self,
                          country_id: Optional[int] = None,
                          disabled: Optional[bool] = None,
                          limit: int = 100,
                          offset: int = 0
                          ) -> List[Resort]:
        params = {}
        if country_id is not None:
            params['country[]'] = country_id
        if disabled is not None:
            params['disabled'] = 1 if disabled else 0
        params['limit'] = limit
        params['offset'] = offset

        data = await self._request("partners/directory/resorts", params=params)
        return [Resort(**item) for item in data]

    async def get_hotels(self,
                         resort_ids: Optional[List[int]] = None,
                         disabled: Optional[bool] = None,
                         hotel_id: Optional[int] = None,
                         limit: int = 100,
                         offset: int = 0
                         ) -> List[Hotel]:
        params = {}
        if resort_ids:
            # API ожидает параметр resort[]=id1&resort[]=id2
            for rid in resort_ids:
                params.setdefault('resort[]', []).append(rid)
        if disabled is not None:
            params['disabled'] = 1 if disabled else 0
        params['limit'] = limit
        params['offset'] = offset

        data = await self._request("partners/directory/hotels", params=params)
        return [Hotel(**item) for item in data]

    async def get_hotel_categories(self) -> List[HotelCategory]:
        data = await self._request("partners/directory/hotelCategories")
        return [HotelCategory(**item) for item in data]

    async def get_meals(self) -> List[Meal]:
        data = await self._request("partners/directory/meals")
        return [Meal(**item) for item in data]

    async def get_departure_cities(self) -> List[DepartureCity]:
        data = await self._request("partners/directory/departureCities")
        return [DepartureCity(**item) for item in data]

    # Главный метод поиска туров по заданным критериям
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
                             hotel_categories: Optional[List[int]] = None
                             ) -> List[Tour]:
        params = {
            'departureCity': departure_city,
            'touristGroup[adults]': adults,
            'touristGroup[kids]': kids,
            'touristGroup[infants]': infants,
            'checkInDateRange[from]': checkin_date_from.isoformat(),
            'checkInDateRange[to]': checkin_date_to.isoformat(),
        }

        if country_ids:
            for cid in country_ids:
                params.setdefault('countries[]', []).append(cid)

        params = {k: v for k, v in params.items() if v is not None}

        if nights_min is not None:
            params['nightRange[from]'] = nights_min
        if nights_max is not None:
            params['nightRange[to]'] = nights_max

        if resorts:
            for rid in resorts:
                params.setdefault('resorts[]', []).append(rid)
        if meals:
            for mid in meals:
                params.setdefault('meals[]', []).append(mid)
        if hotel_categories:
            for hc in hotel_categories:
                params.setdefault('hotelCategories[]', []).append(hc)

        logger.info(f"Запрос к cheapestTours с параметрами: {params}")

        data = await self._request("partners/statistic/cheapestTours", params=params)
        return [Tour(**item) for item in data]
