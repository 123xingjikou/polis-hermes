"""
Sales Promotion CLI
====================

Command-line entry point for the sales promotion agent.
Invoked by GitHub Actions workflows and manual runs.

Usage:
    python -m monetization.sales.run promote --platform twitter --action post
    python -m monetization.sales.run report --days 7
    python -m monetization.sales.run calendar --days 14
    python -m monetization.sales.run dry-run --platform reddit --action post
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

from monetization.sales.agent import create_sales_agent
from monetization.sales.analytics import AnalyticsTracker
from monetization.sales.content_generator import ContentGenerator
from monetization.sales.credentials import validate_credentials
from monetization.sales.models import DateRange
from monetization.sales.publisher import SocialPublisher


async def cmd_promote(args: argparse.Namespace) -> int:
    """Execute a promotion action on the specified platform."""
    platform = args.platform
    action = args.action
    dry_run = args.dry_run

    if not dry_run and not validate_credentials(platform):
        print(f"[ERROR] Missing credentials for {platform}. Set environment variables or use --dry-run.")
        return 1

    agent = create_sales_agent(dry_run=dry_run)

    if action == "post":
        if "generate_content" not in agent.capabilities or "publish_post" not in agent.capabilities:
            print("[ERROR] Agent missing required capabilities for posting.")
            return 1

        content_type = "engagement"
        topic = "autonomous AI agents"

        gen_result = await agent.execute({
            "capability": "generate_content",
            "args": {"platform": platform, "content_type": content_type, "topic": topic},
        })

        if gen_result.get("status") != "ok":
            print(f"[FAIL] Content generation failed: {gen_result.get('message', 'unknown')}")
            return 1

        content_data = gen_result.get("content", {})
        print(f"[OK] Generated {content_type} content for {platform}")
        print(f"Title: {content_data.get('title', '')}")
        print(f"Body:  {content_data.get('body', '')[:100]}...")

        pub_result = await agent.execute({
            "capability": "publish_post",
            "args": {"content": content_data},
        })

        if pub_result.get("status") == "ok":
            pub_data = pub_result.get("result", {})
            print(f"[OK] Published to {platform} {'(dry-run)' if dry_run else ''}")
            if pub_data.get("url"):
                print(f"URL: {pub_data['url']}")
            return 0
        else:
            print(f"[FAIL] Publish failed: {pub_result.get('result', {}).get('error', 'unknown')}")
            return 1

    elif action == "interact":
        if "interact" not in agent.capabilities:
            print("[ERROR] Agent missing interact capability.")
            return 1

        result = await agent.execute({
            "capability": "interact",
            "args": {"platform": platform, "post_id": ""},
        })

        if result.get("status") == "ok":
            print(f"[OK] Interaction on {platform} {'(dry-run)' if dry_run else ''}")
            return 0
        else:
            print(f"[FAIL] Interaction on {platform}: {result.get('result', {}).get('error', 'unknown')}")
            return 1

    elif action == "report":
        return await cmd_report(args)

    else:
        print(f"[ERROR] Unknown action: {action}")
        return 1


async def cmd_report(args: argparse.Namespace) -> int:
    """Generate an analytics report for the specified period."""
    days = args.days
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    tracker = AnalyticsTracker()
    report = await tracker.generate_report(DateRange(start=start, end=end))

    print(f"\n{'='*50}")
    print(f"Sales Promotion Report (last {days} days)")
    print(f"{'='*50}")
    print(f"Total Posts:        {report.total_posts}")
    print(f"Publish Success:    {report.success_rate:.1%}")
    print(f"Total Interactions: {report.total_interactions}")
    print(f"\nPlatform Breakdown:")
    for platform, count in report.platform_breakdown.items():
        print(f"  {platform:12s} {count}")
    print(f"\nContent Performance:")
    for content_type, stats in report.content_performance.items():
        print(f"  {content_type:12s} {stats}")
    print(f"{'='*50}\n")

    return 0


async def cmd_calendar(args: argparse.Namespace) -> int:
    """Generate a content calendar for the specified number of days."""
    days = args.days
    platform = args.platform

    generator = ContentGenerator(llm_capability=None)
    calendar = await generator.generate_calendar(days=days, platform=platform)

    print(f"\n{'='*60}")
    print(f"Content Calendar ({days} days, platform: {platform or 'all'})")
    print(f"{'='*60}")
    for i, content in enumerate(calendar, 1):
        print(f"\n--- Post {i} ---")
        print(f"Platform: {content.platform}")
        print(f"Type:     {content.content_type}")
        print(f"Title:    {content.title}")
        print(f"Body:     {content.body[:100]}...")
    print(f"\n{'='*60}\n")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="monetization.sales.run",
        description="Sales Promotion Agent CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # promote command
    promote_parser = subparsers.add_parser("promote", help="Run a promotion action")
    promote_parser.add_argument(
        "--platform",
        required=True,
        choices=["twitter", "reddit", "hn"],
        help="Target platform",
    )
    promote_parser.add_argument(
        "--action",
        required=True,
        choices=["post", "interact", "report"],
        help="Action to perform",
    )
    promote_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without actually posting",
    )

    # report command
    report_parser = subparsers.add_parser("report", help="Generate analytics report")
    report_parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to report on (default: 7)",
    )

    # calendar command
    calendar_parser = subparsers.add_parser("calendar", help="Generate content calendar")
    calendar_parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to generate (default: 7)",
    )
    calendar_parser.add_argument(
        "--platform",
        default=None,
        choices=["twitter", "reddit", "hn"],
        help="Filter by platform",
    )

    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    if not args.command:
        print("No command specified. Use --help for usage information.")
        return 1

    if args.command == "promote":
        return await cmd_promote(args)
    elif args.command == "report":
        return await cmd_report(args)
    elif args.command == "calendar":
        return await cmd_calendar(args)
    else:
        print(f"[ERROR] Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
