async def generate_itinerary(destination: str, dates: str, travelers: int, preferences: str) -> str:
    return (
        f"Trip plan for {destination}\n"
        f"Dates: {dates}\n"
        f"Travelers: {travelers}\n"
        f"Preferences: {preferences}\n\n"
        f"Day 1: Explore the city center.\n"
        f"Day 2: Visit famous attractions.\n"
        f"Day 3: Leisure and shopping.\n"
    )
