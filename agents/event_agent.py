from dataclasses import dataclass
from typing import List, Optional
import os
import json

try:
    import google.generativeai as genai
except Exception:
    genai = None


@dataclass
class EventOutput:
    event_type: str       # energy_up, pressure, energy_down, neutral
    intensity: float      # 0.0 – 1.0
    debug: List[str]


class EventAgent:
    def __init__(self):
        self.debug: List[str] = []

        # ---------- LLM ----------
        self.enabled = bool(os.getenv("GOOGLE_API_KEY")) and genai is not None
        if self.enabled:
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.model = genai.GenerativeModel("models/gemini-flash-latest")
        else:
            self.model = None

        # ---------- RULE: ENERJİ YÜKSELTEN ----------
        self.energy_up_phrases = [
            "tebrikler", "eline sağlık", "harika iş", "çok iyi olmuş",
            "başarılı", "güzel olmuş",
            "hadi", "gel", "buluşalım", "kahve", "yemeğe çıkalım"
        ]

        # ---------- RULE: AKADEMİK / İŞ BASKISI ----------
        self.pressure_phrases = [
            "fazla basit", "basit kalmış", "yetersiz", "eksik",
            "tekrarlı", "yüzeysel",
            "revize", "güncelle", "ekleseniz", "ekleyin",
            "kullanacak mısınız", "kaç ekran", "detaylandır",
            "tekrar iletebilir", "yeniden gönder",
            "ders seviyesinde", "daha iyi olur", "bekliyoruz",
            "gerekiyor", "olmalı", "eklenmeli",
            "deadline", "son tarih", "acil", "hemen"
        ]

    def analyze(self, text: Optional[str]) -> EventOutput:
        self.debug = []

        if not text or not text.strip():
            self.debug.append("EventAgent: içerik yok")
            return EventOutput("neutral", 0.0, self.debug)

        t = text.lower()

        # ---------- 1) ENERGY UP ----------
        for p in self.energy_up_phrases:
            if p in t:
                self.debug.append(f"Rule: energy_up → {p}")
                return EventOutput("energy_up", 0.6, self.debug)

        # ---------- 2) PRESSURE ----------
        pressure_hits = 0
        for p in self.pressure_phrases:
            if p in t:
                pressure_hits += 1
                self.debug.append(f"Rule: pressure → {p}")

        rule_pressure = min(0.3 + pressure_hits * 0.1, 0.9)

        # ---------- 3) LLM (gerekiyorsa) ----------
        llm_type = None
        llm_intensity = 0.0

        should_call_llm = (
            self.enabled and (
                pressure_hits <= 1 or
                len(t.split()) > 25
            )
        )

        if should_call_llm:
            prompt = f"""
Sadece JSON döndür.

Görev:
Aşağıdaki mesajın okuyan kişiye etkisini sınıflandır.

Etiketler:
- energy_up (moral/enerji yükseltir)
- pressure (eleştiri, revizyon, iş yükü)
- energy_down (olumsuz haber)
- neutral (bilgilendirici)

JSON format:
{{"event_type":"neutral","intensity":0.0}}

Mesaj:
{text}
"""
            try:
                resp = self.model.generate_content(prompt)
                raw = (resp.text or "").strip()
                start, end = raw.find("{"), raw.rfind("}")
                if start != -1 and end != -1:
                    raw = raw[start:end + 1]

                data = json.loads(raw)
                llm_type = data.get("event_type")
                llm_intensity = float(data.get("intensity", 0.5))
                self.debug.append(f"LLM: {llm_type}, intensity={llm_intensity}")

            except Exception as e:
                self.debug.append(f"LLM hata → {e}")

        # ---------- 4) FUSION ----------
        if pressure_hits >= 2:
            self.debug.append("Fusion: Rule pressure baskın")
            return EventOutput("pressure", rule_pressure, self.debug)

        if llm_type in ("energy_up", "pressure", "energy_down"):
            self.debug.append("Fusion: LLM kararı")
            return EventOutput(llm_type, max(llm_intensity, 0.4), self.debug)

        if pressure_hits == 1:
            return EventOutput("pressure", 0.45, self.debug)

        return EventOutput("neutral", 0.0, self.debug)
