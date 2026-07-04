import logging
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from handlers.states import SearchStates
from models import SearchCriteria, Tour
from travelata_api import TravelataAPIClient
from search_engine import filter_by_match_threshold
from repository import create_search_criteria
from datetime import datetime, date
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

router = Router()

_travelata_client: Optional[TravelataAPIClient] = None

def set_travelata_client(client: TravelataAPIClient):
    global _travelata_client
    _travelata_client = client

def parse_date(text: str) -> date | None:
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None

def validate_positive_int(text: str, max_value: int = 10) -> int | None:
    try:
        val = int(text.strip())
        if 0 <= val <= max_value:
            return val
    except ValueError:
        pass
    return None

@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔍 Давайте найдём идеальный тур!\n"
        "Сначала укажите ID страны.\n"
        "(Можно получить список стран через /countries, но пока введите ID, например 92 для Турции)"
    )
    await state.set_state(SearchStates.waiting_for_country)

@router.message(StateFilter(SearchStates.waiting_for_country))
async def process_country(message: Message, state: FSMContext):
    try:
        country_id = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите числовой ID страны.")
        return
    await state.update_data(country_id=country_id)
    await message.answer("Теперь укажите ID города вылета (например, 2 – Москва).")
    await state.set_state(SearchStates.waiting_for_departure_city)

@router.message(StateFilter(SearchStates.waiting_for_departure_city))
async def process_departure_city(message: Message, state: FSMContext):
    try:
        departure_city = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите число ID города.")
        return
    await state.update_data(departure_city=departure_city)
    await message.answer("Введите дату заезда в формате ГГГГ-ММ-ДД (например, 2026-07-01).")
    await state.set_state(SearchStates.waiting_for_checkin_date)

@router.message(StateFilter(SearchStates.waiting_for_checkin_date))
async def process_checkin(message: Message, state: FSMContext):
    checkin = parse_date(message.text)
    if checkin is None:
        await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД.")
        return
    await state.update_data(checkin_date=checkin)
    await message.answer("Введите дату выезда (ГГГГ-ММ-ДД) или нажмите /skip, чтобы указать количество ночей вручную.")
    await state.set_state(SearchStates.waiting_for_checkout_date)

@router.message(StateFilter(SearchStates.waiting_for_checkout_date))
async def process_checkout(message: Message, state: FSMContext):
    checkout = parse_date(message.text)
    if checkout is None:
        await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД или /skip.")
        return
    await state.update_data(checkout_date=checkout)
    data = await state.get_data()
    checkin = data['checkin_date']
    if checkin and checkout:
        nights = (checkout - checkin).days
        if nights <= 0:
            await message.answer("Дата выезда должна быть позже даты заезда.")
            return
        await state.update_data(nights_min=nights, nights_max=nights)
        await message.answer(f"Количество ночей: {nights}. Теперь укажите количество взрослых.")
        await state.set_state(SearchStates.waiting_for_adults)
    else:
        await message.answer("Что-то пошло не так, попробуйте заново.")

@router.message(StateFilter(SearchStates.waiting_for_nights))
async def process_nights(message: Message, state: FSMContext):
    text = message.text.strip()
    nights_min = nights_max = None
    if "-" in text:
        parts = text.split("-")
        if len(parts) == 2:
            try:
                nights_min = int(parts[0].strip())
                nights_max = int(parts[1].strip())
            except ValueError:
                pass
    else:
        try:
            nights_min = nights_max = int(text)
        except ValueError:
            pass
    if nights_min is None:
        await message.answer("Пожалуйста, введите число или диапазон (например, 5-7).")
        return
    await state.update_data(nights_min=nights_min, nights_max=nights_max)
    await message.answer("Сколько взрослых (по умолчанию 2)? Введите число или пропустите (нажмите /skip).")
    await state.set_state(SearchStates.waiting_for_adults)

