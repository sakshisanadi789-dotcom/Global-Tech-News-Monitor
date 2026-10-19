"""Create the Flask REST API and start the web server and scheduler."""

import logging
import re
from datetime import date, datetime
from typing import Any

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.base import SchedulerNotRunningError
from bson import ObjectId
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError
from werkzeug.exceptions import BadRequest
from database import connect_to_mongodb
from news_service import CATEGORY_KEYWORDS
from scheduler import (
    SCHEDULE_INTERVAL_SECONDS,
    configure_news_schedule,
    start_scheduler,
    stop_scheduler,
)


logger = logging.getLogger(__name__)
VALID_CATEGORIES = frozenset((*CATEGORY_KEYWORDS, "Other Technology"))
MAX_PAGE_SIZE = 100


def _to_json_value(value: Any) -> Any:
    """Convert MongoDB and Python values into JSON-compatible values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _to_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    return value


def _article_for_response(article: dict[str, Any]) -> dict[str, Any]:
    """Rename MongoDB's internal _id field to a beginner-friendly id field."""
    result = dict(article)
    result["id"] = str(result.pop("_id"))
    return _to_json_value(result)


def _read_limit(default: int) -> int:
    """Read and validate a bounded result limit from the query string."""
    raw_limit = request.args.get("limit")
    if raw_limit is None:
        return default

    try:
        limit = int(raw_limit)
    except ValueError as error:
        raise ValueError("limit must be a whole number.") from error

    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}.")

    return limit


