"""Load and validate application settings from environment variables."""

import os

from dotenv import load_dotenv


load_dotenv()


def _read_integer_setting(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Read an integer setting and check that it is within its allowed range."""
    value = os.getenv(name, str(default))

    try:
        number = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a whole number.") from error

    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")

    return number


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "tech_news")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")
GNEWS_API_URL = os.getenv(
    "GNEWS_API_URL",
    "https://gnews.io/api/v4/search",
)
GNEWS_QUERY = os.getenv(
    "GNEWS_QUERY",
    'technology OR "artificial intelligence" OR cybersecurity OR '
    '"cloud computing" OR "quantum computing" OR "developer tools" OR startup',
)
NEWS_SCHEDULE_HOUR = _read_integer_setting(
    "NEWS_SCHEDULE_HOUR",
    default=6,
    minimum=0,
    maximum=23,
)
NEWS_SCHEDULE_MINUTE = _read_integer_setting(
    "NEWS_SCHEDULE_MINUTE",
    default=0,
    minimum=0,
    maximum=59,
)
NEWS_SCHEDULE_TIMEZONE = os.getenv("NEWS_SCHEDULE_TIMEZONE", "Asia/Kolkata")
