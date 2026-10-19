"""Type hints for the documents stored by the news application."""

from datetime import datetime
from typing import TypedDict

from bson import ObjectId


class NewsArticle(TypedDict):
    """A normalized article ready to insert into the news collection."""

    title: str
    description: str | None
    source: str
    author: str | None
    url: str
    category: str
    published_at: datetime | None
    collected_at: datetime


class SavedNewsArticle(NewsArticle, total=False):
    """An article read back from MongoDB, which adds its ObjectId."""

    _id: ObjectId


class BriefingStory(TypedDict):
    """One selected story embedded in a daily briefing."""

    section: str
    title: str
    summary: str
    why_it_matters: str
    source: str
    url: str | None
    category: str
    published_at: datetime | None
    importance_score: int


class DailyBriefing(TypedDict):
    """A generated daily briefing ready to store in MongoDB."""

    briefing_date: str
    generated_at: datetime
    total_news: int
    categories: dict[str, int]
    top_news: list[BriefingStory]
    learning_of_day: str
    career_opportunity: str


class SavedDailyBriefing(DailyBriefing, total=False):
    """A briefing read back from MongoDB with its metadata fields."""

    _id: ObjectId
    created_at: datetime
