from aiogram.fsm.state import State, StatesGroup

class SearchStates(StatesGroup):
    waiting_for_country = State()          # ожидаем ввод страны (можно ID или название)
    waiting_for_departure_city = State()   # город вылета
    waiting_for_checkin_date = State()     # дата заезда (в формате ГГГГ-ММ-ДД)
    waiting_for_checkout_date = State()    # дата выезда
    waiting_for_nights = State()           # количество ночей (диапазон или точное число)
    waiting_for_adults = State()           # количество взрослых (по умолчанию 2)
    waiting_for_kids = State()             # количество детей
    waiting_for_infants = State()          # количество младенцев
    waiting_for_hotel_categories = State() # категории отелей (звёзды)
    waiting_for_max_price = State()        # максимальная цена
    waiting_for_confirmation = State()     # подтверждение перед поиском