"""Run the news collection and briefing job once each day."""

import logging
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pymongo import MongoClient

from briefing_service import generate_daily_briefing, print_briefing
from config import (
    NEWS_SCHEDULE_HOUR,
    NEWS_SCHEDULE_MINUTE,
    NEWS_SCHEDULE_TIMEZONE,
)
from database import connect_to_mongodb
from news_service import fetch_news, store_news


logger = logging.getLogger(__name__)
SCHEDULE_INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 5 * 60,
    "1h": 60 * 60,
    "1d": 24 * 60 * 60,
}


def run_daily_news_job() -> dict[str, Any]:
    """Fetch, store, brief, and print news, then close the MongoDB client."""
    client: MongoClient | None = None

    try:
        client, database = connect_to_mongodb()
        articles = fetch_news()
        storage_counts = store_news(database["news"], articles)
        briefing = generate_daily_briefing(
            database["news"],
            database["daily_briefings"],
        )
        print_briefing(briefing)

        result = {
            "fetched": len(articles),
            **storage_counts,
            "briefing_date": briefing["briefing_date"],
        }
        logger.info(
            "Daily news job completed: fetched=%d inserted=%d duplicates=%d",
            result["fetched"],
            result["inserted"],
            result["duplicates"],
        )
        return result
    finally:
        if client is not None:
            client.close()


def start_scheduler() -> BackgroundScheduler:
    """Start the daily job using the schedule and timezone from configuration."""
    try:
        timezone = ZoneInfo(NEWS_SCHEDULE_TIMEZONE)
    except ZoneInfoNotFoundError as error:
        raise ValueError(
            "NEWS_SCHEDULE_TIMEZONE is not a recognized timezone."
        ) from error

    scheduler = BackgroundScheduler(timezone=timezone)
    trigger = CronTrigger(
        hour=NEWS_SCHEDULE_HOUR,
        minute=NEWS_SCHEDULE_MINUTE,
        timezone=timezone,
    )
    scheduler.add_job(
        run_daily_news_job,
        trigger=trigger,
        id="daily-tech-news-briefing",
        name="Collect technology news and generate the daily briefing",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        "Daily news scheduler started for %02d:%02d (%s).",
        NEWS_SCHEDULE_HOUR,
        NEWS_SCHEDULE_MINUTE,
        NEWS_SCHEDULE_TIMEZONE,
    )
    return scheduler


def configure_news_schedule(
    scheduler: BackgroundScheduler,
    interval: str,
) -> None:
    """Change the running news job to one of the supported intervals."""
    if interval not in SCHEDULE_INTERVAL_SECONDS:
        raise ValueError("Unsupported news collection interval.")

    scheduler.reschedule_job(
        "daily-tech-news-briefing",
        trigger="interval",
        seconds=SCHEDULE_INTERVAL_SECONDS[interval],
    )
    logger.info("News collection schedule changed to every %s.", interval)


def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    """Stop the scheduler and wait for any running job to finish."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
