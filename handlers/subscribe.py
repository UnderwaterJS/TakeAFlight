import logging
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from handlers.states import SearchStates
from repository import (
    get_or_create_user,
    create_search_criteria,
    create_subscription,
    get_user_active_subscriptions,
    deactivate_subscription,
    deactivate_all_user_subscriptions,
    search_feed_tours,
    update_subscription_price
)
from cache import cache
from handlers import state as app_state

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, state: FSMContext):
    """Создаёт подписку на последние использованные критерии поиска."""
    data = await state.get_data()
    criteria_data = data.get("last_search_criteria")
    if not criteria_data:
        await message.answer(
            "Сначала выполните поиск, чтобы задать критерии.\n"
            "Используйте /search и настройте параметры."
        )
        return

    country_name = cache.get_country_name(criteria_data.get('country_id')) if criteria_data.get('country_id') else "Любая"
    city_name = cache.get_departure_city_name(criteria_data.get('departure_city_id')) if criteria_data.get('departure_city_id') else "Любой"
    checkin = criteria_data.get('checkin_date_from')
    checkout = criteria_data.get('checkin_date_to')
    
    if 'checkout_date' in criteria_data:
        date_str = f"{checkin.strftime('%Y-%m-%d')} – {criteria_data['checkout_date'].strftime('%Y-%m-%d')}"
    else:
        nights = criteria_data.get('nights_min', criteria_data.get('nights_max'))
        if nights:
            date_str = f"{checkin.strftime('%Y-%m-%d')} + {nights} ночей"
        else:
            date_str = f"{checkin.strftime('%Y-%m-%d')} (дата выезда не указана)"

    stars = criteria_data.get('hotel_categories', [])
    stars_str = ', '.join(f"{s}★" for s in stars) if stars else "любые"
    max_price = criteria_data.get('max_price', 'не указана')

    text = (
        "📌 Вы хотите подписаться на следующие критерии:\n\n"
        f"🌍 Страна: {country_name}\n"
        f"✈️ Город вылета: {city_name}\n"
        f"📅 Даты: {date_str}\n"
        f"⭐ Звёзды: {stars_str}\n"
        f"💰 Макс. цена: {max_price} руб.\n\n"
        "Подтвердите подписку."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подписаться", callback_data="confirm_subscribe")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_subscribe")]
    ])
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "confirm_subscribe")
async def confirm_subscribe(callback: CallbackQuery, state: FSMContext):
    """Сохраняет критерии и создаёт подписку."""
    await callback.answer()

    data = await state.get_data()
    criteria_data = data.get("last_search_criteria")
    if not criteria_data:
        await callback.message.edit_text("❌ Критерии не найдены. Попробуйте сначала выполнить поиск.")
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
        "checkin_date_to": criteria_data.get("checkin_date_to") or criteria_data.get("checkin_date_from"),  # если нет даты выезда, то используем дату заезда
        "nights_min": criteria_data.get("nights_min"),
        "nights_max": criteria_data.get("nights_max"),
        "adults": criteria_data.get("adults", 2),
        "kids": criteria_data.get("kids", 0),
        "infants": criteria_data.get("infants", 0),
        "hotel_categories": criteria_data.get("hotel_categories", []),
        "resorts": criteria_data.get("resorts", []),
        "max_price": criteria_data.get("max_price"),
    })

    from repository import find_subscription_by_user_and_criteria
    existing = await find_subscription_by_user_and_criteria(user.id, criteria_orm.id)
    if existing and existing.is_active:
        await callback.message.edit_text("ℹ️ Вы уже подписаны на эти критерии.")
        return

    subscription = await create_subscription(user.id, criteria_orm.id)

    try:
        country_name = cache.get_country_name(criteria_data.get('country_id')) if criteria_data.get('country_id') else None
        city_name = cache.get_departure_city_name(criteria_data.get('departure_city_id')) if criteria_data.get('departure_city_id') else None
        if country_name and city_name and app_state.feeds_loaded:
            date_from = criteria_data.get('checkin_date_from')
            date_to = criteria_data.get('checkin_date_to') or date_from
            stars = criteria_data.get('hotel_categories', [])
            max_price = criteria_data.get('max_price', 9999999)
            tours = await search_feed_tours(
                departure_city=city_name,
                country=country_name,
                date_from=date_from,
                date_to=date_to,
                nights_min=criteria_data.get('nights_min', 1),
                nights_max=criteria_data.get('nights_max', 30),
                stars=stars,
                max_price=max_price,
                limit=10
            )
            if tours:
                min_price = min(t.price for t in tours)
                await update_subscription_price(subscription.id, min_price)
                logger.info(f"Установлена начальная цена {min_price} для подписки {subscription.id}")
    except Exception as e:
        logger.error(f"Не удалось установить начальную цену для подписки {subscription.id}: {e}")

    await callback.message.edit_text("✅ Вы подписались на обновления цен по этим критериям.")
    await state.clear()

