import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.loop import CityLoop
from residents.factory import create_autogen_resident, create_standard_resident, create_tool_resident
from capabilities.autogen_impl import AUTOGEN_AVAILABLE, AUTOGEN_API_VERSION


async def main():
    print(f"AutoGen available: {AUTOGEN_AVAILABLE}")
    print(f"AutoGen API version: {AUTOGEN_API_VERSION}")
    print(f"OpenAI API Key set: {bool(os.environ.get('OPENAI_API_KEY'))}")
    print()

    alice = create_autogen_resident(
        "Alice",
        personality={"confidence": 0.8, "openness": 0.7, "aggressiveness": 0.2},
        skills={"debate": 0.9},
        system_message="You are Alice, a friendly debater. You enjoy talking about philosophy.",
    )

    bob = create_standard_resident(
        "Bob",
        personality={"confidence": 0.5, "openness": 0.9, "aggressiveness": 0.1},
        skills={"cooking": 0.8},
    )

    charlie = create_tool_resident(
        "Charlie",
        personality={"confidence": 0.4, "openness": 0.6, "aggressiveness": 0.7},
        skills={"tools": 0.8},
    )

    diana = create_autogen_resident(
        "Diana",
        personality={"confidence": 0.9, "openness": 0.4, "aggressiveness": 0.3},
        skills={"governance": 0.9},
        system_message="You are Diana, a pragmatic leader who values efficiency.",
    )

    residents = [alice, bob, charlie, diana]
    loop = CityLoop(residents, tick_interval=0, election_interval=5)

    print("=== Pre-simulation capability probe ===")
    for r in residents:
        print(f"  {r.name}: capabilities={list(r.capabilities.keys())}")
        if hasattr(r, "has_autogen"):
            print(f"    has_autogen={r.has_autogen}, api_version={r.api_version}")

    print()
    print("=== Testing autogen_chat capability (Bob -> Alice) ===")
    result = await alice.handle_autogen_chat(
        context={"sender": "Bob", "message": "Hello Alice, how are you?"}
    )
    print(f"  Result: {result}")
    print()

    await loop.run(max_ticks=10)


if __name__ == "__main__":
    asyncio.run(main())