@router.message(StateFilter(SearchStates.waiting_for_adults))
async def process_adults(message: Message, state: FSMContext):
    val = validate_positive_int(message.text, max_value=10)
    if val is None or val == 0:
        await message.answer("❗Введите число от 1 до 10")
        return
    await state.update_data(adults=val)
    await message.answer("Сколько детей (до 12 лет)? (0, если нет)")
    await state.set_state(SearchStates.waiting_for_kids)

@router.message(StateFilter(SearchStates.waiting_for_kids))
async def process_kids(message: Message, state: FSMContext):
    val = validate_positive_int(message.text, max_value=10)
    if val is None:
        await message.answer("❗Введите число от 0 до 10")
        return
    await state.update_data(kids=val)
    await message.answer("Сколько младенцев (дети до 2 лет)? (0, если нет)")
    await state.set_state(SearchStates.waiting_for_infants)

@router.message(StateFilter(SearchStates.waiting_for_infants))
async def process_infants(message: Message, state: FSMContext):
    val = validate_positive_int(message.text, max_value=5)
    if val is None:
        await message.answer("❗Введите число от 0 до 5")
        return
    await state.update_data(infants=val)
    await message.answer("Сколько звезд должно быть у отеля? (Числа от 1-5, можно диапазоном и через запятую)")
    await state.set_state(SearchStates.waiting_for_hotel_categories)

@router.message(StateFilter(SearchStates.waiting_for_hotel_categories))
async def process_hotel_categories(message: Message, state: FSMContext):
    raw = message.text.strip()
    categories = []
    if '-' in raw:
        parts = raw.split('-')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start, end = int(parts[0]), int(parts[1])
            categories = list(range(min(start,end), max(start,end)+1))
    else:
        for token in raw.replace(',', ' ').split():
            if token.isdigit():
                categories.append(int(token))
    categories = sorted(set(c for c in categories if 1 <= c <= 5))
    if not categories:
        await message.answer("❗ Укажите количество звезд через запятую или диапазон, например: 4,5 или 3-5")
        return
    await state.update_data(hotel_categories=categories)
    await message.answer("Введите максимальную цену за тур (в рублях, например 100000)")
    await state.set_state(SearchStates.waiting_for_max_price)

@router.message(SearchStates.waiting_for_max_price)
async def process_max_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price > 0:
            await state.update_data(max_price=price)
            data = await state.get_data()
            await show_confirmation(message, data)
            await state.set_state(SearchStates.waiting_for_confirmation)
            return
    except ValueError:
        pass
    await message.answer("❗ Введите целое положительное число (рубли)")

# Пропуск (для опциональных полей)
@router.message(Command("skip"))
async def cmd_skip(message: Message, state: FSMContext):
    # Текущее состояние определяет, что пропускаем
    current_state = await state.get_state()
    if current_state == SearchStates.waiting_for_adults.state:
        await state.update_data(adults=2)
        await message.answer("Принято (2 взрослых). Теперь укажите количество детей (0 по умолчанию) или /skip.")
        await state.set_state(SearchStates.waiting_for_kids)
    elif current_state == SearchStates.waiting_for_checkout_date.state:
        await message.answer("Хорошо, укажите количество ночей вручную (число или диапазон).")
        await state.set_state(SearchStates.waiting_for_nights)
    elif current_state == SearchStates.waiting_for_kids.state:
        await state.update_data(kids=0)
        await message.answer("Принято (0 детей). Теперь укажите количество младенцев (0) или /skip.")
        await state.set_state(SearchStates.waiting_for_infants)
    elif current_state == SearchStates.waiting_for_infants.state:
        await state.update_data(infants=0)
        await message.answer("Принято. Теперь введите категории отелей (звёзды) через запятую, например 5,4 или /skip.")
        await state.set_state(SearchStates.waiting_for_hotel_categories)
    elif current_state == SearchStates.waiting_for_hotel_categories.state:
        await state.update_data(hotel_categories=[])
        await message.answer("Принято. Введите максимальную цену в рублях или /skip.")
        await state.set_state(SearchStates.waiting_for_max_price)
    elif current_state == SearchStates.waiting_for_max_price.state:
        await state.update_data(max_price=None)
        data = await state.get_data()
        await show_confirmation(message, data)
        await state.set_state(SearchStates.waiting_for_confirmation)
    else:
        await message.answer("Пропуск недоступен на этом шаге.")