@router.callback_query(F.data == "cancel_subscribe")
async def cancel_subscribe(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("❌ Подписка отменена.")
    await state.clear()

@router.message(Command("my_subscriptions"))
async def cmd_my_subscriptions(message: Message):
    """Показывает список активных подписок пользователя."""
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    subscriptions = await get_user_active_subscriptions(user.id)
    if not subscriptions:
        await message.answer("У вас нет активных подписок.\n"
                             "Чтобы создать подписку, выполните поиск и используйте /subscribe.")
        return

    text = "📋 Ваши активные подписки:\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for idx, sub in enumerate(subscriptions, 1):
        crit = sub.criteria
        country = cache.get_country_name(crit.country_id) if crit.country_id else "Любая"
        city = cache.get_departure_city_name(crit.departure_city_id) if crit.departure_city_id else "Любой"
        date_from = crit.checkin_date_from.strftime("%Y-%m-%d") if crit.checkin_date_from else "не указана"
        date_to = crit.checkin_date_to.strftime("%Y-%m-%d") if crit.checkin_date_to else "не указана"
        nights = f"{crit.nights_min}–{crit.nights_max}" if crit.nights_min and crit.nights_max else str(crit.nights_min) if crit.nights_min else "не указано"
        stars = ', '.join(f"{s}★" for s in crit.hotel_categories) if crit.hotel_categories else "любые"
        max_price = crit.max_price if crit.max_price else "не указана"

        text += (
            f"{idx}. {country}, вылет из {city}\n"
            f"   📅 {date_from} – {date_to}\n"
            f"   🌙 {nights} ночей\n"
            f"   ⭐ {stars}\n"
            f"   💰 до {max_price} руб.\n"
            f"   🆔 ID: {sub.id}\n\n"
        )
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"❌ Отписаться #{sub.id}", callback_data=f"unsub_{sub.id}")
        ])

    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("unsub_"))
async def unsubscribe_callback(callback: CallbackQuery):
    """Обработка отписки по кнопке."""
    sub_id = int(callback.data.split("_")[1])
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name
    )

    from repository import get_subscription_by_id
    sub = await get_subscription_by_id(sub_id)
    if not sub or sub.user_id != user.id:
        await callback.answer("Подписка не найдена или не принадлежит вам.", show_alert=True)
        return

    await deactivate_subscription(sub_id)
    await callback.answer("✅ Вы отписались.")
    await callback.message.edit_text("✅ Подписка отменена.")

@router.message(Command("stop"))
async def cmd_stop(message: Message):
    """Отписывает пользователя от всех уведомлений (деактивирует все подписки)."""
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    count = await deactivate_all_user_subscriptions(user.id)
    if count:
        await message.answer(f"✅ Вы отписаны от всех {count} подписок.")
    else:
        await message.answer("У вас не было активных подписок.")