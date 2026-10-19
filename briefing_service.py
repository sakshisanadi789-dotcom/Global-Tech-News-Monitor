"""Select important collected articles and save a daily briefing."""

import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from config import NEWS_SCHEDULE_TIMEZONE


logger = logging.getLogger(__name__)

SECTION_CATEGORIES: dict[str, tuple[str, ...]] = {
    "AI": ("AI",),
    "AGENTIC AI": ("Agentic AI",),
    "QUANTUM COMPUTING": ("Quantum Computing",),
    "CLOUD & SOFTWARE": ("Cloud", "Programming", "Developer Tools"),
    "CYBERSECURITY": ("Cybersecurity",),
    "TECHNOLOGY BUSINESS": (
        "Startups",
        "Technology Companies",
        "Other Technology",
    ),
}

CATEGORY_WEIGHTS = {
    "Agentic AI": 10,
    "Quantum Computing": 10,
    "Cybersecurity": 9,
    "AI": 9,
    "Cloud": 8,
    "Technology Companies": 8,
    "Startups": 7,
    "Developer Tools": 7,
    "Programming": 6,
    "Other Technology": 3,
}
MAX_STORIES_PER_SECTION = 2

WHY_IT_MATTERS = {
    "AI": "AI developments can change how people build software and solve problems.",
    "Agentic AI": "Agentic AI explores systems that can plan and take actions toward a goal.",
    "Quantum Computing": "Quantum computing research may shape future approaches to specialized computing problems.",
    "Cloud": "Cloud changes can affect how organizations build, deploy, and operate software.",
    "Cybersecurity": "Cybersecurity developments can affect the safety of systems and user data.",
    "Programming": "Programming changes can influence how developers write and maintain software.",
    "Developer Tools": "Developer tools can change how software teams build, test, and maintain applications.",
    "Startups": "Startup developments can reveal emerging products, markets, and business ideas.",
    "Technology Companies": "Major technology company decisions can influence products and the wider industry.",
    "Other Technology": "This development adds context to broader technology trends.",
}

LEARNING_TOPICS = {
    "AI": "Explore how a machine-learning model is trained and evaluated.",
    "Agentic AI": "Build a small agent loop that plans, uses one tool, and checks its result.",
    "Quantum Computing": "Learn the basics of qubits, superposition, and quantum gates.",
    "Cloud": "Deploy a small web application and learn how cloud hosting works.",
    "Cybersecurity": "Practice recognizing common web application security risks.",
    "Programming": "Read about the programming language or software technique in today's story.",
    "Developer Tools": "Try a developer tool mentioned in today's news on a small sample project.",
    "Startups": "Study how a technology startup validates a problem and its proposed solution.",
    "Technology Companies": "Compare the products or platforms mentioned in today's company news.",
    "Other Technology": "Choose one technical term from today's briefing and learn its fundamentals.",
}

CAREER_SKILLS = {
    "AI": "machine learning and AI application development",
    "Agentic AI": "agent design, tool integration, and AI evaluation",
    "Quantum Computing": "quantum information and scientific computing",
    "Cloud": "cloud engineering and platform operations",
    "Cybersecurity": "security analysis and incident response",
    "Programming": "software development and programming language skills",
    "Developer Tools": "developer productivity and software tooling",
    "Startups": "product development and technology entrepreneurship",
    "Technology Companies": "software, product, and technology business roles",
    "Other Technology": "adaptable software and technology fundamentals",
}


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes from MongoDB as UTC and normalize aware values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def score_article(article: dict[str, Any], now: datetime) -> int:
    """Score an article using category importance and publication recency."""
    if now.tzinfo is None:
        raise ValueError("now must include a timezone.")

    category = article.get("category", "Other Technology")
    score = CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["Other Technology"])
    article_date = article.get("published_at") or article.get("collected_at")

    if isinstance(article_date, datetime):
        age = max(now.astimezone(UTC) - _as_utc(article_date), timedelta(0))
        if age < timedelta(days=1):
            score += 5
        elif age < timedelta(days=2):
            score += 4
        elif age < timedelta(days=3):
            score += 3
        elif age < timedelta(days=7):
            score += 2
        elif age < timedelta(days=14):
            score += 1

    return score


def _article_summary(article: dict[str, Any]) -> str:
    """Use the source description or clearly state that only the headline is known."""
    description = article.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return "The source did not provide a description; this summary is based on the headline only."


def _article_sort_key(
    article: dict[str, Any],
    now: datetime,
) -> tuple[int, datetime, str]:
    """Build a stable ranking key so ties do not depend on MongoDB result order."""
    article_date = article.get("published_at") or article.get("collected_at")
    if not isinstance(article_date, datetime):
        article_date = datetime.min.replace(tzinfo=UTC)

    return (
        score_article(article, now),
        _as_utc(article_date),
        str(article.get("url", "")),
    )


