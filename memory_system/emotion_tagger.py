"""
Emotion tagger: sentiment analysis and emotional labeling for memories.

Provides both rule-based tagging (no external dependencies) and an extensible
interface for pluggable sentiment models. Supports the 8 basic emotions from
Plutchik's wheel: joy, sadness, anger, fear, surprise, disgust, trust,
anticipation.
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

from .base import MemoryItem, MemoryStage, MemoryType


class EmotionTagger:
    EMOTION_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        "joy": [
            "开心", "快乐", "高兴", "喜悦", "兴奋", "愉快", "欢乐", "笑",
            "happy", "joy", "glad", "excited", "delight", "cheerful", "elated",
            "成功", "成就", "胜利", "获奖", "庆祝", "满足", "幸福", "收获满满",
            "success", "achievement", "win", "celebrate", "satisfaction",
        ],
        "sadness": [
            "伤心", "难过", "失望", "悲伤", "沮丧", "遗憾", "痛苦", "哭",
            "sad", "disappoint", "sorrow", "grief", "depress", "regret", "pain",
            "失败", "失去", "分离", "孤独", "绝望",
            "fail", "loss", "lonely", "hopeless",
        ],
        "anger": [
            "生气", "愤怒", "恼火", "怒", "愤", "烦躁", "暴怒",
            "angry", "anger", "furious", "rage", "annoyed", "irritate",
            "不公", "抗议", "仇恨",
            "unfair", "hate", "resent",
        ],
        "fear": [
            "害怕", "恐惧", "担心", "焦虑", "紧张", "恐慌", "吓",
            "fear", "afraid", "anxiety", "worry", "panic", "scared", "nervous",
            "危险", "威胁", "不确定",
            "danger", "threat", "uncertain",
        ],
        "surprise": [
            "惊讶", "震惊", "意外", "吃惊", "没想到", "居然",
            "surprise", "shock", "amaze", "unexpected", "astonish", "wow",
            "竟然", "忽然", "突然",
            "suddenly", "unexpectedly",
        ],
        "disgust": [
            "厌恶", "恶心", "反感", "嫌弃", "讨厌",
            "disgust", "revolt", "repulse", "sick", "hate",
            "糟糕", "恶劣", "肮脏",
            "terrible", "awful", "dirty",
        ],
        "trust": [
            "信任", "相信", "可靠", "放心", "安心", "信赖",
            "trust", "believe", "reliable", "confide", "depend",
            "合作", "友谊", "忠诚",
            "cooperate", "friend", "loyal",
        ],
        "anticipation": [
            "期待", "盼望", "希望", "展望", "计划", "准备",
            "anticipate", "expect", "hope", "plan", "prepare", "look forward",
            "未来", "目标", "愿景",
            "future", "goal", "vision",
        ],
    }

    def __init__(self, custom_keywords: dict[str, list[str]] | None = None):
        self.keywords = dict(self.EMOTION_KEYWORDS)
        if custom_keywords:
            for emotion, words in custom_keywords.items():
                if emotion in self.keywords:
                    self.keywords[emotion] = list(set(self.keywords[emotion] + words))
                else:
                    self.keywords[emotion] = words

    def tag(self, text: str) -> dict[str, Any]:
        if not text:
            return self._empty_result()

        text_lower = text.lower()
        scores: dict[str, float] = {}
        matched_keywords: dict[str, list[str]] = {}

        for emotion, keywords in self.keywords.items():
            score = 0.0
            matched: list[str] = []
            for kw in keywords:
                count = len(re.findall(re.escape(kw), text_lower))
                if count > 0:
                    score += count * (len(kw) / max(len(text), 1)) * 10
                    matched.append(kw)
            if score > 0:
                scores[emotion] = min(1.0, score)
                matched_keywords[emotion] = matched

        if not scores:
            result: dict[str, Any] = {
                "primary_emotion": "neutral",
                "intensity": 0.1,
                "valence": 0.0,
                "arousal": 0.1,
            }
            for emotion in self.keywords:
                result[emotion] = 0.05
            result["scores"] = dict.fromkeys(self.keywords, 0.05)
            return result

        primary = max(scores, key=scores.get)
        intensity = scores[primary]
        valence = self._compute_valence(scores)
        arousal = self._compute_arousal(scores)

        all_scores = {e: scores.get(e, 0.05) for e in self.keywords}

        result: dict[str, Any] = {
            "primary_emotion": primary,
            "intensity": round(intensity, 3),
            "valence": round(valence, 3),
            "arousal": round(arousal, 3),
            "matched_keywords": matched_keywords,
        }
        for k, v in all_scores.items():
            result[k] = round(v, 3)
        result["scores"] = {k: round(v, 3) for k, v in all_scores.items()}
        return result

    def batch_tag(self, texts: list[str]) -> list[dict[str, Any]]:
        return [self.tag(t) for t in texts]

    def _empty_result(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "primary_emotion": "neutral",
            "intensity": 0.0,
            "valence": 0.0,
            "arousal": 0.0,
        }
        for emotion in self.keywords:
            result[emotion] = 0.0
        result["scores"] = dict.fromkeys(self.keywords, 0.0)
        return result

    @staticmethod
    def _compute_valence(scores: dict[str, float]) -> float:
        positive = scores.get("joy", 0.0) + scores.get("trust", 0.0) + scores.get("anticipation", 0.0) * 0.5
        negative = (
            scores.get("sadness", 0.0)
            + scores.get("anger", 0.0)
            + scores.get("fear", 0.0)
            + scores.get("disgust", 0.0)
        )
        total = positive + negative
        if total == 0:
            return 0.0
        return (positive - negative) / total

    @staticmethod
    def _compute_arousal(scores: dict[str, float]) -> float:
        high = scores.get("anger", 0.0) + scores.get("fear", 0.0) + scores.get("surprise", 0.0) + scores.get("joy", 0.0) * 0.5
        total = sum(scores.values())
        if total == 0:
            return 0.0
        return high / total


class EmotionalMemory:
    def __init__(self, store: Any, tagger: EmotionTagger | None = None):
        self.store = store
        self.tagger = tagger or EmotionTagger()

    def record(
        self,
        agent_id: str,
        event: str,
        emotion: str | None = None,
        intensity: float | None = None,
        context: str | None = None,
        tags: list[str] | None = None,
    ) -> Any:
        if emotion is None or intensity is None:
            tag_result = self.tagger.tag(event)
            emotion = emotion or tag_result["primary_emotion"]
            intensity = intensity if intensity is not None else tag_result["intensity"]

        item = MemoryItem(
            content=event,
            memory_type=MemoryType.EMOTIONAL,
            agent_id=agent_id,
            stage=MemoryStage.SHORT_TERM,
            emotion=emotion,
            emotion_intensity=intensity,
            context=context,
            tags=tags or [],
            relevance_score=intensity,
            metadata={"emotion_scores": self.tagger.tag(event).get("scores", {})},
        )
        self.store.insert(item)
        return item

    def recall(
        self,
        agent_id: str,
        emotion: str | None = None,
        min_intensity: float = 0.0,
        query: str | None = None,
        limit: int = 20,
    ) -> list[Any]:
        if emotion:
            results = self.store.search_by_emotion(emotion, agent_id, limit=limit * 2)
            results = [r for r in results if r.memory_type == MemoryType.EMOTIONAL]
        elif query:
            results = self.store.search_fulltext(query, agent_id, limit=limit * 2)
            results = [r for r in results if r.memory_type == MemoryType.EMOTIONAL]
        else:
            results = self.store.get_by_agent(
                agent_id, MemoryType.EMOTIONAL, limit=limit * 2
            )

        filtered = [
            r for r in results
            if r.memory_type == MemoryType.EMOTIONAL
            and r.emotion_intensity >= min_intensity
        ]
        filtered.sort(key=lambda x: x.emotion_intensity, reverse=True)
        return filtered[:limit]

    def get_emotional_profile(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        items = self.store.get_by_agent(
            agent_id, MemoryType.EMOTIONAL, limit=limit
        )
        if not items:
            return {"agent_id": agent_id, "dominant_emotion": "neutral", "emotions": {}}

        emotion_counts: dict[str, float] = {}
        for item in items:
            if item.emotion:
                emotion_counts[item.emotion] = emotion_counts.get(item.emotion, 0.0) + item.emotion_intensity

        dominant = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"
        total = sum(emotion_counts.values()) or 1.0

        return {
            "agent_id": agent_id,
            "dominant_emotion": dominant,
            "emotions": {k: round(v / total, 3) for k, v in emotion_counts.items()},
            "sample_count": len(items),
        }

    def count(self, agent_id: str) -> int:
        return self.store.count_by_agent(agent_id, MemoryType.EMOTIONAL)
