from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from repository import (
    get_or_create_user,
    create_search_criteria,
    create_subscription,
    get_criteria_by_user,
    deactivate_subscription,
    get_subscription_by_id
)
from models import SearchCriteria

router = Router()

# Команда /subscribe – подписка на последние критерии (или на текущий поиск)
@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    # Заглушка: пока просто скажем, что нужно сначала выполнить поиск.
    await message.answer(
        "📌 Чтобы подписаться на уведомления о снижении цен, сначала выполните поиск (/search). "
        "После получения результатов нажмите кнопку 'Подписаться' под любым туром.\n\n"
        "Или используйте /my_subscriptions для управления подписками."
    )

# /my_subscriptions – список активных подписок
@router.message(Command("my_subscriptions"))
async def cmd_my_subscriptions(message: Message):
    user = await get_or_create_user(message.from_user.id, username=message.from_user.username)
    criteria_list = await get_criteria_by_user(user.id)
    if not criteria_list:
        await message.answer("У вас нет активных подписок. Создайте новую через /search.")
        return

    text = "📋 Ваши подписки:\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for i, crit in enumerate(criteria_list, 1):
        # Ищем подписку, связанную с этими критериями (у пользователя может быть только одна подписка на критерии)
        text += (
            f"{i}. Страна: {crit.country_id or 'любая'}, "
            f"Даты: {crit.checkin_date_from} – {crit.checkin_date_to}, "
            f"Ночей: {crit.nights_min or '?'}–{crit.nights_max or '?'}\n"
        )
        # Кнопка отписки (позже привяжем к конкретной подписке)
        # Пока просто добавим кнопку для каждого критерия
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"❌ Отписаться от #{i}",
                callback_data=f"unsub_{crit.id}"
            )
        ])

    if keyboard.inline_keyboard:
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text)

# Обработчик отписки по кнопке
@router.callback_query(F.data.startswith("unsub_"))
async def unsubscribe_callback(callback: CallbackQuery):
    # Извлекаем ID критериев (или подписки) из callback.data
    crit_id = int(callback.data.split("_")[1])
    # Находим подписку пользователя на эти критерии
    # В реальности нужно найти subscription по user_id и criteria_id
    await deactivate_subscription_by_criteria(callback.from_user.id, crit_id)
    await callback.answer("Вы отписались от уведомлений по этим критериям.")
    await callback.message.edit_text("Подписка отменена.")

# /stop – отписаться от всех уведомлений
@router.message(Command("stop"))
async def cmd_stop(message: Message):
    user = await get_or_create_user(message.from_user.id)
    # Получаем все активные подписки пользователя и деактивируем их
    await deactivate_all_user_subscriptions(user.id)
    await message.answer("Вы отписались от всех уведомлений. Чтобы подписаться снова, используйте /search.")