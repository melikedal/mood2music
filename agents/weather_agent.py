import os
import requests
from dotenv import load_dotenv

load_dotenv()


class WeatherAgent:
    BASE_URL = "https://api.weatherapi.com/v1/current.json"

    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY")
        self.enabled = bool(self.api_key)

    def get_weather(self, city: str) -> dict:
        # API KEY yoksa veya bossa fallback don
        if not self.enabled:
            return {"weather": "unknown", "temperature": 10.0, "is_dark": False}

        params = {"key": self.api_key, "q": city, "lang": "tr"}

        try:
            r = requests.get(self.BASE_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            condition = data["current"]["condition"]["text"].lower()
            temp = float(data["current"]["temp_c"])
            is_day = data["current"]["is_day"] == 1

            return {
                "weather": self._map_weather(condition),
                "temperature": temp,
                "is_dark": not is_day,
            }

        except Exception:
            # API patlarsa GUI cokmesin
            return {"weather": "unknown", "temperature": 10.0, "is_dark": False}

    def _map_weather(self, condition: str) -> str:
        if "yağmur" in condition or "rain" in condition:
            return "rainy"
        if "bulut" in condition or "cloud" in condition:
            return "cloudy"
        if "açık" in condition or "clear" in condition:
            return "clear"
        if "kar" in condition or "snow" in condition:
            return "snowy"
        return "neutral"
