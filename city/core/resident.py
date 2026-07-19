from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
import time


@dataclass
class MemoryItem:
    content: str
    timestamp: float
    importance: float = 0.5


class MemoryBuffer:
    def __init__(self, short_term_limit: int = 50, long_term_limit: int = 15):
        self.short_term: List[MemoryItem] = []
        self.long_term: List[MemoryItem] = []
        self.st_limit = short_term_limit
        self.lt_limit = long_term_limit

    def add(self, content: str, importance: float = 0.5) -> None:
        item = MemoryItem(content, time.time(), importance)
        self.short_term.append(item)
        if len(self.short_term) > self.st_limit:
            self.short_term.pop(0)

    def summarize(self) -> None:
        """将短期记忆提炼为长期记忆（简化：取高重要性条目）"""
        if len(self.short_term) >= 5:
            high = [m for m in self.short_term if m.importance > 0.7]
            self.long_term.extend(high)
            self.short_term = self.short_term[-10:]
            if len(self.long_term) > self.lt_limit:
                self.long_term = self.long_term[-self.lt_limit:]


class CityResident:
    def __init__(
        self,
        name: str,
        personality: Dict[str, float],
        skills: Dict[str, float],
        role: str = "member",
        coins: int = 100,
    ):
        self.name = name
        self.personality = personality
        self.skills = skills
        self.role = role
        self.coins = coins
        self.memory = MemoryBuffer()
        self.relationships: Dict[str, float] = {}
        self.needs = {"energy": 100, "social": 100, "fun": 100, "hunger": 100}
        self.capabilities: Dict[str, Callable] = {}

    async def decide(self, context: dict) -> dict:
        """生成行动描述。

        优先查找自身 capabilities 中的 "decide" 能力函数；
        如果未找到，则由子类重写此方法。
        """
        decide_fn = self.capabilities.get("decide")
        if decide_fn:
            return await decide_fn(context)
        raise NotImplementedError(
            f"{type(self).__name__}({self.name}) has no 'decide' capability and "
            f"does not override decide()"
        )

    async def execute(self, action: dict) -> dict:
        """调用对应能力函数执行行动"""
        capability = action.get("capability")
        if capability and capability in self.capabilities:
            func = self.capabilities[capability]
            return await func(context=action.get("args", {}))
        return {"status": "error", "message": f"Capability {capability} not found"}

    def change_relationship(self, other_name: str, delta: float) -> None:
        current = self.relationships.get(other_name, 0)
        self.relationships[other_name] = max(-100, min(100, current + delta))

    def __repr__(self) -> str:
        return (
            f"CityResident(name={self.name!r}, role={self.role!r}, "
            f"coins={self.coins}, needs={self.needs})"
        )
