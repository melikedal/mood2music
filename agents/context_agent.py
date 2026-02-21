from datetime import datetime
from agents.weather_agent import WeatherAgent


class ContextAgent:
    def __init__(self):
        self.weather_agent = WeatherAgent()

    def collect(self, city: str) -> dict:
        now = datetime.now()

        weather = self.weather_agent.get_weather(city)

        return {
            "city": city,
            "weather": weather.get("weather", "unknown"),
            "temperature": weather.get("temperature", 10.0),
            "is_dark": weather.get("is_dark", False),
            "time_of_day": "night" if now.hour < 6 or now.hour >= 20 else "day",
            "day_type": "weekday" if now.weekday() < 5 else "weekend",
        }
