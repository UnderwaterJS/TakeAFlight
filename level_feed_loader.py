import aiohttp
import yaml
import logging
from datetime import datetime
from typing import List
from models import FeedTour
from repository import save_feed_tours

logger = logging.getLogger(__name__)

FEED_URLS = [
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_moscow.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_spb.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_kazan.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_ekb.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_ufa.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_perm.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_tyumen.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_samara.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_irkutsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_omsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_novosibirsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_surgut.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_nizhnekamsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_krasnoyarsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_vladivostok.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_mineralnye_vody.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_sochi.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_nizhny_novgorod.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_chelyabinsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_kaliningrad.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_syktyvkar.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_orenburg.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_khabarovsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_nizhnevartovsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_volgograd.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_saratov.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_magnitogorsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_arkhangelsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_makhachkala.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_astrakhan.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_cheboksary.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_kemerovo.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_ulyanovsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_barnaul.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_murmansk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_novokuznetsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_abakan.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_orsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_tomsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_yuzhno-sakhalinsk.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_chita.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_blagoveshchensk.yml",
]

def extract_city_from_url(url: str) -> str:
    """Извлекает название города из URL (латиница)."""
    filename = url.split('/')[-1]
    city = filename.replace('hotel_feed_', '').replace('.yml', '')
    return city

async def load_single_feed(url: str, session: aiohttp.ClientSession) -> List[FeedTour]:
    """Загружает один YAML-файл и парсит его в список FeedTour."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            raw_data = await response.text()
            data = yaml.safe_load(raw_data)
            if not isinstance(data, list):
                logger.error(f"Неожиданный формат данных в {url}: ожидался список")
                return []
            city = extract_city_from_url(url)
            tours = []
            for item in data:
                tour = FeedTour(
                    id=item.get('id') or item.get('tour_id', ''),
                    departure_city=city,
                    country=item.get('country') or item.get('country_name', ''),
                    resort=item.get('resort') or item.get('city') or item.get('region', ''),
                    hotel_name=item.get('hotel_name') or item.get('hotel', ''),
                    stars=int(item.get('stars', 0)),
                    price=int(item.get('price', 0)),
                    departure_date=datetime.strptime(item.get('departure_date') or item.get('date', '1970-01-01'), '%Y-%m-%d').date(),
                    nights=int(item.get('nights', 0)),
                    operator=item.get('operator') or item.get('tour_operator', ''),
                    hotel_preview=item.get('hotel_preview') or item.get('hotel_image', ''),
                    resort_preview=item.get('resort_preview') or item.get('resort_image', ''),
                    url_country=item.get('url_country') or item.get('country_url', ''),
                    url_resort=item.get('url_resort') or item.get('resort_url', ''),
                    url_hotel=item.get('url_hotel') or item.get('hotel_url', ''),
                )
                tours.append(tour)
            return tours
    except Exception as e:
        logger.exception(f"Ошибка при загрузке фида {url}: {e}")
        return []

async def refresh_all_feeds():
    """Загружает все фиды и сохраняет их в БД."""
    logger.info("Начинается обновление фидов Level.Travel")
    all_tours = []
    async with aiohttp.ClientSession() as session:
        for url in FEED_URLS:
            tours = await load_single_feed(url, session)
            all_tours.extend(tours)
            logger.info(f"Загружено {len(tours)} туров из {url}")
    if all_tours:
        count = await save_feed_tours(all_tours)
        logger.info(f"Сохранено {count} туров в БД")
    else:
        logger.warning("Не загружено ни одного тура, обновление отменено")