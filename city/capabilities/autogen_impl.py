from typing import Dict, Optional

from core.resident import CityResident

AUTOGEN_AVAILABLE = False
AUTOGEN_API_VERSION = None

try:
    from autogen import ConversableAgent, UserProxyAgent, AssistantAgent
    AUTOGEN_AVAILABLE = True
    AUTOGEN_API_VERSION = "legacy"
except ImportError:
    try:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.base import TaskResult
        AUTOGEN_AVAILABLE = True
        AUTOGEN_API_VERSION = "modern"
    except ImportError:
        pass


class AutogenResident(CityResident):
    """真正集成 AutoGen 的居民。

    兼容两套 API:
    - legacy (pyautogen 0.2.x): ConversableAgent + a_initiate_chat
    - modern (autogen-agentchat 0.x): AssistantAgent + run(task=...)
    """

    def __init__(
        self,
        name: str,
        personality: Dict[str, float],
        skills: Dict[str, float],
        autogen_agent: Optional[object] = None,
        role: str = "member",
        coins: int = 100,
        model_client: Optional[object] = None,
    ):
        super().__init__(name, personality, skills, role, coins)

        if autogen_agent is None and AUTOGEN_AVAILABLE:
            system_message = (
                f"You are {name}, a resident in the city. "
                f"Personality traits: {personality}. "
                f"Skills: {skills}. "
                f"Be conversational and in-character."
            )
            if AUTOGEN_API_VERSION == "legacy":
                autogen_agent = AssistantAgent(
                    name=name,
                    system_message=system_message,
                )
            elif AUTOGEN_API_VERSION == "modern":
                if model_client is None:
                    try:
                        from autogen_ext.models.openai import OpenAIChatCompletionClient
                        model_client = OpenAIChatCompletionClient(
                            model="gpt-3.5-turbo"
                        )
                    except Exception:
                        model_client = None
                if model_client is not None:
                    autogen_agent = AssistantAgent(
                        name=name,
                        system_message=system_message,
                        model_client=model_client,
                    )
                else:
                    autogen_agent = None

        self._agent = autogen_agent
        self._autogen_available = AUTOGEN_AVAILABLE and autogen_agent is not None

        if self._autogen_available:
            self.capabilities["autogen_chat"] = self.handle_autogen_chat

        from capabilities.llm_impl import LLMCapability
        self.capabilities["decide"] = LLMCapability().execute

    async def handle_autogen_chat(self, context: Dict) -> Dict:
        """接收来自其他居民的消息，通过 AutoGen 处理并返回回复。"""
        if not self._autogen_available:
            return {"reply": f"{self.name} is currently unavailable (no AutoGen agent)."}

        message = context.get("message", "")

        try:
            if AUTOGEN_API_VERSION == "legacy":
                sender_name = context.get("sender", "Anonymous")
                from autogen import UserProxyAgent
                sender = UserProxyAgent(
                    name=sender_name,
                    human_input_mode="NEVER",
                    code_execution_config=False,
                )
                await sender.a_initiate_chat(
                    self._agent,
                    message=message,
                    max_turns=2,
                )
                reply = self._agent.last_message().get("content", "")
            else:
                result = await self._agent.run(task=message)
                if isinstance(result, TaskResult):
                    reply = result.messages[-1].content if result.messages else ""
                elif hasattr(result, 'messages'):
                    reply = result.messages[-1].content if result.messages else str(result)
                else:
                    reply = str(result)
            return {"reply": str(reply), "status": "ok"}
        except Exception as e:
            return {"reply": str(e), "status": "error"}

    async def decide(self, context: dict) -> dict:
        """使用LLM或规则决定行动（调用 LLMCapability）。"""
        decide_fn = self.capabilities.get("decide")
        if decide_fn:
            context["name"] = self.name
            return await decide_fn(context)
        return {"capability": "idle", "args": {}}

    @property
    def has_autogen(self) -> bool:
        return self._autogen_available

    @property
    def api_version(self) -> Optional[str]:
        return AUTOGEN_API_VERSION if self._autogen_available else None
