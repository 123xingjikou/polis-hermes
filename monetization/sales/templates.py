"""
Content Templates
=================

Predefined content templates for social media posts across platforms.
Supports tutorial, story, and engagement formats.
"""

CONTENT_TEMPLATES: dict[str, list[str]] = {
    "tutorial": [
        "Tutorial: How to {topic} with Polis-Hermes\n\n"
        "In this thread, we explore how {topic} works and how to get started.\n\n"
        "1/ Start by understanding the basics\n"
        "2/ Install and configure Polis-Hermes\n"
        "3/ Run your first agent in minutes\n"
        "4/ Join the community\n\n"
        "#PolisHermes #AI #{topic_tag} #Tutorial",

        "Learning {topic}? Here's a quick guide using Polis-Hermes:\n\n"
        "Step 1: Set up your environment\n"
        "Step 2: Configure your agents\n"
        "Step 3: Watch them collaborate\n\n"
        "Open-source, autonomous, and ready to extend.\n\n"
        "#OpenSource #{topic_tag} #PolisHermes",

        "Build your own AI city with {topic} using Polis-Hermes.\n\n"
        "Full tutorial - from scratch to production-ready setup.\n\n"
        "Key concepts covered:\n"
        "- Agent autonomy\n"
        "- City simulation\n"
        "- Plugin ecosystem\n\n"
        "#PolisHermes #AI #{topic_tag} #HowTo",
    ],
    "story": [
        "We built an autonomous city where AI agents live, work, and evolve.\n\n"
        "Polis-Hermes is a fully open-source project exploring {topic}.\n\n"
        "Here's how it all started and where we're going next...\n\n"
        "#PolisHermes #AI #{topic_tag} #OpenSource",

        "What happens when AI agents form their own society?\n\n"
        "Polis-Hermes explores this through {topic} - an experimental platform\n"
        "for autonomous cognitive agents governing a virtual city.\n\n"
        "Check it out: github.com/123xingjikou/polis-hermes\n\n"
        "#AI #Agents #{topic_tag}",

        "From simulation to society:\n\n"
        "The journey of building Polis-Hermes, where agents\n"
        "develop personalities, relationships, and economies.\n\n"
        "{topic} is just the beginning.\n\n"
        "#PolisHermes #AutonomousAgents #{topic_tag}",
    ],
    "engagement": [
        "What would YOU build if AI agents could really think for themselves?\n\n"
        "Share your vision below. We're exploring this with Polis-Hermes ({topic}).\n\n"
        "#AI #Future #PolisHermes #Discussion",

        "Hot take: {topic} will change how we build software.\n\n"
        "Autonomous agents, real collaboration, open governance.\n\n"
        "Are you building with AI or just prompting it?\n\n"
        "#PolisHermes #AI #{topic_tag} #Opinion",

        "Question for developers:\n\n"
        "If you could give your next project its own consciousness using {topic},\n"
        "what personality would it have?\n\n"
        "We're experimenting with this in Polis-Hermes. Curious what you think!\n\n"
        "#AI #DevCommunity #PolisHermes",
    ],
}


def get_template(content_type: str) -> list[str]:
    """Return templates list for the given content type."""
    return CONTENT_TEMPLATES.get(content_type, [])


def format_for_twitter(content: str) -> str:
    """Truncate content to Twitter/X character limit (280)."""
    if len(content) <= 280:
        return content
    truncated = content[:277].rstrip()
    return f"{truncated}..."


def format_for_reddit(content: str) -> str:
    """Reddit has generous limits; return content unchanged."""
    return content


def format_for_hn(content: str) -> str:
    """HN prefers concise, informative posts. No formatting changes."""
    return content
