import json
import random
import re
from typing import Dict


class LLMCapability:
    """LLM 能力调用 + fallback 规则引擎。

    有 OPENAI_API_KEY 时真实调用 LLM，否则退化为基于人格和需求的规则决策。
    """

    def __init__(self) -> None:
        self.mode = "fallback"
        self.client = None
        try:
            import openai
            self.client = openai.OpenAI()
            self.mode = "real"
        except Exception:
            self.mode = "fallback"

    async def execute(self, context: Dict) -> Dict:
        if self.mode == "real":
            return await self._call_openai(context)
        else:
            return self._fallback_rule(context)

    async def _call_openai(self, context: Dict) -> Dict:
        prompt = self._build_prompt(context)
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            return self._parse_response(content)
        except Exception as e:
            return {"capability": "idle", "args": {}, "error": str(e)}

    def _build_prompt(self, context: Dict) -> str:
        personality = context.get("personality", {})
        memory = context.get("recent_memory", [])
        needs = context.get("needs", {})
        available_caps = context.get("capabilities", [])
        others = context.get("other_residents", [])
        name = context.get("name", "agent")
        prompt = (
            f"You are {name}, an agent living in a virtual city.\n"
            f"Personality: {json.dumps(personality, ensure_ascii=False)}\n"
            f"Current needs: {json.dumps(needs, ensure_ascii=False)}\n"
            f"Recent memories: {json.dumps(memory[-5:], ensure_ascii=False)}\n"
            f"Other residents you can interact with: {json.dumps(others, ensure_ascii=False)}\n"
            f"Available capabilities: {json.dumps(available_caps, ensure_ascii=False)}\n"
            f"Choose ONE action you want to take right now. "
            f"Respond strictly in JSON format:\n"
            f'{{"capability": "<action_name>", "args": {{"target": "...", "message": "..."}}}}'
        )
        return prompt

    def _parse_response(self, text: str) -> Dict:
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if "capability" in data and "args" in data:
                    return data
        except Exception:
            pass
        return {"capability": "idle", "args": {}}

    def _fallback_rule(self, context: Dict) -> Dict:
        """规则引擎：根据人格参数 + 需求优先级产生差异化行为。"""
        needs = context.get("needs", {})
        personality = context.get("personality", {})
        available_caps = context.get("capabilities", [])
        others = context.get("other_residents", [])
        name = context.get("name", "agent")

        social = needs.get("social", 100)
        hunger = needs.get("hunger", 100)
        energy = needs.get("energy", 100)
        fun = needs.get("fun", 100)

        openness = personality.get("openness", 0.5)
        aggression = personality.get("aggressiveness", 0.5)
        confidence = personality.get("confidence", 0.5)

        candidates = []

        if hunger < 80 and "eat" in available_caps:
            candidates.append(("eat", {"food": "bread"}, (100 - hunger) * 1.5))

        if energy < 60 and "rest" in available_caps:
            candidates.append(("rest", {}, (100 - energy) * 1.2))

        if social < 80 and "talk" in available_caps and others:
            target = random.choice(others)
            msg_greetings = [
                f"Hey {target}, what do you think about the weather?",
                f"Hi {target}, how's your day going?",
                f"{target}, I've been thinking about life lately.",
                f"Hey {target}, want to chat?",
            ]
            msg = random.choice(msg_greetings)
            talk_score = (100 - social) * openness
            candidates.append(("talk", {"target": target, "message": msg}, talk_score))

        if fun < 70 and "idle" in available_caps:
            candidates.append(("idle", {}, (100 - fun) * 0.5))

        if "work" in available_caps:
            work_base = 20 + aggression * 25 - confidence * 5
            candidates.append(("work", {}, work_base))

        if "autogen_chat" in available_caps and others and openness > 0.5:
            target = random.choice(others)
            candidates.append(("autogen_chat", {"sender": name, "message": f"Hello {target}!"}, 15 * openness))

        if "mcp" in available_caps and energy > 40:
            candidates.append(("mcp", {"tool_name": "search", "args": {"query": "city news"}}, 10 * aggression))

        if "subprocess" in available_caps and energy > 50:
            candidates.append(("subprocess", {"command": "echo hello"}, 8 * aggression))

        if not candidates:
            return {"capability": "idle", "args": {}}

        candidates.sort(key=lambda x: x[2], reverse=True)
        best = candidates[0]

        if len(candidates) > 1 and random.random() < 0.3:
            best = candidates[1]

        return {"capability": best[0], "args": best[1]}
