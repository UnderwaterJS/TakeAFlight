from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("✈️ Добро пожаловать в TakeFlight Bot!\n\n"
        "Я помогу найти самые выгодные туры и горящие путевки.\n"
        "Используйте /help для списка команд.")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "📖 Команды бота:\n\n"
        "/start – Приветствие\n"
        "/help – Справка\n"
        "/search – Начать поиск тура\n"
        "/subscribe – Управление подписками\n"
        "/hot – Горящие туры (быстрый поиск)\n"
        "/my_subscriptions – Мои подписки\n"
        "/stop – Отписаться от всех уведомлений\n"
        "\n"
        "💡 Вы можете задать критерии поиска:\n"
        "• Страна и курорт\n"
        "• Даты поездки\n"
        "• Количество ночей\n"
        "• Класс отеля (звёзды)\n"
        "• Максимальная цена\n"
        "\n"
        "Если подходящих туров мало, бот предложит варианты с частичным совпадением!"
    )
    await message.answer(text)

