from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AffectState:
    # 0–100 arası
    valence: int
    arousal: int
    physical_comfort: int
    environmental_calm: int
    emotional_intensity: int


@dataclass
class AffectOutput:
    state: AffectState
    breakdown: Dict[str, Dict[str, int]]
    debug: List[str]


class AffectVectorAgent:
    """
    Duygu + olay + mikro sinyal + bağlamdan 5 boyutlu state üretir.
    Tek skor yok. Her boyut ayrı.
    """

    def __init__(self):
        self.debug: List[str] = []

    def calculate(
        self,
        emotion: str,
        event_type: str | None,
        event_intensity: float,
        micro_score: int,
        context: dict
    ) -> AffectOutput:
        self.debug = []
        breakdown: Dict[str, Dict[str, int]] = {}

        base = AffectState(
            valence=50,
            arousal=50,
            physical_comfort=50,
            environmental_calm=50,
            emotional_intensity=50,
        )
        breakdown["base"] = {
            "valence": 50,
            "arousal": 50,
            "physical_comfort": 50,
            "environmental_calm": 50,
            "emotional_intensity": 50,
        }

        # 1) DUYGU
        emo_map = {
            "mutluluk":  {"valence": +18, "arousal": +8,  "physical_comfort": +10, "environmental_calm": +6,  "emotional_intensity": +6},
            "nötr":      {"valence": +0,  "arousal": +0,  "physical_comfort": +0,  "environmental_calm": +0,  "emotional_intensity": +0},
            "şaşkınlık": {"valence": +2,  "arousal": +10, "physical_comfort": -2,  "environmental_calm": -4, "emotional_intensity": +12},
            "hüzün":     {"valence": -18, "arousal": -8,  "physical_comfort": -10, "environmental_calm": -6, "emotional_intensity": +6},
            "korku":     {"valence": -15, "arousal": +12, "physical_comfort": -12, "environmental_calm": -15, "emotional_intensity": +16},
            "öfke":      {"valence": -12, "arousal": +16, "physical_comfort": -10, "environmental_calm": -12, "emotional_intensity": +18},
        }
        emo_delta = emo_map.get(emotion, emo_map["nötr"])
        breakdown["emotion"] = dict(emo_delta)
        self._apply(base, emo_delta)

        # 2) OLAY
        it = max(0.0, min(event_intensity, 1.0))
        event_delta = {"valence": 0, "arousal": 0, "physical_comfort": 0, "environmental_calm": 0, "emotional_intensity": 0}

        if event_type == "energy_up":
            eff = max(it, 0.3)
            event_delta["valence"] = int(+10 * eff)
            event_delta["arousal"] = int(+6 * eff)
            event_delta["emotional_intensity"] = int(+4 * eff)

        elif event_type in ("pressure", "stress", "energy_down"):
            eff = max(it, 0.4)
            event_delta["valence"] = int(-10 * eff)
            event_delta["arousal"] = int(+8 * eff)
            event_delta["physical_comfort"] = int(-10 * eff)
            event_delta["environmental_calm"] = int(-14 * eff)
            event_delta["emotional_intensity"] = int(+10 * eff)

        breakdown["event"] = dict(event_delta)
        self._apply(base, event_delta)

        # 3) MİKRO SİNYAL
        micro_delta = {
            "valence": micro_score * 3,
            "arousal": micro_score * 1,
            "physical_comfort": micro_score * 7,
            "environmental_calm": micro_score * 2,
            "emotional_intensity": micro_score * -1,
        }
        breakdown["micro"] = dict(micro_delta)
        self._apply(base, micro_delta)

        # 4) BAĞLAM
        context_delta = {"valence": 0, "arousal": 0, "physical_comfort": 0, "environmental_calm": 0, "emotional_intensity": 0}

        if context.get("is_dark"):
            context_delta["arousal"] -= 3
            context_delta["physical_comfort"] -= 2
            context_delta["environmental_calm"] += 2

        temp = context.get("temperature", 10)
        if temp < 5:
            context_delta["physical_comfort"] -= 5
            context_delta["environmental_calm"] -= 2
        elif temp < 10:
            context_delta["physical_comfort"] -= 3
            context_delta["environmental_calm"] -= 1

        if context.get("day_type") == "weekday":
            context_delta["environmental_calm"] -= 2
            context_delta["emotional_intensity"] += 2

        breakdown["context"] = dict(context_delta)
        self._apply(base, context_delta)

        final = AffectState(
            valence=self._clamp(base.valence),
            arousal=self._clamp(base.arousal),
            physical_comfort=self._clamp(base.physical_comfort),
            environmental_calm=self._clamp(base.environmental_calm),
            emotional_intensity=self._clamp(base.emotional_intensity),
        )

        self.debug.append(f"AffectState: {final}")
        return AffectOutput(state=final, breakdown=breakdown, debug=self.debug)

    def _apply(self, s: AffectState, d: Dict[str, int]) -> None:
        s.valence += d.get("valence", 0)
        s.arousal += d.get("arousal", 0)
        s.physical_comfort += d.get("physical_comfort", 0)
        s.environmental_calm += d.get("environmental_calm", 0)
        s.emotional_intensity += d.get("emotional_intensity", 0)

    def _clamp(self, x: int) -> int:
        return max(0, min(100, int(x)))
