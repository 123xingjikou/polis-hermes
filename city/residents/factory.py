from core.resident import CityResident
from capabilities.autogen_impl import AutogenResident, AUTOGEN_AVAILABLE, AUTOGEN_API_VERSION
from capabilities.llm_impl import LLMCapability
from capabilities.tool_impl import MockMCPCapability, SubprocessCapability


async def _talk_capability(context: dict) -> dict:
    target = context.get("target", "someone")
    msg = context.get("message", "Hello")
    return {"action": "talk", "to": target, "message": msg, "reply": f"{target} says: {msg} back!"}


def create_autogen_resident(
    name: str,
    personality: dict,
    skills: dict,
    system_message: str = None,
) -> AutogenResident:
    """创建一个使用 AutoGen 的居民。

    如果 autogen 并未安装，则降级为使用 LLM 决策的 AutogenResident
    （没有内部 autogen agent，但保留能力接口）。
    """
    return AutogenResident(
        name=name,
        personality=personality,
        skills=skills,
        autogen_agent=None,
    )


def create_standard_resident(
    name: str,
    personality: dict,
    skills: dict,
) -> CityResident:
    """创建一个使用 LLM 决定能力的普通居民。

    无 API key 时退化为规则引擎。
    """
    r = CityResident(name, personality, skills)
    llm = LLMCapability()
    r.capabilities["decide"] = llm.execute
    r.capabilities["talk"] = _talk_capability
    return r


def create_tool_resident(
    name: str,
    personality: dict,
    skills: dict,
) -> CityResident:
    """创建一个带有模拟 MCP 工具能力的居民。"""
    r = CityResident(name, personality, skills)
    llm = LLMCapability()
    r.capabilities["decide"] = llm.execute
    r.capabilities["mcp"] = MockMCPCapability().execute
    r.capabilities["subprocess"] = SubprocessCapability().execute
    return r