def create_app(
    client: MongoClient | None = None,
    database: Database | None = None,
) -> Flask:
    """Create the API app, optionally using a supplied MongoDB connection."""
    if (client is None) != (database is None):
        raise ValueError("client and database must either both be supplied or both omitted.")

    if client is None or database is None:
        client, database = connect_to_mongodb()

    app = Flask(__name__)
    app.config["MONGO_CLIENT"] = client
    app.config["NEWS_COLLECTION"] = database["news"]
    app.config["BRIEFINGS_COLLECTION"] = database["daily_briefings"]
    app.config["SCHEDULER"] = None
    app.config["NEWS_SCHEDULE_INTERVAL"] = "1d"

    def schedule_response(interval: str):
        scheduler = app.config["SCHEDULER"]
        job = (
            scheduler.get_job("daily-tech-news-briefing")
            if scheduler is not None
            else None
        )
        next_run_time = (
            job.next_run_time.isoformat()
            if job is not None and job.next_run_time is not None
            else None
        )
        return {
            "interval": interval,
            "interval_seconds": SCHEDULE_INTERVAL_SECONDS[interval],
            "next_run_time": next_run_time,
        }

    @app.get("/")
    def news_dashboard():
        return render_template(
            "index.html",
            categories=sorted(VALID_CATEGORIES),
        )

    @app.get("/health")
    def health():
        try:
            app.config["MONGO_CLIENT"].admin.command("ping")
        except PyMongoError:
            logger.exception("Health check could not reach MongoDB.")
            return jsonify({"status": "unavailable", "error": "Database is unavailable."}), 503

        return jsonify({"status": "ok", "database": "connected"}), 200

    @app.route("/schedule", methods=["GET", "POST"])
    def news_schedule():
        if request.method == "GET":
            interval = app.config["NEWS_SCHEDULE_INTERVAL"]
            return jsonify(schedule_response(interval)), 200

        if not request.is_json:
            return jsonify({"error": "Request body must be JSON."}), 400
        try:
            payload = request.get_json()
        except BadRequest:
            return jsonify({"error": "Request body must contain valid JSON."}), 400
        interval = payload.get("interval") if isinstance(payload, dict) else None
        if not isinstance(interval, str) or interval not in SCHEDULE_INTERVAL_SECONDS:
            return jsonify(
                {
                    "error": "interval must be one of 1m, 5m, 1h, or 1d.",
                }
            ), 400

        scheduler = app.config["SCHEDULER"]
        if scheduler is None:
            return jsonify({"error": "The news scheduler is not running."}), 503

        try:
            configure_news_schedule(scheduler, interval)
        except (JobLookupError, SchedulerNotRunningError):
            logger.exception("Could not update the news collection schedule.")
            return jsonify({"error": "Could not update the news schedule."}), 503

        app.config["NEWS_SCHEDULE_INTERVAL"] = interval
        return jsonify(schedule_response(interval)), 200

    @app.get("/news")
    def latest_news():
        try:
            limit = _read_limit(default=20)
            cursor = (
                app.config["NEWS_COLLECTION"]
                .find()
                .sort([("published_at", -1), ("collected_at", -1)])
                .limit(limit)
            )
            articles = [_article_for_response(article) for article in cursor]
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except PyMongoError:
            logger.exception("Could not retrieve the latest news.")
            return jsonify({"error": "Could not retrieve news."}), 503

        return jsonify({"news": articles, "count": len(articles)}), 200

    @app.get("/news/search")
    def search_news():
        keyword = request.args.get("keyword", "").strip()
        if not keyword:
            return jsonify({"error": "A non-empty keyword query parameter is required."}), 400
        if len(keyword) > 100:
            return jsonify({"error": "keyword must be 100 characters or fewer."}), 400

        try:
            limit = _read_limit(default=20)
            safe_keyword = re.escape(keyword)
            cursor = (
                app.config["NEWS_COLLECTION"]
                .find(
                    {
                        "$or": [
                            {"title": {"$regex": safe_keyword, "$options": "i"}},
                            {"description": {"$regex": safe_keyword, "$options": "i"}},
                            {"category": {"$regex": safe_keyword, "$options": "i"}},
                        ]
                    }
                )
                .sort([("published_at", -1), ("collected_at", -1)])
                .limit(limit)
            )
            articles = [_article_for_response(article) for article in cursor]
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except PyMongoError:
            logger.exception("Could not search news.")
            return jsonify({"error": "Could not search news."}), 503

        return jsonify({"news": articles, "count": len(articles)}), 200

    @app.get("/news/category/<category>")
    def news_by_category(category: str):
        if category not in VALID_CATEGORIES:
            return jsonify(
                {
                    "error": "Invalid category.",
                    "valid_categories": sorted(VALID_CATEGORIES),
                }
            ), 400

        try:
            limit = _read_limit(default=20)
            cursor = (
                app.config["NEWS_COLLECTION"]
                .find({"category": category})
                .sort([("published_at", -1), ("collected_at", -1)])
                .limit(limit)
            )
            articles = [_article_for_response(article) for article in cursor]
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except PyMongoError:
            logger.exception("Could not retrieve news by category.")
            return jsonify({"error": "Could not retrieve news."}), 503

        return jsonify({"category": category, "news": articles, "count": len(articles)}), 200

    @app.get("/news/<article_id>")
    def get_news_article(article_id: str):
        if not ObjectId.is_valid(article_id):
            return jsonify({"error": "Article id must be a valid MongoDB ObjectId."}), 400

        try:
            article = app.config["NEWS_COLLECTION"].find_one(
                {"_id": ObjectId(article_id)}
            )
        except PyMongoError:
            logger.exception("Could not retrieve the requested article.")
            return jsonify({"error": "Could not retrieve article."}), 503

        if article is None:
            return jsonify({"error": "Article not found."}), 404
        return jsonify(_article_for_response(article)), 200

    @app.get("/briefings")
    def previous_briefings():
        try:
            limit = _read_limit(default=10)
            cursor = (
                app.config["BRIEFINGS_COLLECTION"]
                .find()
                .sort("briefing_date", -1)
                .limit(limit)
            )
            briefings = [_to_json_value(briefing) for briefing in cursor]
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except PyMongoError:
            logger.exception("Could not retrieve previous briefings.")
            return jsonify({"error": "Could not retrieve briefings."}), 503

        return jsonify({"briefings": briefings, "count": len(briefings)}), 200

    @app.get("/briefings/<briefing_date>")
    def briefing_by_date(briefing_date: str):
        try:
            parsed_date = date.fromisoformat(briefing_date)
        except ValueError:
            return jsonify({"error": "Date must use the YYYY-MM-DD format."}), 400

        if parsed_date.isoformat() != briefing_date:
            return jsonify({"error": "Date must use the YYYY-MM-DD format."}), 400

        try:
            briefing = app.config["BRIEFINGS_COLLECTION"].find_one(
                {"briefing_date": briefing_date}
            )
        except PyMongoError:
            logger.exception("Could not retrieve the requested briefing.")
            return jsonify({"error": "Could not retrieve briefing."}), 503

        if briefing is None:
            return jsonify({"error": "Briefing not found."}), 404
        return jsonify(_to_json_value(briefing)), 200

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Endpoint not found."}), 404

    return app


def run_app() -> None:
    """Start the Flask development server and one daily scheduler."""
    app = create_app()
    scheduler = start_scheduler()
    app.config["SCHEDULER"] = scheduler

    try:
        app.run(host="127.0.0.1", port=5000)
    finally:
        stop_scheduler(scheduler)
        app.config["MONGO_CLIENT"].close()


if __name__ == "__main__":
    run_app()
