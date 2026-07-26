import aiohttp
import yaml
import logging
from datetime import datetime
from typing import List
from models import FeedTour
from repository import save_feed_tours
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

FEED_URLS = [
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_moscow.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_spb.yml",
    "https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_kazan.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_ekb.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_ufa.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_perm.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_tyumen.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_samara.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_irkutsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_omsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_novosibirsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_surgut.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_nizhnekamsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_krasnoyarsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_vladivostok.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_mineralnye_vody.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_sochi.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_nizhny_novgorod.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_chelyabinsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_kaliningrad.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_syktyvkar.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_orenburg.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_khabarovsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_nizhnevartovsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_volgograd.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_saratov.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_magnitogorsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_arkhangelsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_makhachkala.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_astrakhan.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_cheboksary.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_kemerovo.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_ulyanovsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_barnaul.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_murmansk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_novokuznetsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_abakan.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_orsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_tomsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_yuzhno-sakhalinsk.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_chita.yml",
    #"https://storage.yandexcloud.net/lt-analytics/offer_feed/hotel_feed_blagoveshchensk.yml",
]

async def load_single_feed(url: str, session: aiohttp.ClientSession) -> List[FeedTour]:
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            raw_data = await response.text()
            root = ET.fromstring(raw_data)   # парсим XML
            shop = root.find('shop')
            if shop is None:
                logger.error(f"Нет shop в {url}")
                return []
            offers = shop.find('offers')
            if offers is None:
                logger.warning(f"Нет offers в {url}")
                return []
            tours = []
            for offer in offers.findall('offer'):
                try:
                    offer_id = offer.get('id', '')
                    if not offer_id:
                        continue
                    def get_text(tag, default=''):
                        elem = offer.find(tag)
                        return elem.text if elem is not None else default

                    price = int(get_text('price', '0'))
                    adults = int(get_text('adults', '2'))
                    nights = int(get_text('days', '7'))
                    hotel_name = get_text('name')
                    stars_raw = get_text('hotel_stars')
                    stars = 0
                    if stars_raw and stars_raw.isdigit():
                        stars = int(stars_raw)
                    country = get_text('country')
                    region = get_text('region')
                    departure_city = get_text('departure_city')
                    departure_date_str = get_text('tour_date')
                    if not departure_date_str:
                        continue
                    departure_date = datetime.strptime(departure_date_str, '%Y-%m-%d').date()
                    operator_name = get_text('operator_name')
                    picture_hotel = get_text('picture_hotel')
                    hotel_url = get_text('hotel-url')
                    region_url = get_text('region-url')
                    country_url = get_text('country-url')
                    min_country_price_url = get_text('min_country_price_url')
                    min_region_price_url = get_text('min_region_price_url')

                    tour = FeedTour(
                        id=offer_id,
                        price=price,
                        nights=nights,
                        hotel_name=hotel_name,
                        hotel_stars=stars,
                        country=country,
                        region=region,
                        departure_city=departure_city,
                        departure_date=departure_date,
                        operator_name=operator_name,
                        picture_hotel=picture_hotel,
                        picture_hotel_800x600=get_text('picture_hotel_800x600'),
                        picture_seo_800x620=get_text('picture_seo_800x620'),
                        hotel_url=hotel_url,
                        region_url=region_url,
                        country_url=country_url,
                        min_country_price_url=min_country_price_url,
                        min_region_price_url=min_region_price_url,
                    )
                    tours.append(tour)
                except Exception as e:
                    logger.error(f"Ошибка парсинга оффера {offer.get('id')}: {e}")
                    continue
            logger.info(f"Загружено {len(tours)} туров из {url}")
            return tours
    except ET.ParseError as e:
        logger.error(f"Ошибка парсинга XML в {url}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Ошибка при загрузке фида {url}: {e}")
        return []

async def refresh_all_feeds():
    logger.info("Начинается обновление фидов Level.Travel")
    all_tours = []
    async with aiohttp.ClientSession() as session:
        for url in FEED_URLS:
            tours = await load_single_feed(url, session)
            all_tours.extend(tours)

    if not all_tours:
        logger.warning("Не загружено ни одного тура, обновление отменено")
        return

    seen_ids = set()
    unique_tours = []
    for t in all_tours:
        if t.id not in seen_ids:
            seen_ids.add(t.id)
            unique_tours.append(t)

    duplicates_count = len(all_tours) - len(unique_tours)
    if duplicates_count:
        logger.info(f"Найдено дубликатов: {duplicates_count}, удалено")
    all_tours = unique_tours
    logger.info(f"Всего уникальных туров для сохранения: {len(all_tours)}")

    try:
        count = await save_feed_tours(all_tours)
        logger.info(f"Сохранено {count} туров в БД")
    except Exception as e:
        logger.exception("Ошибка сохранения туров в БД")
        raise