from dataclasses import dataclass
from typing import Dict, List

from agents.emotion_agent import EmotionAgent
from agents.context_agent import ContextAgent
from agents.spotify_agent import SpotifyAgent
from agents.event_agent import EventAgent
from agents.micro_signal_agent import MicroSignalAgent
from agents.affect_vector_agent import AffectVectorAgent, AffectState
from agents.regulation_agent import RegulationAgent, RegulationPlan


@dataclass
class CoordinatorResult:
    final_emotion: str
    affect_state: AffectState
    affect_breakdown: Dict
    regulation: RegulationPlan
    context: Dict
    music: Dict
    micro_activity: str
    debug: List[str]


class CoordinatorAgent:
    def __init__(self):
        self.emotion_agent = EmotionAgent(use_gpu=False)
        self.context_agent = ContextAgent()
        self.event_agent = EventAgent()
        self.micro_agent = MicroSignalAgent()
        self.affect_agent = AffectVectorAgent()
        self.regulation_agent = RegulationAgent()
        self.spotify_agent = SpotifyAgent()

    def process(
        self,
        user_text: str,
        city: str,
        event_text: str | None,
        micro_input: int
    ) -> CoordinatorResult:

        debug: List[str] = []

        # 1️⃣ Emotion
        emo = self.emotion_agent.analyze(user_text)
        debug.extend(emo.debug)

        # 2️⃣ Event
        event = self.event_agent.analyze(event_text)
        debug.extend(event.debug)

        # 3️⃣ Micro signal
        micro_score = self.micro_agent.score(micro_input)
        debug.append(f"Mikro sinyal skoru: {micro_score}")

        # 4️⃣ Context
        context = self.context_agent.collect(city)
        debug.append(f"Context: {context}")

        # 5️⃣ Affect vector
        affect = self.affect_agent.calculate(
            emotion=emo.final_emotion,
            event_type=event.event_type,
            event_intensity=event.intensity,
            micro_score=micro_score,
            context=context
        )
        debug.extend(affect.debug)

        # 6️⃣ Regulation
        regulation = self.regulation_agent.plan(affect.state)
        debug.extend(regulation.debug)

        # 7️⃣ Music
        music = self.spotify_agent.recommend(
            emotion=emo.final_emotion,
            state=affect.state,
            plan=regulation
        )

        # 8️⃣ MICRO ACTIVITY
        micro_activity = self._micro_activity(
            emo.final_emotion,
            regulation
        )

        return CoordinatorResult(
            final_emotion=emo.final_emotion,
            affect_state=affect.state,
            affect_breakdown=affect.breakdown,
            regulation=regulation,
            context=context,
            music=music,
            micro_activity=micro_activity,
            debug=debug
        )

    # ================= MICRO ACTIVITY =================
    def _micro_activity(
        self,
        emotion: str,
        regulation: RegulationPlan
    ) -> str:

        d = regulation.delta

        if d["arousal"] <= -10:
            return "2 dakika yavaş nefes egzersizi (4–6)."

        if d["environmental_calm"] >= 10:
            return "Telefonu sessize alıp kısa bir mola ver."

        return {
            "öfke": "5 dakika tempolu yürüyüş + derin nefes",
            "hüzün": "Sıcak bir içecek al ve kısa yazı molası ver",
            "korku": "4–6 nefes egzersizi",
            "şaşkınlık": "10 dakikalık kısa yürüyüş",
            "mutluluk": "Sevdiğin birine kısa mesaj at",
            "nötr": "2 dakika gözlerini dinlendir",
        }.get(emotion, "Kısa mola ver")
