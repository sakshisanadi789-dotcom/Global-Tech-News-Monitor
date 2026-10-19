"""Regenerate today's briefing from news already saved in MongoDB."""

from typing import Any

from pymongo import MongoClient

from briefing_service import generate_daily_briefing, print_briefing
from database import connect_to_mongodb


def refresh_today_briefing() -> dict[str, Any]:
    """Regenerate and print today's briefing without fetching new articles."""
    client: MongoClient | None = None

    try:
        client, database = connect_to_mongodb()
        briefing = generate_daily_briefing(
            database["news"],
            database["daily_briefings"],
        )
        print_briefing(briefing)
        return briefing
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    refresh_today_briefing()