_countries_cache: Dict[int, str] = {}
_cities_cache: Dict[int, str] = {}

async def _load_caches(client: TravelataAPIClient):
    global _countries_cache, _cities_cache
    if not _countries_cache:
        countries = await client.get_countries()
        _countries_cache = {c.id: c.name for c in countries}
    if not _cities_cache:
        cities = await client.get_departure_cities()
        _cities_cache = {c.id: c.name for c in cities}

async def show_confirmation(message: Message, data: dict):
    client = _travelata_client
    if client:
        await _load_caches(client)

    country_id = data.get('country_id')
    city_id = data.get('departure_city')
    checkin = data.get('checkin_date')
    checkout = data.get('checkout_date')
    nights_min = data.get('nights_min')
    nights_max = data.get('nights_max')
    categories = data.get('hotel_categories', [])
    adults = data.get('adults', 1)
    kids = data.get('kids', 0)
    infants = data.get('infants', 0)
    max_price = data.get('max_price')

    country_name = _countries_cache.get(country_id, str(country_id) if country_id else 'не указана')
    city_name = _cities_cache.get(city_id, str(city_id) if city_id else 'не указан')

    if categories:
        categories_str = ', '.join(f"{c}★" for c in categories)
    else:
        categories_str = 'любые'

    if nights_min is not None and nights_max is not None:
        if nights_min == nights_max:
            nights_str = str(nights_min)
        else:
            nights_str = f"{nights_min}-{nights_max}"
    else:
        nights_str = "не указано"

    from datetime import timedelta
    if checkin and checkout:
        checkout_str = checkout.strftime("%Y-%m-%d")
    elif checkin and nights_min is not None:
        checkout_calc = checkin + timedelta(days=nights_min)
        if nights_max is not None and nights_max != nights_min:
            checkout_calc2 = checkin + timedelta(days=nights_max)
            checkout_str = f"{checkout_calc.strftime('%Y-%m-%d')} – {checkout_calc2.strftime('%Y-%m-%d')}"
        else:
            checkout_str = checkout_calc.strftime("%Y-%m-%d")
    else:
        checkout_str = "не указана"

    text = (
        "📋 Проверьте параметры:\n"
        f"Страна: {country_name}\n"
        f"Город вылета: {city_name}\n"
        f"Заезд: {checkin.strftime('%Y-%m-%d') if checkin else 'не указан'}\n"
        f"Выезд (ориентир): {checkout_str}\n"
        f"Ночей: {nights_str}\n"
        f"Взрослых: {adults}\n"
        f"Детей: {kids}\n"
        f"Младенцев: {infants}\n"
        f"Категории отелей: {categories_str}\n"
        f"Макс. цена: {max_price if max_price else 'не указана'} руб.\n"
        "\nНажмите «Искать» для поиска туров."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Искать", callback_data="search_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="search_cancel")]
    ])
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "search_confirm", StateFilter(SearchStates.waiting_for_confirmation))
async def confirm_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Ищем...")
    data = await state.get_data()

    criteria = SearchCriteria(
        user_id=callback.from_user.id,
        country_id=data.get('country_id'),
        departure_city_id=data['departure_city'],
        checkin_date_from=data['checkin_date'],
        checkin_date_to=data['checkin_date'],
        nights_min=data.get('nights_min'),
        nights_max=data.get('nights_max'),
        adults=data.get('adults', 2),
        kids=data.get('kids', 0),
        infants=data.get('infants', 0),
        hotel_categories=data.get('hotel_categories', []),
        max_price=data.get('max_price')
    )

    client = _travelata_client
    if client is None:
        await callback.message.edit_text("❌ Ошибка: клиент API не инициализирован. Попробуйте позже.")
        await state.clear()
        return
    
    try:
        tours = await client.get_cheapest_tours(
            country_ids=[criteria.country_id] if criteria.country_id else [],
            departure_city=criteria.departure_city_id,
            checkin_date_from=criteria.checkin_date_from,
            checkin_date_to=criteria.checkin_date_from,
            adults=criteria.adults,
            kids=criteria.kids,
            infants=criteria.infants,
            nights_min=criteria.nights_min,
            nights_max=criteria.nights_max,
            hotel_categories=criteria.hotel_categories if criteria.hotel_categories else None,
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при поиске: {e}")
        await state.clear()
        return
    
    if criteria.max_price is not None:
        tours = [t for t in tours if t.price <= criteria.max_price]

    if not tours:
        await callback.message.edit_text("По вашему запросу туров не найдено.\n"
            "Попробуйте изменить критерии (например, расширить даты или увеличить бюджет).")
        await state.clear()
        return
    
    grouped = filter_by_match_threshold(tours, criteria)

    try:
        saved_criteria = await create_search_criteria(criteria)
        criteria_id = saved_criteria.id
    except Exception as e:
        logger.error(f"Не удалось сохранить критерии: {e}")
        criteria_id = None
    
    text, keyboard = format_tours_message(grouped, criteria_id, criteria)
    if keyboard:
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text)

    await state.clear()

