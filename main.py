from travelata_api import TravelataAPIClient
from config import settings
from datetime import date

async def search_tours():
    async with TravelataAPIClient(
        login=settings.travelata_login,
        password=settings.travelata_password
    ) as client:
        tours = await client.get_cheapest_tours(
            country_ids=[92],
            departure_city=2,
            checkin_date_from=date(2026, 7, 1),
            checkin_date_to=date(2026, 7, 15),
            adults=2
        )
        for tour in tours:
            print(tour.hotelName, tour.price)