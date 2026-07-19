import asyncio
import random
import time
from typing import List, Optional

from core.state import CityState
from core.resident import CityResident
from capabilities.governance_impl import Governance


SIMPLE_CAPABILITIES = {}


def _register_simple_cap(name: str):
    """注册一个简单的同步能力函数（转换为异步）。"""
    def decorator(func):
        async def wrapper(context):
            return func(context)
        SIMPLE_CAPABILITIES[name] = wrapper
        return func
    return decorator


@_register_simple_cap("eat")
def _eat_cap(context: dict) -> dict:
    food = context.get("food", "bread")
    hunger_restore = 20
    return {"action": "eat", "food": food, "hunger_restore": hunger_restore,
            "message": f"Ate {food}, hunger reduced by {hunger_restore}."}


@_register_simple_cap("rest")
def _rest_cap(context: dict) -> dict:
    energy_restore = 25
    return {"action": "rest", "energy_restore": energy_restore,
            "message": f"Rested, energy restored by {energy_restore}."}


@_register_simple_cap("talk")
def _talk_cap(context: dict) -> dict:
    target = context.get("target", "someone")
    msg = context.get("message", "Hello")
    return {"action": "talk", "to": target, "message": msg,
            "reply": f"{target} acknowledges: '{msg[:20]}...'"}


@_register_simple_cap("work")
def _work_cap(context: dict) -> dict:
    base_income = 5
    return {"action": "work", "income": base_income,
            "message": f"Worked, earned {base_income} coins."}


@_register_simple_cap("idle")
def _idle_cap(context: dict) -> dict:
    fun_restore = 5
    return {"action": "idle", "fun_restore": fun_restore,
            "message": f"Rested idly, fun +{fun_restore}."}


class CityLoop:
    def __init__(
        self,
        residents: List[CityResident],
        tick_interval: float = 3,
        db_path: str = "city_state.db",
        election_interval: int = 10,
    ):
        self.residents = {r.name: r for r in residents}
        self.state = CityState(db_path)
        self.governance = Governance(residents)
        self.tick = 0
        self.interval = tick_interval
        self.election_interval = election_interval

        for r in residents:
            for cap_name, func in SIMPLE_CAPABILITIES.items():
                if cap_name not in r.capabilities:
                    r.capabilities[cap_name] = func

    async def run(self, max_ticks: int = 10) -> None:
        print(f"\n{'='*70}")
        print(f"City simulation starting with {len(self.residents)} residents.")
        print(f"{'='*70}")
        for name, r in self.residents.items():
            caps = list(r.capabilities.keys())
            print(f"  {name:10s} | role={r.role:10s} | agg={r.personality.get('aggressiveness', 0):.1f} "
                  f"ope={r.personality.get('openness', 0):.1f} con={r.personality.get('confidence', 0):.1f}")
            print(f"{'':12s} caps={caps}")
        print(f"{'='*70}\n")

        for _ in range(max_ticks):
            await self._single_tick()

        self.state.close()
        print(f"\n{'='*70}")
        print(f"Simulation ended at tick {self.tick}.")
        self._print_summary()
        print(f"{'='*70}")

    async def _single_tick(self) -> None:
        print(f"\n--- Tick {self.tick} ---")

        for r in self.residents.values():
            aggression = r.personality.get("aggressiveness", 0.5)
            openness = r.personality.get("openness", 0.5)

            r.needs["energy"] = max(0, r.needs["energy"] - 5 - int(aggression * 3))
            r.needs["fun"] = max(0, r.needs["fun"] - 2 - int(openness * 2))
            r.needs["hunger"] = max(0, r.needs["hunger"] - 3)
            r.needs["social"] = max(0, r.needs["social"] - 4 + int(openness * 2))

        if self.tick > 0 and self.tick % self.election_interval == 0:
            mayor = self.governance.election(strategy="wealthiest")
            print(f"  [GOVERNANCE] Election! New mayor: {mayor.name}")
            self.state.add_event(self.tick, f"Election: {mayor.name}")

        if self.governance.mayor and self.tick % (self.election_interval * 2) == 0 and self.tick > 0:
            decision = self.governance.mayor_decision(tax=5)
            print(f"  [GOVERNANCE] {decision}")
            self.state.add_event(self.tick, decision)

        for r in self.residents.values():
            context = {
                "name": r.name,
                "personality": r.personality,
                "needs": r.needs,
                "recent_memory": [m.content for m in r.memory.short_term[-5:]],
                "other_residents": [n for n in self.residents if n != r.name],
                "capabilities": list(r.capabilities.keys()),
            }
            action = await r.decide(context)
            print(f"  {r.name:10s} decides: {action}")
            result = await r.execute(action)
            print(f"  {r.name:10s} result : {result}")

            if action.get("capability") == "eat":
                r.needs["hunger"] = min(100, r.needs["hunger"] + result.get("hunger_restore", 0))
            elif action.get("capability") == "rest":
                r.needs["energy"] = min(100, r.needs["energy"] + result.get("energy_restore", 0))
            elif action.get("capability") == "idle":
                r.needs["fun"] = min(100, r.needs["fun"] + result.get("fun_restore", 0))
            elif action.get("capability") == "work":
                r.coins += result.get("income", 0)

            r.memory.add(
                f"Tick {self.tick}: took {action.get('capability')} -> {result.get('message', '')}",
                importance=0.6,
            )

            if action.get("capability") == "talk":
                target = action.get("args", {}).get("target")
                if target and target in self.residents:
                    r.needs["social"] = min(100, r.needs["social"] + 5)
                    self.residents[target].needs["social"] = min(100, self.residents[target].needs["social"] + 3)
                    r.change_relationship(target, +2)
                    self.residents[target].change_relationship(r.name, +1)
                    print(f"  [SOCIAL] {r.name} <-> {target}: relationship +2/+1")

        for r in self.residents.values():
            r.memory.summarize()

        for r in self.residents.values():
            self.state.save_resident(r)

        for r in self.residents.values():
            r.coins += 10

        self.tick += 1
        if self.interval > 0:
            await asyncio.sleep(self.interval)

    def _print_summary(self) -> None:
        print("Final resident states:")
        for name, r in self.residents.items():
            print(
                f"  {name:10s} | coins={r.coins:4d} | "
                f"energy={r.needs['energy']:3d} social={r.needs['social']:3d} "
                f"fun={r.needs['fun']:3d} hunger={r.needs['hunger']:3d} | "
                f"relationships={r.relationships}"
            )
        if self.governance.mayor:
            print(f"Current mayor: {self.governance.mayor.name}")
        print(f"Treasury: {self.governance.treasury}")
