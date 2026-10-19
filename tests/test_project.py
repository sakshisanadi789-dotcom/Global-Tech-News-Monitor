"""Offline tests for news processing, briefings, scheduling, and API routes."""

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import requests
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

import briefing_service
import news_service
import refresh_briefing
import scheduler
from main import create_app


class Cursor:
    """A small iterable stand-in for a sortable, limitable PyMongo cursor."""

    def __init__(self, documents):
        self.documents = documents

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def __iter__(self):
        return iter(self.documents)


class NewsServiceTests(unittest.TestCase):
    def test_categorization_prefers_specific_categories(self):
        self.assertEqual(
            news_service.categorize_article("Quantum AI research", None),
            "Quantum Computing",
        )
        self.assertEqual(
            news_service.categorize_article("An AI coding assistant", None),
            "AI",
        )
        self.assertEqual(
            news_service.categorize_article("A straw analysis", None),
            "Other Technology",
        )

    def test_fetch_news_normalizes_articles(self):
        response = MagicMock()
        response.ok = True
        response.json.return_value = {
            "articles": [
                {
                    "title": "Quantum research update",
                    "description": "A short source description.",
                    "source": {"name": "Example News"},
                    "author": None,
                    "url": "https://example.com/quantum",
                    "publishedAt": "2026-10-18T08:30:00Z",
                }
            ],
        }

        with (
            patch.object(news_service, "GNEWS_API_KEY", "test-key"),
            patch.object(news_service.requests, "get", return_value=response) as get,
        ):
            articles = news_service.fetch_news()

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["category"], "Quantum Computing")
        self.assertEqual(articles[0]["source"], "Example News")
        self.assertEqual(
            articles[0]["published_at"],
            datetime(2026, 10, 18, 8, 30, tzinfo=UTC),
        )
        self.assertIsNotNone(articles[0]["collected_at"].tzinfo)
        self.assertEqual(get.call_args.kwargs["timeout"], 20)
        self.assertEqual(
            get.call_args.args[0],
            "https://gnews.io/api/v4/search",
        )
        self.assertEqual(get.call_args.kwargs["params"]["max"], 10)
        self.assertEqual(get.call_args.kwargs["params"]["lang"], "en")
        self.assertEqual(
            get.call_args.kwargs["params"]["apikey"],
            "test-key",
        )
        self.assertEqual(
            get.call_args.kwargs["params"]["apikey"],
            "test-key",
        )

    def test_fetch_news_rejects_missing_key_and_handles_empty_response(self):
        with (
            patch.object(news_service, "GNEWS_API_KEY", ""),
            patch.object(news_service.requests, "get") as get,
        ):
            with self.assertRaises(news_service.GNewsError):
                news_service.fetch_news()
        get.assert_not_called()

        response = MagicMock()
        response.ok = True
        response.json.return_value = {"articles": []}
        with (
            patch.object(news_service, "GNEWS_API_KEY", "test-key"),
            patch.object(news_service.requests, "get", return_value=response),
        ):
            self.assertEqual(news_service.fetch_news(), [])

    def test_fetch_news_translates_timeout_and_invalid_json(self):
        with (
            patch.object(news_service, "GNEWS_API_KEY", "test-key"),
            patch.object(
                news_service.requests,
                "get",
                side_effect=requests.Timeout,
            ),
        ):
            with self.assertRaisesRegex(news_service.GNewsError, "timed out"):
                news_service.fetch_news()

        response = MagicMock()
        response.ok = True
        response.json.side_effect = requests.exceptions.JSONDecodeError(
            "invalid",
            "",
            0,
        )
        with (
            patch.object(news_service, "GNEWS_API_KEY", "test-key"),
            patch.object(news_service.requests, "get", return_value=response),
        ):
            with self.assertRaisesRegex(news_service.GNewsError, "invalid JSON"):
                news_service.fetch_news()

    def test_store_news_counts_duplicate_urls(self):
        collection = MagicMock()
        collection.insert_one.side_effect = [MagicMock(), DuplicateKeyError("duplicate")]
        article = {"url": "https://example.com/article"}

        result = news_service.store_news(collection, [article, article])

        self.assertEqual(result, {"inserted": 1, "duplicates": 1})
        self.assertEqual(
            news_service.store_news(collection, []),
            {"inserted": 0, "duplicates": 0},
        )