def _build_top_news(
    articles: list[dict[str, Any]],
    now: datetime,
) -> list[dict[str, Any]]:
    """Choose up to two highest-scoring articles for each briefing section."""
    selected: list[dict[str, Any]] = []

    for section, categories in SECTION_CATEGORIES.items():
        candidates = [article for article in articles if article.get("category") in categories]
        candidates.sort(key=lambda article: _article_sort_key(article, now), reverse=True)

        for article in candidates[:MAX_STORIES_PER_SECTION]:
            category = article.get("category", "Other Technology")
            selected.append(
                {
                    "section": section,
                    "title": article.get("title", "Untitled technology story"),
                    "summary": _article_summary(article),
                    "why_it_matters": WHY_IT_MATTERS.get(
                        category,
                        WHY_IT_MATTERS["Other Technology"],
                    ),
                    "source": article.get("source", "Unknown source"),
                    "url": article.get("url"),
                    "category": category,
                    "published_at": article.get("published_at"),
                    "importance_score": score_article(article, now),
                }
            )

    return selected


def _learning_and_career(top_news: list[dict[str, Any]]) -> tuple[str, str]:
    """Suggest one learning topic and relevant career skills from selected stories."""
    if not top_news:
        return (
            "Review the fundamentals of a technology topic you are currently learning.",
            "Strong programming, communication, and problem-solving skills are useful across technology roles.",
        )

    category = top_news[0]["category"]
    return (
        LEARNING_TOPICS.get(category, LEARNING_TOPICS["Other Technology"]),
        f"Relevant skills to explore: {CAREER_SKILLS.get(category, CAREER_SKILLS['Other Technology'])}.",
    )


def _daily_window(
    now: datetime,
    timezone: ZoneInfo,
) -> tuple[date, datetime, datetime]:
    """Find the local briefing date and its UTC collection-time boundaries."""
    if now.tzinfo is None:
        raise ValueError("now must include a timezone.")

    local_now = now.astimezone(timezone)
    briefing_date = local_now.date()
    local_start = datetime.combine(briefing_date, time.min, tzinfo=timezone)
    local_end = datetime.combine(
        briefing_date + timedelta(days=1),
        time.min,
        tzinfo=timezone,
    )
    return briefing_date, local_start.astimezone(UTC), local_end.astimezone(UTC)


def generate_daily_briefing(
    news_collection: Collection[dict[str, Any]],
    briefing_collection: Collection[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build and upsert the briefing for the current local calendar date."""
    try:
        timezone = ZoneInfo(NEWS_SCHEDULE_TIMEZONE)
    except ZoneInfoNotFoundError as error:
        raise ValueError("NEWS_SCHEDULE_TIMEZONE is not a recognized timezone.") from error

    generated_at = now or datetime.now(timezone)
    briefing_date, start_utc, end_utc = _daily_window(generated_at, timezone)

    try:
        articles = list(
            news_collection.find(
                {"collected_at": {"$gte": start_utc, "$lt": end_utc}}
            )
        )
        categories: dict[str, int] = {}
        for article in articles:
            category = article.get("category", "Other Technology")
            categories[category] = categories.get(category, 0) + 1

        top_news = _build_top_news(articles, generated_at)
        learning_of_day, career_opportunity = _learning_and_career(top_news)
        briefing = {
            "briefing_date": briefing_date.isoformat(),
            "generated_at": generated_at.astimezone(UTC),
            "total_news": len(articles),
            "categories": categories,
            "top_news": top_news,
            "learning_of_day": learning_of_day,
            "career_opportunity": career_opportunity,
        }

        briefing_collection.update_one(
            {"briefing_date": briefing["briefing_date"]},
            {
                "$set": briefing,
                "$setOnInsert": {"created_at": generated_at.astimezone(UTC)},
            },
            upsert=True,
        )
        saved_briefing = briefing_collection.find_one(
            {"briefing_date": briefing["briefing_date"]}
        )
    except PyMongoError:
        logger.exception("Could not create or save the daily briefing.")
        raise

    if saved_briefing is None:
        raise RuntimeError("MongoDB did not return the saved daily briefing.")

    return saved_briefing


def format_briefing(briefing: dict[str, Any]) -> str:
    """Format a saved briefing as readable terminal text."""
    lines = [
        "DAILY GLOBAL TECH BRIEFING",
        f"Date: {briefing['briefing_date']}",
        f"Articles collected: {briefing['total_news']}",
        "",
    ]
    stories_by_section: dict[str, list[dict[str, Any]]] = {
        section: [] for section in SECTION_CATEGORIES
    }
    for story in briefing["top_news"]:
        stories_by_section.setdefault(story["section"], []).append(story)

    for section, stories in stories_by_section.items():
        lines.append(section)
        if not stories:
            lines.append("- No articles collected for this section today.")
        for story in stories:
            lines.extend(
                [
                    f"- {story['title']}",
                    f"  Summary: {story['summary']}",
                    f"  Why it matters: {story['why_it_matters']}",
                    f"  Source: {story['source']} ({story['url']})",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "LEARNING OF THE DAY",
            briefing["learning_of_day"],
            "",
            "CAREER OPPORTUNITY",
            briefing["career_opportunity"],
        ]
    )
    return "\n".join(lines)


def print_briefing(briefing: dict[str, Any]) -> None:
    """Print the formatted briefing to the terminal."""
    print(format_briefing(briefing))
