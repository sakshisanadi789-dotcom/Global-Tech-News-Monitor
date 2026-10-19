"""Project interview questions with answers based on the implementation."""


QUESTIONS_AND_ANSWERS: tuple[tuple[str, str], ...] = (
    (
        "1. Explain the complete project flow.",
        (
            "The browser dashboard is served by Flask from templates/index.html. "
            "When the dashboard requests /news, Flask queries MongoDB and returns "
            "the saved articles as JSON. The browser renders those articles. "
            "News collection is a separate background flow: APScheduler triggers "
            "run_daily_news_job(), which connects to MongoDB, calls GNews, "
            "normalizes and categorizes valid articles, stores new articles, "
            "generates the daily briefing, and closes the MongoDB client. The "
            "dashboard can then retrieve the newly saved articles through Flask's "
            "REST API."
        ),
    ),
    (
        "2. Why is a scheduler needed, and how does it trigger a Python function?",
        (
            "Without a scheduler, the news collection function would need to be "
            "started manually. APScheduler lets the application run that work at "
            "configured times in the background while Flask continues serving "
            "requests. In scheduler.py, start_scheduler() creates a "
            "BackgroundScheduler, creates a CronTrigger from the configured hour, "
            "minute, and timezone, and registers run_daily_news_job as the "
            "callable for the job ID daily-tech-news-briefing. Calling "
            "scheduler.start() starts its background thread. When the trigger "
            "becomes due, APScheduler calls run_daily_news_job(); that function "
            "fetches, stores, and briefs the news. The dashboard can also change "
            "this running job to one of four interval triggers: one minute, five "
            "minutes, one hour, or one day. The scheduler does not make new "
            "stories exist; it periodically asks GNews for available results. "
            "The dashboard-selected interval is held in memory, so restarting "
            "the application restores the configured daily schedule."
        ),
    ),
    (
        "3. What happens if the server is stopped at 6 AM and the schedule is 7 AM?",
        (
            "If the application starts again before 7 AM, its scheduler starts "
            "and the 7 AM run can happen normally. If the application is stopped "
            "when 7 AM arrives, the function cannot run because the scheduler "
            "exists only inside the running application process. This project "
            "uses an in-memory scheduler and does not persist missed jobs. "
            "Restarting after 7 AM therefore does not catch up on that run; with "
            "the default daily schedule it waits until the next scheduled day. "
            "The configured one-hour misfire grace period can allow a delayed "
            "job while the scheduler process is still running, but it does not "
            "recover a job lost while the process was stopped. Keep the "
            "application running, or use a persistent/external scheduler if "
            "jobs must survive downtime."
        ),
    ),
    (
        "4. How does the project prevent duplicate news in MongoDB?",
        (
            "database.py creates a unique MongoDB index named "
            "unique_article_url on the news collection's url field. When "
            "store_news() inserts an article, MongoDB rejects an insert whose "
            "URL already exists by raising DuplicateKeyError. The service catches "
            "that specific error and increments the duplicates count, while "
            "other database errors are logged and re-raised. This prevents "
            "duplicate documents with the same URL, including across later "
            "collection runs. It does not identify the same story published "
            "under different URLs. The daily_briefings collection separately "
            "has a unique index on briefing_date so there is at most one saved "
            "briefing document per date."
        ),
    ),
    (
        "5. How does news travel from the external API through Python and "
        "MongoDB to REST API and Postman?",
        (
            "1) APScheduler calls run_daily_news_job(). 2) fetch_news() sends an "
            "HTTP GET request to the configured GNews search endpoint with the "
            "query, English language, published-date sort, maximum result count, "
            "and API key from configuration. It uses a timeout and reports "
            "request, HTTP, JSON, or response-shape failures rather than "
            "treating them as successful results. 3) Each returned article is "
            "checked for a usable title, HTTP(S) URL, and source. Python "
            "normalizes its fields, parses the publication date, assigns a "
            "category, and records collected_at. Invalid article entries are "
            "skipped. 4) store_news() inserts each normalized document into "
            "MongoDB's tech_news.news collection; MongoDB assigns an _id and the "
            "unique URL index rejects repeats. 5) The same job reads stored "
            "articles to build and save the daily briefing in "
            "tech_news.daily_briefings. 6) Flask routes such as GET /news, "
            "GET /news/search?keyword=python, and GET /news/category/AI query "
            "MongoDB, serialize ObjectId and datetime values for JSON, and "
            'return a response such as {"news": [...], "count": 1}. Flask '
            "serves the same routes when called from the browser or Postman. "
            "Postman is only an HTTP client for testing: send GET "
            "http://127.0.0.1:5000/news after the application is running to "
            "see the saved data. Postman does not fetch from GNews or insert "
            "articles by itself."
        ),
    ),
)


def print_questions_and_answers() -> None:
    """Print the project questions and their implementation-specific answers."""
    for question, answer in QUESTIONS_AND_ANSWERS:
        print(f"{question}\n{answer}\n")


if __name__ == "__main__":
    print_questions_and_answers()