class BriefingServiceTests(unittest.TestCase):
    def test_briefing_filters_by_local_day_and_upserts(self):
        now = datetime(2026, 10, 18, 6, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        articles = [
            {
                "title": "AI model release",
                "description": "Details from the source.",
                "source": "Example News",
                "url": "https://example.com/ai",
                "category": "AI",
                "published_at": now.astimezone(UTC) - timedelta(hours=1),
                "collected_at": now.astimezone(UTC),
            }
        ]
        news_collection = MagicMock()
        news_collection.find.return_value = articles
        saved_briefing = {
            "briefing_date": "2026-10-18",
            "generated_at": now.astimezone(UTC),
            "total_news": 1,
            "categories": {"AI": 1},
            "top_news": [],
            "learning_of_day": "Learn AI",
            "career_opportunity": "Explore AI roles",
        }
        briefing_collection = MagicMock()
        briefing_collection.find_one.return_value = saved_briefing

        result = briefing_service.generate_daily_briefing(
            news_collection,
            briefing_collection,
            now,
        )

        self.assertEqual(result, saved_briefing)
        query = news_collection.find.call_args.args[0]
        self.assertEqual(
            query["collected_at"]["$gte"],
            datetime(2026, 10, 17, 18, 30, tzinfo=UTC),
        )
        self.assertEqual(
            query["collected_at"]["$lt"],
            datetime(2026, 10, 18, 18, 30, tzinfo=UTC),
        )
        self.assertTrue(briefing_collection.update_one.call_args.kwargs["upsert"])
        self.assertEqual(
            briefing_collection.update_one.call_args.args[1]["$set"]["total_news"],
            1,
        )

    def test_scoring_prefers_recent_articles_and_limits_section_size(self):
        now = datetime(2026, 10, 18, 6, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        recent = now.astimezone(UTC)
        articles = [
            {
                "title": f"AI story {index}",
                "description": "Source description.",
                "source": "Example News",
                "url": f"https://example.com/{index}",
                "category": "AI",
                "published_at": recent - timedelta(hours=index),
                "collected_at": recent,
            }
            for index in range(4)
        ]

        stories = briefing_service._build_top_news(list(reversed(articles)), now)

        self.assertEqual(len(stories), briefing_service.MAX_STORIES_PER_SECTION)
        self.assertEqual(stories[0]["title"], "AI story 0")
        self.assertGreater(
            briefing_service.score_article(articles[0], now),
            briefing_service.score_article(
                {**articles[0], "published_at": recent - timedelta(days=15)},
                now,
            ),
        )

    def test_empty_day_still_generates_readable_briefing(self):
        now = datetime(2026, 10, 18, 6, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        news_collection = MagicMock()
        news_collection.find.return_value = []
        briefing_collection = MagicMock()
        briefing_collection.find_one.return_value = {
            "briefing_date": "2026-10-18",
            "total_news": 0,
            "categories": {},
            "top_news": [],
            "learning_of_day": "Review technology fundamentals.",
            "career_opportunity": "Explore transferable skills.",
        }

        briefing = briefing_service.generate_daily_briefing(
            news_collection,
            briefing_collection,
            now,
        )

        self.assertEqual(briefing["total_news"], 0)
        self.assertIn("No articles collected", briefing_service.format_briefing(briefing))


class SchedulerTests(unittest.TestCase):
    def test_daily_job_runs_services_in_order_and_closes_client(self):
        client = MagicMock()
        database = {"news": MagicMock(), "daily_briefings": MagicMock()}
        briefing = {"briefing_date": "2026-10-18"}
        calls = []

        with (
            patch.object(scheduler, "connect_to_mongodb", return_value=(client, database)),
            patch.object(
                scheduler,
                "fetch_news",
                side_effect=lambda: calls.append("fetch") or [{"url": "example"}],
            ),
            patch.object(
                scheduler,
                "store_news",
                side_effect=lambda *_args: calls.append("store")
                or {"inserted": 1, "duplicates": 0},
            ),
            patch.object(
                scheduler,
                "generate_daily_briefing",
                side_effect=lambda *_args: calls.append("brief") or briefing,
            ),
            patch.object(
                scheduler,
                "print_briefing",
                side_effect=lambda *_args: calls.append("print"),
            ),
        ):
            result = scheduler.run_daily_news_job()

        self.assertEqual(calls, ["fetch", "store", "brief", "print"])
        self.assertEqual(result["inserted"], 1)
        client.close.assert_called_once()

    def test_daily_job_closes_client_when_a_service_fails(self):
        client = MagicMock()
        database = {"news": MagicMock(), "daily_briefings": MagicMock()}

        with (
            patch.object(scheduler, "connect_to_mongodb", return_value=(client, database)),
            patch.object(scheduler, "fetch_news", side_effect=RuntimeError("test failure")),
        ):
            with self.assertRaisesRegex(RuntimeError, "test failure"):
                scheduler.run_daily_news_job()

        client.close.assert_called_once()


class ManualRefreshTests(unittest.TestCase):
    def test_refresh_regenerates_prints_and_closes_client(self):
        client = MagicMock()
        database = {"news": MagicMock(), "daily_briefings": MagicMock()}
        briefing = {"briefing_date": "2026-10-18", "total_news": 2}

        with (
            patch.object(
                refresh_briefing,
                "connect_to_mongodb",
                return_value=(client, database),
            ),
            patch.object(
                refresh_briefing,
                "generate_daily_briefing",
                return_value=briefing,
            ) as generate,
            patch.object(refresh_briefing, "print_briefing") as print_result,
        ):
            result = refresh_briefing.refresh_today_briefing()

        self.assertEqual(result, briefing)
        generate.assert_called_once_with(
            database["news"],
            database["daily_briefings"],
        )
        print_result.assert_called_once_with(briefing)
        client.close.assert_called_once()

    def test_refresh_closes_client_when_generation_fails(self):
        client = MagicMock()
        database = {"news": MagicMock(), "daily_briefings": MagicMock()}

        with (
            patch.object(
                refresh_briefing,
                "connect_to_mongodb",
                return_value=(client, database),
            ),
            patch.object(
                refresh_briefing,
                "generate_daily_briefing",
                side_effect=RuntimeError("test failure"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "test failure"):
                refresh_briefing.refresh_today_briefing()

        client.close.assert_called_once()


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.article_id = ObjectId()
        self.article = {
            "_id": self.article_id,
            "title": "Python cloud article",
            "description": "A technology story.",
            "source": "Example News",
            "author": None,
            "url": "https://example.com/article",
            "category": "Cloud",
            "published_at": datetime(2026, 10, 18, tzinfo=UTC),
            "collected_at": datetime(2026, 10, 18, 1, tzinfo=UTC),
        }
        self.briefing = {
            "_id": ObjectId(),
            "briefing_date": "2026-10-18",
            "generated_at": datetime(2026, 10, 18, tzinfo=UTC),
            "total_news": 1,
            "categories": {"Cloud": 1},
            "top_news": [],
        }
        self.news_collection = MagicMock()
        self.news_collection.find.side_effect = (
            lambda *_args, **_kwargs: Cursor([self.article])
        )
        self.news_collection.find_one.return_value = self.article
        self.briefings_collection = MagicMock()
        self.briefings_collection.find.side_effect = (
            lambda *_args, **_kwargs: Cursor([self.briefing])
        )
        self.briefings_collection.find_one.return_value = self.briefing
        self.client = MagicMock()
        self.app = create_app(
            self.client,
            {
                "news": self.news_collection,
                "daily_briefings": self.briefings_collection,
            },
        )
        self.app.testing = True
        self.http = self.app.test_client()

    def test_article_and_briefing_endpoints_serialize_mongodb_values(self):
        response = self.http.get("/news?limit=5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["news"][0]["id"], str(self.article_id))
        self.assertNotIn("_id", response.json["news"][0])
        self.assertEqual(
            response.json["news"][0]["published_at"],
            "2026-10-18T00:00:00+00:00",
        )

        response = self.http.get(f"/news/{self.article_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["id"], str(self.article_id))
        self.assertEqual(self.http.get("/briefings").status_code, 200)
        response = self.http.get("/briefings/2026-10-18")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["generated_at"],
            "2026-10-18T00:00:00+00:00",
        )

    def test_search_category_and_input_validation(self):
        response = self.http.get("/news/search?keyword=python")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["count"], 1)
        query = self.news_collection.find.call_args.args[0]
        self.assertEqual(query["$or"][0]["title"]["$regex"], "python")

        self.http.get("/news/search?keyword=%2E%2A")
        query = self.news_collection.find.call_args.args[0]
        self.assertEqual(query["$or"][0]["title"]["$regex"], r"\.\*")
        self.assertEqual(self.http.get("/news/search").status_code, 400)
        self.assertEqual(self.http.get("/news?limit=invalid").status_code, 400)
        self.assertEqual(self.http.get("/news/category/Unknown").status_code, 400)
        self.assertEqual(self.http.get("/briefings/2026-2-1").status_code, 400)

    def test_schedule_endpoint_updates_and_validates_interval(self):
        self.assertEqual(
            self.http.get("/schedule").json,
            {
                "interval": "1d",
                "interval_seconds": 24 * 60 * 60,
                "next_run_time": None,
            },
        )
        response = self.http.post("/schedule", json={"interval": "5m"})
        self.assertEqual(response.status_code, 503)

        scheduler_instance = MagicMock()
        scheduler_instance.get_job.return_value = None
        self.app.config["SCHEDULER"] = scheduler_instance
        response = self.http.post("/schedule", json={"interval": "5m"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["interval"], "5m")
        scheduler_instance.reschedule_job.assert_called_once_with(
            "daily-tech-news-briefing",
            trigger="interval",
            seconds=300,
        )

        response = self.http.post("/schedule", json={"interval": "10m"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(scheduler_instance.reschedule_job.call_count, 1)
        self.assertEqual(
            self.http.post("/schedule", json={"interval": []}).status_code,
            400,
        )
        self.assertEqual(
            self.http.post("/schedule", data="{}", content_type="text/plain").status_code,
            400,
        )
        self.assertEqual(
            self.http.post(
                "/schedule",
                data="{",
                content_type="application/json",
            ).status_code,
            400,
        )

    def test_not_found_and_database_unavailable_responses(self):
        self.assertEqual(self.http.get("/news/invalid-id").status_code, 400)
        self.news_collection.find_one.return_value = None
        self.assertEqual(
            self.http.get(f"/news/{ObjectId()}").status_code,
            404,
        )
        self.briefings_collection.find_one.return_value = None
        self.assertEqual(
            self.http.get("/briefings/2026-10-19").status_code,
            404,
        )
        self.client.admin.command.side_effect = ServerSelectionTimeoutError(
            "private connection detail"
        )
        with self.assertLogs("main", level="ERROR"):
            response = self.http.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private connection detail", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
