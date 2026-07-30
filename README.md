# ✈️ TakeFlight Bot

Telegram-бот для поиска горящих туров с уведомлениями о снижении цен.

## Возможности

- Поиск туров по критериям: страна, город вылета, даты, количество ночей, звёзды отеля, бюджет.
- Показ нескольких вариантов туров.
- Подписка на критерии – бот проверяет цены и уведомляет о снижении (интервал 10 минут).
- Использование фидов Level.Travel для получения актуальных туров.

## Технологии

- Python 3.12
- Aiogram 3.x (FSM, роутеры)
- SQLAlchemy 2.0 (async) + aiosqlite
- Pydantic + Pydantic Settings
- aiohttp
- logging
- pytest + pytest-asyncio

## Установка и запуск

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/takeflight-bot.git
   cd takeflight-bot
Создайте виртуальное окружение и установите зависимости:

bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# или venv\Scripts\activate для Windows
pip install -r requirements.txt
Настройте переменные окружения:
Скопируйте .env.example в .env и заполните:

BOT_TOKEN – токен вашего Telegram-бота.

TRAVELATA_LOGIN и TRAVELATA_PASSWORD – данные для доступа к справочникам Travelata API.

Остальные параметры можно оставить по умолчанию.

Запустите бота:

bash
python main.py
Структура проекта
main.py – точка входа.

config.py – настройки.

models.py – Pydantic-модели.

repository.py – ORM-модели и CRUD-операции.

travelata_api.py – клиент для справочников (страны, города вылета).

level_feed_loader.py – загрузчик фидов Level.Travel.

cache.py – кеш справочников.

price_monitor.py – фоновый мониторинг цен.

handlers/ – обработчики команд (FSM, поиск, подписки).

tests/ – тесты.

Команды бота
/start – приветствие

/help – справка

/search – начать поиск тура

/test_search – тестовый поиск с предустановками

/subscribe – подписаться на текущие критерии

/my_subscriptions – показать мои подписки

/stop – отписаться от всех уведомлений

/hot – горящие туры (быстрый поиск) – в разработке

Тестирование
Запустите тесты:

bash
pytest -v

Лицензия
MIT
