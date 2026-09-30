"""Find likely polarizing topics among Twitter/X trends using Twikit."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any


SIGNAL_PATTERNS = {
    "elections and politics": (r"\belection\w*\b", r"\bpolitic\w*\b", r"\bpresident\b", r"\bgovernment\b", r"\bcongress\b"),
    "war and international conflict": (r"\bwar\b", r"\binvasion\b", r"\bceasefire\b", r"\bhostage\w*\b", r"\bconflict\b", r"\bmilitary\b", r"\bgenocide\b"),
    "immigration and borders": (r"\bimmigra\w*\b", r"\bmigrant\w*\b", r"\bdeport\w*\b", r"\bborder\w*\b", r"\basylum\b"),
    "rights and identity": (r"\blgbtq?\+?\b", r"\btransgender\b", r"\bgender\b", r"\brace\b", r"\bracis\w*\b", r"\bdiscriminat\w*\b"),
    "reproductive rights": (r"\babortion\b", r"\breproductive\b", r"\bcontraception\b"),
    "religion": (r"\breligio\w*\b", r"\bchurch\b", r"\bfaith\b", r"\bmuslim\w*\b", r"\bchristian\w*\b", r"\bjewish\b"),
    "guns and public safety": (r"\bgun\w*\b", r"\bfirearm\w*\b", r"\bshooting\b", r"\bpolice\b", r"\bpolicing\b"),
    "climate and energy": (r"\bclimate\b", r"\bglobal warming\b", r"\bfossil fuel\w*\b", r"\bnuclear energy\b"),
    "health policy": (r"\bvaccine\w*\b", r"\bmandate\w*\b", r"\bhealthcare\b", r"\bpublic health\b"),
    "speech and media": (r"\bcensorship\b", r"\bfree speech\b", r"\bmisinformation\b", r"\bdisinformation\b", r"\bban\w*\b"),
    "courts and law": (r"\bsupreme court\b", r"\btrial\b", r"\bverdict\b", r"\bindict\w*\b", r"\bconstitution\b"),
    "economics and labor": (r"\binflation\b", r"\btax\w*\b", r"\bunion\w*\b", r"\bstrike\b", r"\bminimum wage\b", r"\bcost of living\b"),
}

COMPILED_SIGNALS = {
    label: tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)
    for label, patterns in SIGNAL_PATTERNS.items()
}


@dataclass(frozen=True)
class Topic:
    name: str
    signals: list[str]
    tweet_count: int | None = None


def find_signals(text: str) -> list[str]:
    """Return rubric categories with at least one matching term or phrase."""
    return [
        label
        for label, patterns in COMPILED_SIGNALS.items()
        if any(pattern.search(text) for pattern in patterns)
    ]


def classify_trend(trend: Any) -> Topic | None:
    name = str(getattr(trend, "name", "")).strip()
    if not name:
        return None

    context = " ".join(
        str(value)
        for value in (
            getattr(trend, "domain_context", ""),
            *(getattr(trend, "grouped_trends", None) or []),
        )
        if value
    )
    signals = find_signals(f"{name} {context}")
    if not signals:
        return None

    count = getattr(trend, "tweets_count", None)
    return Topic(name=name, signals=signals, tweet_count=count if isinstance(count, int) else None)


async def fetch_trends(limit: int, location: str | None) -> list[Any]:
    try:
        from twikit import Client
    except ImportError as error:
        raise RuntimeError("Twikit is missing. Install it with: python -m pip install -r requirements.txt") from error

    client = Client(language="en-US")
    try:
        if location:
            locations = await client.get_available_locations()
            match = next((item for item in locations if item.name.casefold() == location.casefold()), None)
            if match is None:
                available = ", ".join(sorted({item.name for item in locations})[:12])
                raise ValueError(f"Unknown trend location '{location}'. Examples: {available}")
            place_trends = await client.get_place_trends(match.woeid)
            return list(place_trends.trends)[:limit]

        return await client.get_trends("trending", count=limit, retry=False)
    finally:
        await client.http.aclose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List likely polarizing topics from current Twitter/X trends.",
        epilog="The keyword rubric is a rough signal, not an objective measure of controversy.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum trends to inspect (default: 50).")
    parser.add_argument("--location", help="Trend location name, for example United States or Japan.")
    parser.add_argument("--json", action="store_true", help="Print matching topics as a JSON list.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    return args


async def run() -> int:
    args = parse_args()
    try:
        trends = await fetch_trends(args.limit, args.location)
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        if "KEY_BYTE indices" in str(error):
            print(
                "Twikit could not parse X's current client scripts. "
                "Trend scraping is blocked until Twikit supports the updated page. "
                "Check for a Twikit update and try again.",
                file=sys.stderr,
            )
            return 1
        print(f"Could not fetch trends: {error}", file=sys.stderr)
        return 1

    topics = [topic for trend in trends if (topic := classify_trend(trend)) is not None]
    if args.json:
        print(json.dumps([asdict(topic) for topic in topics], indent=2, ensure_ascii=False))
        return 0

    scope = f" in {args.location}" if args.location else ""
    print(f"Likely polarizing trending topics{scope} ({len(topics)} found):")
    if not topics:
        print("No trends matched the current keyword rubric.")
    for topic in topics:
        count = f" | {topic.tweet_count:,} posts" if topic.tweet_count is not None else ""
        print(f"- {topic.name}{count}")
        print(f"  Signals: {', '.join(topic.signals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))