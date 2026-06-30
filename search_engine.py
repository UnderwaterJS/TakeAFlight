from typing import List, Optional, Dict, Any
from models import Tour, SearchCriteria


def calculate_match_score(tour: Tour, criteria: SearchCriteria) -> float:
    """
    Вычисляем процент соответствия тура по критериям (0..1).
    """
    weights = {
        'country': 0.25,
        'resorts': 0.15,
        'dates': 0.25,
        'nights': 0.15,
        'hotel_category': 0.10,
        'price': 0.10,
    }
    score = 0.0

    # 1. Страна
    if criteria.country_id is not None:
        # Предполагаем, что у нас есть функция get_resort_country(resort_id)
        # Пока упростим: если resortId не связан со страной напрямую, пропускаем.
        # В реальности нужно получить страну курорта через справочник.
        # Здесь используем заглушку: считаем, что у нас есть словарь resort_to_country.
        # Временно считаем, что все туры из правильной страны (если не знаем).
        pass

    # 2. Курорты
    if criteria.resorts:
        if tour.resortId in criteria.resorts:
            score += weights['resorts']
        else:
            # Можно дать частичное совпадение, если курорт рядом
            score += 0.0  # пока 0, но ориентировочно считать 0.07(половина от 'resorts')

    # 3. Даты заезда
    if criteria.checkin_date_from and criteria.checkin_date_to:
        if criteria.checkin_date_from <= tour.checkinDate <= criteria.checkin_date_to:
            score += weights['dates']
        else:
            # Частичное совпадение: чем ближе дата к интервалу, тем выше
            # Для простоты пока 0
            pass

    # 4. Ночи
    if criteria.nights_min is not None and criteria.nights_max is not None:
        if criteria.nights_min <= tour.nights <= criteria.nights_max:
            score += weights['nights']
        else:
            # Частичное: в зависимости от числа до ближайшей границы
            pass

    # 5. Категория отеля
    if criteria.hotel_categories:
        if tour.hotelCategory in criteria.hotel_categories:
            score += weights['hotel_category']
        else:
            # Можно проверить, есть ли близкая категория (например, если искали 5*, а нашли 4*)
            pass

    # 6. Цена
    if criteria.max_price is not None:
        if tour.price <= criteria.max_price:
            score += weights['price']
        else:
            # Частичное: чем меньше превышение, тем лучше
            pass

    return score

def rank_tours(tours: List[Tour], criteria: SearchCriteria) -> List[Dict[str, Any]]:
    """
    Возвращает список туров с добавленным полем match_percent, отсортированный по убыванию.
    """
    ranked = []
    for tour in tours:
        score = calculate_match_score(tour, criteria)
        ranked.append({
            'tour': tour,
            'match_percent': round(score * 100, 1)
        })
    ranked.sort(key=lambda x: x['match_percent'], reverse=True)
    return ranked

def filter_by_match_threshold(
        tours: List[Tour],
        criteria: SearchCriteria,
        thresholds: List[float] = [1.0, 0.8, 0.6]
) -> List[Dict[str, Any]]:
    """
    Последовательно применяет пороги, возвращает туры, удовлетворяющие хотя бы одному.
    Если на первом пороге есть >= 3 результата, возвращает их.
    Иначе расширяет до следующего порога.
    """
    all_ranked = rank_tours(tours, criteria)
    for threshold in thresholds:
        filtered = [item for item in all_ranked if item['match_percent'] >= threshold * 100]
        if len(filtered) >= 3: # минимальное количество для показа
            return filtered
        # Если ни один порог не дал 3 результата, возвращаем все (или пустой)
    return all_ranked[:5]  # хотя бы 5 лучших