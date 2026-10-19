"""Fetch news from GNews, categorize it, and save it to MongoDB."""

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import requests
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from config import GNEWS_API_KEY, GNEWS_API_URL, GNEWS_QUERY
from models import NewsArticle


logger = logging.getLogger(__name__)

# Keep specific categories before broader categories such as AI.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Agentic AI": ("agentic", "ai agent", "ai agents", "autonomous agent"),
    "Quantum Computing": ("quantum", "qubit"),
    "Cybersecurity": ("cybersecurity", "cyber attack", "ransomware", "vulnerability"),
    "Cloud": ("cloud computing", "cloud service", "cloud platform", "aws", "azure"),
    "Developer Tools": ("developer tool", "ide", "code editor", "github copilot"),
    "Programming": ("programming", "programming language", "software development"),
    "Startups": ("startup", "start-up", "venture capital", "funding round"),
    "Technology Companies": (
        "apple",
        "google",
        "microsoft",
        "amazon",
        "meta",
        "nvidia",
        "tesla",
    ),
    "AI": (
        "artificial intelligence",
        "machine learning",
        "ai",
        "llm",
        "language model",
    ),
}


class GNewsError(Exception):
    """Raised when the GNews request or response cannot be used safely."""


def categorize_article(title: str, description: str | None) -> str:
    """Choose the first matching category using editable keyword rules."""
    combined_text = f"{title} {description or ''}".casefold()
    normalized_text = "".join(
        character if character.isalnum() else " "
        for character in combined_text
    )
    text = f" {' '.join(normalized_text.split())} "

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(f" {keyword.casefold()} " in text for keyword in keywords):
            return category

    return "Other Technology"


def _parse_published_at(value: object) -> datetime | None:
    """Convert an ISO-formatted publication date into a timezone-aware datetime."""
    if not isinstance(value, str) or not value:
        return None

    try:
        published_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Using no publication date for an invalid GNews date.")
        return None

    if published_at.tzinfo is None:
        return published_at.replace(tzinfo=UTC)

    return published_at


def _is_http_url(value: object) -> bool:
    """Return whether a value is an absolute HTTP or HTTPS URL."""
    if not isinstance(value, str):
        return False

    try:
        parsed_url = urlsplit(value)
    except ValueError:
        return False

    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def _normalize_article(article: object) -> NewsArticle | None:
    """Convert one GNews article into the project's MongoDB document shape."""
    if not isinstance(article, dict):
        logger.warning("Skipping a GNews article with an invalid data shape.")
        return None

    title = article.get("title")
    url = article.get("url")
    source_data = article.get("source")
    source = source_data.get("name") if isinstance(source_data, dict) else None

    if not isinstance(title, str) or not title.strip():
        logger.warning("Skipping a GNews article with no title.")
        return None
    if not _is_http_url(url):
        logger.warning("Skipping a GNews article with no valid HTTP URL.")
        return None
    if not isinstance(source, str) or not source.strip():
        logger.warning("Skipping a GNews article with no source name.")
        return None

    description = article.get("description")
    if not isinstance(description, str):
        description = None

    author = article.get("author")
    if not isinstance(author, str):
        author = None

    return {
        "title": title.strip(),
        "description": description.strip() if description else None,
        "source": source.strip(),
        "author": author.strip() if author else None,
        "url": url,
        "category": categorize_article(title, description),
        "published_at": _parse_published_at(article.get("publishedAt")),
        "collected_at": datetime.now(UTC),
    }


def fetch_news() -> list[NewsArticle]:
    """Fetch and normalize the latest articles from the configured GNews endpoint."""
    if not GNEWS_API_KEY:
        raise GNewsError(
            "GNEWS_API_KEY is not set. Add your GNews key to the local .env file."
        )

    try:
        response = requests.get(
            GNEWS_API_URL,
            params={
                "q": GNEWS_QUERY,
                "lang": "en",
                "sortby": "publishedAt",
                "max": 10,
                "apikey": GNEWS_API_KEY,
            },
            timeout=20,
        )
    except requests.Timeout:
        raise GNewsError("The GNews request timed out.") from None
    except requests.ConnectionError:
        raise GNewsError("Could not connect to GNews.") from None
    except requests.RequestException:
        raise GNewsError("The GNews request failed.") from None

    if not response.ok:
        raise GNewsError(f"GNews returned HTTP status {response.status_code}.")

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        raise GNewsError("GNews returned invalid JSON.") from None

    if not isinstance(payload, dict):
        raise GNewsError("GNews returned an invalid response format.")

    raw_articles = payload.get("articles")
    if not isinstance(raw_articles, list):
        raise GNewsError("GNews response did not contain an articles list.")

    articles = []
    for raw_article in raw_articles:
        normalized_article = _normalize_article(raw_article)
        if normalized_article is not None:
            articles.append(normalized_article)

    return articles


def store_news(
    news_collection: Collection[dict[str, Any]],
    articles: list[NewsArticle],
) -> dict[str, int]:
    """Insert new articles and count links rejected by the unique URL index."""
    inserted = 0
    duplicates = 0

    for article in articles:
        try:
            news_collection.insert_one(article)
            inserted += 1
        except DuplicateKeyError:
            duplicates += 1
        except PyMongoError:
            logger.exception("Could not save a news article to MongoDB.")
            raise

    return {"inserted": inserted, "duplicates": duplicates}
