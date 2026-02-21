import os
import random
import base64
import requests
from typing import Dict

from agents.affect_vector_agent import AffectState
from agents.regulation_agent import RegulationPlan


class SpotifyAgent:
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    SEARCH_URL = "https://api.spotify.com/v1/search"

    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET eksik")

        self.token: str | None = None
        self._refresh_token()

    # ================= AUTH =================
    def _refresh_token(self):
        auth = f"{self.client_id}:{self.client_secret}"
        b64 = base64.b64encode(auth.encode()).decode()

        r = requests.post(
            self.TOKEN_URL,
            headers={
                "Authorization": f"Basic {b64}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        r.raise_for_status()
        self.token = r.json()["access_token"]

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    # ================= LANGUAGE =================
    def _is_turkish(self, text: str) -> bool:
        turkish_chars = "çğıöşüÇĞİÖŞÜ"
        return any(c in text for c in turkish_chars)

    # ================= PUBLIC =================
    def recommend(
        self,
        emotion: str,
        state: AffectState,
        plan: RegulationPlan
    ) -> Dict:
        try:
            return self._recommend_internal(emotion, state, plan)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                self._refresh_token()
                return self._recommend_internal(emotion, state, plan)
            raise

    # ================= CORE =================
    def _recommend_internal(
        self,
        emotion: str,
        state: AffectState,
        plan: RegulationPlan
    ) -> Dict:

        queries: list[str] = []

        # 1️⃣ EMOTION → zayıf ipucu
        if emotion == "mutluluk":
            queries += ["warm chill", "positive calm"]
        elif emotion == "hüzün":
            queries += ["soft acoustic", "calm piano"]
        elif emotion == "öfke":
            queries += ["calm lofi"]
        elif emotion == "korku":
            queries += ["safe ambient"]
        else:
            queries += ["chill instrumental"]

        # 2️⃣ REGULATION DELTA → ana yön
        d = plan.delta

        if d["arousal"] <= -10:
            queries += ["slow ambient", "low tempo", "calm lofi"]

        if d["arousal"] >= 10:
            queries += ["uplifting pop", "energetic indie"]

        if d["physical_comfort"] >= 10:
            queries += ["soft piano", "warm acoustic"]

        if d["environmental_calm"] >= 10:
            queries += ["peaceful ambient", "minimal ambient"]

        if d["emotional_intensity"] <= -10:
            queries += ["low intensity instrumental"]

        if d["emotional_intensity"] >= 10:
            queries += ["emotional indie", "cinematic instrumental"]

        if d["valence"] >= 10:
            queries += ["feel good chill"]

        if d["valence"] <= -10:
            queries += ["melancholic indie", "soft sad songs"]

        if not queries:
            queries = ["chill instrumental"]

        query = random.choice(queries)

        # 3️⃣ Spotify Search
        params = {
            "q": query,
            "type": "track",
            "limit": 30,
            "market": "TR"
        }

        r = requests.get(
            self.SEARCH_URL,
            headers=self._headers(),
            params=params,
            timeout=15,
        )
        r.raise_for_status()

        items = r.json().get("tracks", {}).get("items", [])
        if not items:
            return self._fallback(query)

        tr, foreign = [], []
        for t in items:
            artist = t["artists"][0]["name"]
            (tr if self._is_turkish(artist) else foreign).append(t)

        pool = tr if tr and random.random() < 0.5 else (foreign or tr)
        track = random.choice(pool)

        return {
            "query": query,
            "track": track["name"],
            "artist": track["artists"][0]["name"],
            "spotify_url": track["external_urls"]["spotify"],
            "language": "TR" if track in tr else "Foreign",
        }

    def _fallback(self, query: str) -> Dict:
        return {
            "query": query,
            "track": "Rahatlatıcı Seçim",
            "artist": "Spotify Mix",
            "spotify_url": None,
            "language": None,
        }
