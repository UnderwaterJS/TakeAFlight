from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from repository import (
    get_or_create_user,
    create_search_criteria,
    create_subscription,
    get_criteria_by_user,
    deactivate_subscription,
    get_subscription_by_id
)
from cache import cache

router = Router()

class SubscribeStates(StatesGroup):
    waiting_for_confirm = State()

@router.message(lambda msg: msg.text == "/subscribe")
async def cmd_subscribe(message: Message, state: FSMContext):
    data = await state.get_data()
    criteria_data = data.get("last_search_criteria")
    if not criteria_data:
        await message.answer("Сначала выполните поиск, чтобы задать критерии.")
        return

    text = "Вы хотите подписаться на следующие критерии:\n"
    text += f"Страна: {cache.get_country_name(criteria_data.get('country_id'))}\n"
    text += f"Город вылета: {cache.get_departure_city_name(criteria_data.get('departure_city_id'))}\n"
    text += f"Даты: {criteria_data.get('checkin_date_from')} – {criteria_data.get('checkin_date_to')}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подписаться", callback_data="confirm_subscribe")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_subscribe")]
    ])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(SubscribeStates.waiting_for_confirm)

@router.callback_query(F.data == "confirm_subscribe", SubscribeStates.waiting_for_confirm)
async def confirm_subscribe(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    criteria_data = data.get("last_search_criteria")
    if not criteria_data:
        await callback.answer("Критерии не найдены.", show_alert=True)
        return

    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name
    )

    criteria_orm = await create_search_criteria({
        "user_id": user.id,
        "country_id": criteria_data.get("country_id"),
        "departure_city_id": criteria_data.get("departure_city_id"),
        "checkin_date_from": criteria_data.get("checkin_date_from"),
        "checkin_date_to": criteria_data.get("checkin_date_to"),
        "nights_min": criteria_data.get("nights_min"),
        "nights_max": criteria_data.get("nights_max"),
        "adults": criteria_data.get("adults", 2),
        "kids": criteria_data.get("kids", 0),
        "infants": criteria_data.get("infants", 0),
        "hotel_categories": criteria_data.get("hotel_categories", []),
        "resorts": criteria_data.get("resorts", []),
        "max_price": criteria_data.get("max_price"),
    })

    subscription = await create_subscription(user.id, criteria_orm.id)

    await callback.message.edit_text("✅ Вы подписались на обновления цен по этим критериям.")
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "cancel_subscribe", SubscribeStates.waiting_for_confirm)
async def cancel_subscribe(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Подписка отменена.")
    await callback.answer()
    await state.clear()

@router.message(lambda msg: msg.text == "/my_subscriptions")
async def cmd_my_subscriptions(message: Message):
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    from repository import get_active_subscriptions
    all_subs = await get_active_subscriptions()
    user_subs = [s for s in all_subs if s.user_id == user.id]
    if not user_subs:
        await message.answer("У вас нет активных подписок.")
        return

    text = "Ваши подписки:\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for sub in user_subs:
        crit = sub.criteria
        country = cache.get_country_name(crit.country_id) if crit.country_id else "Любая"
        city = cache.get_departure_city_name(crit.departure_city_id) if crit.departure_city_id else "Любой"
        text += f"• {country}, вылет из {city}, {crit.checkin_date_from.date()}–{crit.checkin_date_to.date()}\n"
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=f"Отписаться #{sub.id}", callback_data=f"unsub_{sub.id}")]
        )
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("unsub_"))
async def unsubscribe_callback(callback: CallbackQuery):
    sub_id = int(callback.data.split("_")[1])
    sub = await get_subscription_by_id(sub_id)
    if not sub or sub.user_id != (await get_or_create_user(callback.from_user.id)).id:
        await callback.answer("Подписка не найдена.", show_alert=True)
        return
    await deactivate_subscription(sub_id)
    await callback.message.edit_text("✅ Подписка отменена.")
    await callback.answer()