from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

from agents.affect_vector_agent import AffectState

@dataclass
class RegulationTarget:
    valence: int
    arousal: int
    physical_comfort: int
    environmental_calm: int
    emotional_intensity: int


@dataclass
class RegulationPlan:
    target: RegulationTarget
    delta: Dict[str, int]      # target - current
    guidance: List[str]        # doğal dil direktif
    debug: List[str]


class RegulationAgent:
    def __init__(self):
        self.debug: List[str] = []
        self.default_target = RegulationTarget(
            valence=55,
            arousal=50,
            physical_comfort=60,
            environmental_calm=60,
            emotional_intensity=50
        )

    def plan(self, current: AffectState) -> RegulationPlan:
        self.debug = []

        t = self.default_target
        delta = {
            "valence": t.valence - current.valence,
            "arousal": t.arousal - current.arousal,
            "physical_comfort": t.physical_comfort - current.physical_comfort,
            "environmental_calm": t.environmental_calm - current.environmental_calm,
            "emotional_intensity": t.emotional_intensity - current.emotional_intensity,
        }

        guidance = self._guidance_from_delta(delta)

        self.debug.append(f"Target: {t}")
        self.debug.append(f"Delta: {delta}")

        return RegulationPlan(target=t, delta=delta, guidance=guidance, debug=self.debug)

    def _guidance_from_delta(self, d: Dict[str, int]) -> List[str]:
        g: List[str] = []

        if d["valence"] >= 10:
            g.append("Valence yükselt: daha pozitif/umutlu tonlar.")
        elif d["valence"] <= -10:
            g.append("Valence düşür: daha melankolik tonlar (çok ağır değil).")

        if d["arousal"] >= 10:
            g.append("Arousal artır: tempo biraz yüksek, ritmik.")
        elif d["arousal"] <= -10:
            g.append("Arousal azalt: düşük tempo, yumuşak geçişler, sakin.")

        if d["physical_comfort"] >= 10:
            g.append("Physical comfort artır: sıcak/rahatlatıcı tınılar (akustik/lofi/piyano).")

        if d["environmental_calm"] >= 10:
            g.append("Environmental calm artır: ambient/lofi, minimal, güvenli his.")

        if d["emotional_intensity"] <= -10:
            g.append("Emotional intensity azalt: dramatik olmayan, düşük yoğunluk.")
        elif d["emotional_intensity"] >= 10:
            g.append("Emotional intensity artır: duygulu ama kontrol edilebilir.")

        if not g:
            g.append("Genel denge: orta tempo, sakin-pozitif, rahatsız etmeyen seçim.")
        return g

