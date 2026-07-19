from typing import List, Optional
from core.resident import CityResident


class Governance:
    """选举与经济治理简化实现。"""

    def __init__(self, residents: List[CityResident]):
        self.residents = residents
        self.mayor: Optional[CityResident] = None
        self.term_ticks: int = 0
        self.treasury: int = 0

    def election(self, strategy: str = "random") -> CityResident:
        """执行选举，返回新市长。

        strategy:
            - "random": 随机选择
            - "wealthiest": 选择最富有的居民
            - "social": 选择关系总分最高的居民
        """
        import random
        if not self.residents:
            raise ValueError("No residents to elect from")

        if strategy == "wealthiest":
            self.mayor = max(self.residents, key=lambda r: r.coins)
        elif strategy == "social":
            def social_score(r: CityResident) -> float:
                return sum(r.relationships.values())
            self.mayor = max(self.residents, key=social_score)
        else:
            self.mayor = random.choice(self.residents)

        self.term_ticks = 0
        return self.mayor

    def mayor_decision(self, **kwargs) -> str:
        """市长做出影响全局的决策（简化）。"""
        if self.mayor is None:
            return "No mayor elected."
        tax = kwargs.get("tax", 5)
        for r in self.residents:
            if r.name != self.mayor.name:
                actual_tax = min(tax, r.coins)
                r.coins -= actual_tax
                self.treasury += actual_tax
        return f"Mayor {self.mayor.name} collected tax ({tax} coins), treasury now {self.treasury}"

    def grant_coin(self, name: str, amount: int) -> str:
        for r in self.residents:
            if r.name == name:
                r.coins += amount
                return f"Granted {amount} coins to {name}, now has {r.coins}"
        return f"Resident {name} not found"
