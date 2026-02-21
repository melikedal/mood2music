from __future__ import annotations
import os
import re
import json
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

load_dotenv()

try:
    import google.generativeai as genai
except Exception:
    genai = None


# ================= OUTPUT =================
@dataclass
class EmotionOutput:
    ml_label: str
    llm_label: str
    rule_label: str
    final_emotion: str
    debug: List[str]


# ================= AGENT =================
class EmotionAgent:
    HF_MODEL = "savasy/bert-base-turkish-sentiment-cased"
    EMOTIONS = ["mutluluk", "hüzün", "öfke", "korku", "şaşkınlık", "nötr"]

    def __init__(self, use_gpu: bool = False):
        self.debug: List[str] = []

        # ---------- ML MODEL ----------
        self.tokenizer = AutoTokenizer.from_pretrained(self.HF_MODEL)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.HF_MODEL)
        self.model.eval()

        self.device = torch.device(
            "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        )
        self.model.to(self.device)

        # ---------- RULE-BASED ----------
        self.negations = [
            "değil", "degil", "hiç", "asla", "yok",
            "olmuyor", "olmadı", "olamaz"
        ]

        self.irony_phrases = [
            "tabii tabii", "aynen", "çok komik",
            "hadi canım", "kesin", "ya tabi"
        ]

        self.neutral_phrases = [
            "idare eder", "eh işte", "fena değil",
            "orta", "şöyle böyle", "ne iyi ne kötü",
            "normal", "bilmiyorum", "karışık",
            "ortalama", "eh", "idare",
            "kötü değil", "iyi değil"
        ]

        # 🔑 KISA AMA ANLAMLI KELİMELER EKLENDİ
        self.emotion_lexicon = {
            "mutluluk": [
                "mutlu", "sevinç", "harika", "müthiş",
                "keyif", "huzur", "iyi", "güzel", "memnun"
            ],
            "hüzün": [
                "üzgün", "kırgın", "yalnız",
                "ağladım", "hasret", "pişman"
            ],
            "öfke": [
                "sinir", "öfke", "kızgın",
                "nefret", "bıktım", "yeter"
            ],
            "korku": [
                "kork", "ürktüm", "panik",
                "dehşet", "endişe"
            ],
            "şaşkınlık": [
                "şaşkın", "inanmıyorum",
                "vay be", "ciddi misin"
            ],
        }

        # ---------- LLM ----------
        api_key = os.getenv("GOOGLE_API_KEY")
        self.llm_enabled = bool(api_key) and genai is not None

        if self.llm_enabled:
            genai.configure(api_key=api_key)
            try:
                self.llm = genai.GenerativeModel("gemini-2.5-flash-lite")
            except Exception:
                self.llm = genai.GenerativeModel("models/gemini-flash-latest")
        else:
            self.llm = None

    # ================= PUBLIC =================
    def analyze(self, text: str) -> EmotionOutput:
        self.debug = []
        clean = self._normalize(text)

        # ---------- AJANDA: KISA METİN FİLTRESİ ----------
        if len(clean) < 5:
            if self._contains_any(clean, self._all_lexicon_words()):
                self.debug.append(
                    "Ajanda: Kısa ama anlamlı kelime → analiz devam"
                )
            else:
                self.debug.append(
                    "Ajanda: Kısa & anlamsız metin → nötr"
                )
                return EmotionOutput(
                    ml_label="nötr",
                    llm_label="nötr",
                    rule_label="nötr",
                    final_emotion="nötr",
                    debug=self.debug
                )

        # ---------- ML ----------
        ml_label = self._ml_predict(clean)
        self.debug.append(f"ML(BERT) sonucu: {ml_label}")

        # ---------- RULE ----------
        rule_label = self._rule_predict(clean)
        self.debug.append(f"Rule-based sonucu: {rule_label}")

        # ---------- LLM ----------
        llm_label = "nötr"
        if self.llm_enabled:
            llm_label = self._llm_predict(clean)
            self.debug.append(f"LLM(Gemini) sonucu: {llm_label}")
        else:
            self.debug.append("LLM(Gemini) devre dışı")

        # ---------- FUSION ----------
        final_emotion = self._fusion(rule_label, ml_label, llm_label)
        self.debug.append(f"FINAL: {final_emotion}")

        return EmotionOutput(
            ml_label=ml_label,
            llm_label=llm_label,
            rule_label=rule_label,
            final_emotion=final_emotion,
            debug=self.debug
        )

    # ================= ML =================
    def _ml_predict(self, text: str) -> str:
        inputs = self.tokenizer(
            text, return_tensors="pt",
            truncation=True, padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self.model(**inputs).logits
            pred_id = int(torch.argmax(logits, dim=1).item())

        raw = self.model.config.id2label.get(pred_id, "").lower()

        if "positive" in raw:
            return "mutluluk"
        if "negative" in raw:
            return "hüzün"
        return "nötr"

    # ================= RULE =================
    def _rule_predict(self, text: str) -> str:
        for p in self.neutral_phrases:
            if p in text:
                return "nötr"

        for p in self.irony_phrases:
            if p in text:
                return "hüzün"

        if any(n in text.split() for n in self.negations):
            if self._contains_any(text, self.emotion_lexicon["mutluluk"]):
                return "hüzün"

        scores = {e: 0 for e in self.EMOTIONS}
        for emo, words in self.emotion_lexicon.items():
            for w in words:
                if re.search(rf"\b{re.escape(w)}\b", text):
                    scores[emo] += 1

        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else "nötr"

    # ================= LLM =================
    def _llm_predict(self, text: str) -> str:
        if not self.llm:
            return "nötr"

        prompt = f"""
Sadece JSON döndür.

Etiketler:
mutluluk, hüzün, öfke, korku, şaşkınlık, nötr

Cümle:
{text}

JSON:
{{"label":"nötr"}}
"""
        try:
            resp = self.llm.generate_content(prompt)
            raw = (resp.text or "").strip()

            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                raw = raw[start:end + 1]

            data = json.loads(raw)
            label = str(data.get("label", "nötr")).lower()
            return label if label in self.EMOTIONS else "nötr"
        except Exception:
            return "nötr"

    # ================= FUSION =================
    def _fusion(self, rule_label: str, ml_label: str, llm_label: str) -> str:
        if rule_label != "nötr":
            self.debug.append("Fusion: Rule-based öncelik")
            return rule_label

        if llm_label != "nötr" and llm_label != ml_label:
            self.debug.append("Fusion: ML–LLM çelişkisi → LLM")
            return llm_label

        if rule_label == "nötr" and llm_label == "nötr":
            self.debug.append("Fusion: Düşük sinyal → nötr")
            return "nötr"

        self.debug.append("Fusion: ML destekleyici kabul edildi")
        return ml_label

    # ================= UTILS =================
    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.lower().strip())

    def _contains_any(self, text: str, words: List[str]) -> bool:
        return any(
            re.search(rf"\b{re.escape(w)}\b", text)
            for w in words
        )

    def _all_lexicon_words(self) -> List[str]:
        return sum(self.emotion_lexicon.values(), [])
