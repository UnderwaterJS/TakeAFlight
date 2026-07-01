from aiogram import Router, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from repository import (
    get_or_create_user,
    create_search_criteria,
    create_subscription,
    save_price_history
)
from models import Tour, SearchCriteria

router = Router()

# Обработчик кнопки "Подписаться на тур"
@router.callback_query(F.data.startswith("subscribe_tour_"))
async def subscribe_to_tour(callback: CallbackQuery):
    tour_identity = callback.data.split("_")[2]  # формат: subscribe_tour_<tour_identity>
    user = await get_or_create_user(callback.from_user.id)
    
    # Здесь нужно создать подписку на конкретный тур.
    # Для этого мы можем сохранить критерии поиска, которые привели к этому туру,
    # или сохранить сам tour_identity как отдельную подписку.
    # В нашей модели Subscription привязана к SearchCriteria, но мы можем расширить её позже.
    await callback.answer("Вы подписались на уведомления по этому туру! Мы сообщим, если цена снизится.")
    await callback.message.edit_reply_markup(reply_markup=None)  # убираем кнопки

# Кнопка "Показать ещё" – загружает следующую страницу результатов
@router.callback_query(F.data == "show_more")
async def show_more_tours(callback: CallbackQuery):
    # и показать следующую порцию.
    await callback.answer("Загружаем ещё туры...")
    # Заглушка:
    await callback.message.answer("Дополнительные туры (заглушка).")

# Кнопка "Детали" – показывает подробную информацию о туре
@router.callback_query(F.data.startswith("tour_details_"))
async def tour_details(callback: CallbackQuery):
    tour_identity = callback.data.split("_")[2]
    # Здесь нужно получить тур из кэша или БД по tour_identity и показать детали.
    await callback.answer("Детали тура")
    await callback.message.answer(
        f"🏨 Детали тура {tour_identity}\n"
        "Пока здесь только заглушка, но позже будет полная информация."
    )

# Общий обработчик для неизвестных callback (логирование)
@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer("Неизвестное действие", show_alert=True)