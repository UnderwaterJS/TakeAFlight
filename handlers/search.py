from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from handlers.states import SearchStates
from models import SearchCriteria
from datetime import datetime, date

router = Router()

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
    await message.answer("Введите дату выезда (ГГГГ-ММ-ДД).")
    await state.set_state(SearchStates.waiting_for_checkout_date)

@router.message(StateFilter(SearchStates.waiting_for_checkout_date))
async def process_checkout(message: Message, state: FSMContext):
    checkout = parse_date(message.text)
    if checkout is None:
        await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД.")
        return
    await state.update_data(checkout_date=checkout)
    await message.answer("Сколько ночей вы планируете? Введите диапазон через дефис (например, 5-7) или одно число.")
    await state.set_state(SearchStates.waiting_for_nights)

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

async def show_confirmation(message: Message, data: dict):
    nights_min = data.get('nights_min')
    nights_max = data.get('nights_max')
    if nights_min is not None and nights_max is not None:
        nights_str = f"{nights_min}-{nights_max}"
    else:
        nights_str = "не указано"
    text = (
        "📋 Проверьте параметры:\n"
        f"Страна: {data.get('country', 'не указана')}\n"
        f"Город вылета: {data.get('departure_city', 'не указан')}\n"
        f"Заезд: {data.get('checkin_date', 'не указан')}\n"
        f"Ночей: {nights_str}\n"
        f"Взрослых: {data.get('adults', 1)}\n"
        f"Детей: {data.get('kids', 0)}\n"
        f"Младенцев: {data.get('infants', 0)}\n"
        f"Категории отелей: {', '.join(map(str, data.get('hotel_categories', []))) or 'любые'}\n"
        f"Макс. цена: {data.get('max_price', 'не указана')} руб.\n"
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
        checkin_date_to=data['checkout_date'],
        nights_min=data.get('nights_min'),
        nights_max=data.get('nights_max'),
        adults=data.get('adults', 2),
        kids=data.get('kids', 0),
        infants=data.get('infants', 0),
        hotel_categories=data.get('hotel_categories', []),
        max_price=data.get('max_price')
    )
    # Здесь нужно вызвать поиск (пока заглушка)
    await callback.message.edit_text("Поиск выполнен! (заглушка)")
    await state.clear()

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