def format_tours_message(grouped: Dict[int, List[Tour]], criteria_id: Optional[int], criteria: SearchCriteria) -> tuple[str, Optional[InlineKeyboardMarkup]]:
    text = "🔍 Найденные туры:\n\n"
    buttons = []
    tour_counter = 0
    
    # Порядок отображения: 100% → 80% → 60%
    for match_percent in [100, 80, 60]:
        tours_in_group = grouped.get(match_percent, [])
        if not tours_in_group:
            continue
        text += f"✅ {match_percent}% совпадение:\n"
        # Показываем первые 5 из группы (можно сделать больше/меньше)
        for tour in tours_in_group[:5]:
            tour_counter += 1
            # Формируем строку отеля
            hotel_info = f"🏨 {tour.hotelName}" if tour.hotelName else "🏨 Отель без названия"
            stars = f"⭐ {tour.hotelCategoryName}" if tour.hotelCategoryName else f"⭐ {tour.hotelCategory}*"
            text += (
                f"{hotel_info}\n"
                f"{stars}\n"
                f"💰 {tour.price} руб.\n"
                f"🌙 {tour.nights} ночей\n"
                f"📅 Заезд: {tour.checkinDate}\n"
                f"🔗 [Подробнее]({tour.tourPageUrl})\n"
                "---\n"
            )
            # Кнопка подписки на этот тур (используем tourIdentity)
            buttons.append([
                InlineKeyboardButton(
                    text=f"🔔 Подписаться на тур #{tour_counter}",
                    callback_data=f"subscribe_tour_{tour.tourIdentity}"
                )
            ])
    
    if tour_counter == 0:
        return "😔 Не найдено туров, удовлетворяющих критериям.", None
    
    # Кнопка подписки на критерии (если удалось сохранить)
    if criteria_id:
        buttons.append([
            InlineKeyboardButton(
                text="🔔 Подписаться на эти критерии",
                callback_data=f"subscribe_criteria_{criteria_id}"
            )
        ])
    else:
        # Если не сохранили, всё равно предложим (но без id) – можно сохранить позже
        pass
    
    # Дополнительная кнопка "Показать ещё" (пагинация) – позже реализуем
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    return text, keyboard

@router.callback_query(F.data == "search_cancel", StateFilter(SearchStates.waiting_for_confirmation))
async def cancel_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Поиск отменён.")
    await callback.message.edit_text("Поиск отменён. Если захотите снова – /search")
    await state.clear()

# Команда отмены
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.")