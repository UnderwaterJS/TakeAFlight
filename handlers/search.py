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
    except ValeuError:
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
    try:
        checkin = parse_date(message.text)
    except not checkin:
        await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД.")
        return
    await state.update_data(checkin_date=checkin)
    await message.answer("Введите дату выезда (ГГГГ-ММ-ДД).")
    await state.set_state(SearchStates.waiting_for_checkout_date)

@router.message(StateFilter(SearchStates.waiting_for_checkout_date))
async def process_checkout(message: Message, state: FSMContext):
    try:
        checkout = parse_date(message.text)
    except not checkout:
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

# Пропуск (для опциональных полей)
@router.message(Command("skip"))
async def cmd_skip(message: Message, state: FSMContext):
    # Текущее состояние определяет, что пропускаем
    current_state = await state.get_state()
    if current_state == SearchStates.waiting_for_adults:
        await state.update_data(adults=2)
        await message.answer("Принято (2 взрослых). Теперь укажите количество детей (0 по умолчанию) или /skip.")
        await state.set_state(SearchStates.waiting_for_kids)
    elif current_state == SearchStates.waiting_for_kids:
        await state.update_data(kids=0)
        await message.answer("Принято (0 детей). Теперь укажите количество младенцев (0) или /skip.")
        await state.set_state(SearchStates.waiting_for_infants)
    elif current_state == SearchStates.waiting_for_infants:
        await state.update_data(infants=0)
        await message.answer("Принято. Теперь введите категории отелей (звёзды) через запятую, например 5,4 или /skip.")
        await state.set_state(SearchStates.waiting_for_hotel_categories)
    elif current_state == SearchStates.waiting_for_hotel_categories:
        await state.update_data(hotel_categories=[])
        await message.answer("Принято. Введите максимальную цену в рублях или /skip.")
        await state.set_state(SearchStates.waiting_for_max_price)
    elif current_state == SearchStates.waiting_for_max_price:
        await state.update_data(max_price=None)
        await show_summary(message, state)
    else:
        await message.answer("Пропуск недоступен на этом шаге.")

async def show_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    # Формируем сообщение со всеми критериями
    text = (
        "📋 Ваши критерии:\n"
        f"• Страна: {data.get('country_id')}\n"
        f"• Город вылета: {data.get('departure_city')}\n"
        f"• Даты: {data.get('checkin_date')} – {data.get('checkout_date')}\n"
        f"• Ночи: {data.get('nights_min')} - {data.get('nights_max')}\n"
        f"• Взрослых: {data.get('adults', 2)}\n"
        f"• Детей: {data.get('kids', 0)}\n"
        f"• Младенцев: {data.get('infants', 0)}\n"
        f"• Категории отелей: {data.get('hotel_categories', 'не указаны')}\n"
        f"• Макс. цена: {data.get('max_price', 'не указана')}\n\n"
        "✅ Всё верно? Нажмите 'Искать' или введите /cancel для отмены."
    )
    # Кнопки подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Искать", callback_data="search_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="search_cancel")]
    ])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(SearchStates.waiting_for_confirmation)

# Обработка подтверждения
@router.callback_query(F.data == "search_confirm", StateFilter(SearchStates.waiting_for_confirmation))
async def confirm_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Ищем...")
    data = await state.get_data()
    # Преобразуем в SearchCriteria
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

# НЕДОСТАЮЩИЕ ОБРАБОТЧИКИ (будут реализованы позже)

# 1. waiting_for_adults – количество взрослых (по умолчанию 2)
#    Ожидаем число, /skip → 2

# 2. waiting_for_kids – количество детей от 2 до 11 лет (по умолчанию 0)
#    Ожидаем число, /skip → 0

# 3. waiting_for_infants – количество младенцев до 2 лет (по умолчанию 0)
#    Ожидаем число, /skip → 0

# 4. waiting_for_hotel_categories – категории отелей (звёзды)
#    Ожидаем числа через запятую, например 5,4  или /skip → []

# 5. waiting_for_max_price – максимальная цена в рублях
#    Ожидаем целое число, /skip → None

# 6. После ввода max_price показываем сводку и переходим в waiting_for_confirmation
#    (уже есть функция show_summary)