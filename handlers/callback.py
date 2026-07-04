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

@router.callback_query(F.data.startswith("subscribe_tour_"))
async def subscribe_tour(callback: CallbackQuery):
    tour_identity = callback.data.split("_")[-1]
    await callback.answer(f"Подписка на тур {tour_identity} пока не реализована.", show_alert=True)

@router.callback_query(F.data.startswith("subscribe_criteria_"))
async def subscribe_criteria(callback: CallbackQuery):
    criteria_id = int(callback.data.split("_")[-1])
    await callback.answer(f"Подписка на критерии #{criteria_id} пока не реализована.", show_alert=True)

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