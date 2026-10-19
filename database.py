"""Connect to MongoDB and prepare the project collections."""

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from config import MONGODB_DATABASE, MONGODB_URI


def connect_to_mongodb() -> tuple[MongoClient, Database]:
    """Connect to MongoDB, verify the connection, and create unique indexes."""
    client = None

    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
        )
        client.admin.command("ping")

        database = client[MONGODB_DATABASE]
        database["news"].create_index(
            [("url", ASCENDING)],
            unique=True,
            name="unique_article_url",
        )
        database["daily_briefings"].create_index(
            [("briefing_date", ASCENDING)],
            unique=True,
            name="unique_briefing_date",
        )
    except PyMongoError as error:
        if client is not None:
            client.close()
        raise ConnectionError(
            "Could not connect to MongoDB or prepare its indexes. "
            "Check the MongoDB service and MONGODB_URI."
        ) from error

    return client, database
