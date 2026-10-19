# Daily Global Tech News Scheduler

> **Learning project for BCA freshers.** The first implementation is complete, with a step-by-step explanation below. Automated tests use mocked external services; the live MongoDB, GNews, and Postman demonstration still needs to be run with your own setup and credentials.

## Project objective

Build a small Python application that collects technology news from GNews, stores articles in MongoDB, and prepares a concise daily briefing for learners following important global technology developments.

The project is intended to teach practical Python, REST APIs, JSON, environment variables, scheduling, and MongoDB. It will use a simple, single-application design—not microservices, Docker, or Kubernetes.

## Technologies

- Python
- MongoDB and PyMongo
- Requests for HTTP API calls
- Flask for the REST API
- APScheduler for the daily job
- JSON
- VS Code and Postman
- MongoDB Compass for inspecting saved data

Flask is used for the REST API and GNews is the configured news provider. API keys and connection details are supplied through environment variables, not committed to Git.

## News coverage

The briefing will focus on:

- Artificial intelligence and agentic AI
- Quantum computing
- Cloud computing and software architecture
- Cybersecurity
- Programming and developer tools
- Startups, technology business, and major technology companies
- Important technology trends

Articles are categorized with editable keyword lists. Categories are **AI**, **Agentic AI**, **Quantum Computing**, **Cloud**, **Cybersecurity**, **Programming**, **Developer Tools**, **Startups**, **Technology Companies**, and **Other Technology**.

## Project structure

```text
daily-tech-news/
├── main.py                 # Start the REST API and scheduler
├── templates/
│   └── index.html          # Simple browser dashboard
├── config.py               # Read and validate environment settings
├── database.py             # Connect to MongoDB and create indexes
├── news_service.py         # Fetch, normalize, categorize, and save news
├── scheduler.py            # Run the daily collection and briefing job
├── briefing_service.py     # Score stories and generate the briefing
├── refresh_briefing.py     # Manually regenerate today's briefing
├── models.py               # Keep the article and briefing data shapes clear
├── tests/
│   └── test_project.py     # Offline tests using mocked API and database calls
├── requirements.txt
├── .env.example            # Safe example settings; no real secrets
├── .gitignore
└── README.md
```

## Architecture and data flow

1. At the configured time (default: 6:00 AM), APScheduler starts the daily job.
2. `news_service.py` requests news from GNews, validates the JSON response, and normalizes the article fields.
3. Articles are categorized using configurable keyword rules and inserted into MongoDB. A unique index on the article URL prevents the same URL being stored more than once.
4. `briefing_service.py` reads the collected articles, scores them by topic relevance and recency, and selects the strongest stories for the briefing.
5. The briefing is saved in MongoDB and printed in the terminal. The REST API serves saved news and briefings as JSON.
6. Learners can inspect documents and indexes in MongoDB Compass and test API requests in Postman.

The relevance score is simple, deterministic, and explainable: article category contributes fixed importance points, and newer articles receive a recency advantage. Articles are not chosen randomly. A unique URL only catches repeated links; it cannot guarantee that different URLs do not describe the same underlying story.

## MongoDB plan

Database: `tech_news`

### `news` collection

Article fields:

```json
{
  "title": "Example technology headline",
  "description": "A short description from the news source.",
  "source": "Example News",
  "author": null,
  "url": "https://example.com/news/article",
  "category": "AI",
  "published_at": "2026-10-18T08:30:00Z",
  "collected_at": "2026-10-18T09:00:00Z"
}
```

MongoDB assigns an `_id` (`ObjectId`) to each document. A unique index is created on `url`.

### `daily_briefings` collection

Briefing fields include `briefing_date`, `generated_at`, `total_news`, category counts, selected `top_news`, learning and career suggestions, and `created_at`. A unique index on `briefing_date` keeps one saved briefing per date.

MongoDB documents are BSON records, a JSON-like format. The steps demonstrate inserting, finding, filtering, and sorting records, as well as viewing collections and indexes in MongoDB Compass. Update and delete operations are not part of the application's current API.

## Daily briefing format

The generated briefing includes:

1. AI
2. Agentic AI
3. Quantum computing
4. Cloud and software
5. Cybersecurity
6. Technology business
7. Learning of the day
8. Career opportunity

Each selected story has a headline, source description (or a note if no description was supplied), a category-based explanation of why it matters, and its source link. Learning and career suggestions are simple category-based prompts; they are not personalized advice or facts generated from the article. The current version does not generate new summaries or guarantee a ten-minute reading time.

## REST API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check whether the application is running |
| `GET` | `/news` | Return the latest news |
| `GET` | `/news/{id}` | Return one article |
| `GET` | `/news/category/{category}` | Filter news by category |
| `GET` | `/news/search?keyword=python` | Search title, description, and category |
| `GET` | `/briefings` | Return previous daily briefings |
| `GET` | `/briefings/{date}` | Return a briefing for a date |

Responses use JSON and appropriate HTTP status codes. Errors are clear without exposing credentials or internal exception details. Endpoint examples and sample responses are documented in Step 7 below.

## Configuration and error handling

Settings will be read from environment variables, including:

- `MONGODB_URI` (default `mongodb://localhost:27017`)
- `MONGODB_DATABASE` (default `tech_news`)
- `GNEWS_API_KEY` (required to fetch news)
- `GNEWS_API_URL` (GNews search endpoint by default)
- `GNEWS_QUERY` (default technology topics)
- `NEWS_SCHEDULE_HOUR` (default `6`) and `NEWS_SCHEDULE_MINUTE` (default `0`)
- `NEWS_SCHEDULE_TIMEZONE` (default `Asia/Kolkata`)

The application will handle network timeouts, API failures, invalid JSON, empty results, MongoDB connection problems, duplicate URLs, missing articles, invalid dates, and unsupported categories. Real secrets belong in a local `.env` file, which must be ignored by Git; only `.env.example` with placeholder values should be committed.

### First-time setup (Windows / VS Code)

1. Install Python, MongoDB Community Server (or create an authorized MongoDB Atlas database), MongoDB Compass, VS Code, and Postman. Start the MongoDB server if using a local installation.
2. Open the project folder in VS Code and open a PowerShell terminal at the repository root.
3. Create and activate a Python virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If activation is unavailable in your terminal, run `.venv\Scripts\python.exe` directly in place of `python` in the following commands.
4. Install the packages:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Copy the example configuration and edit the local copy:

   ```powershell
   Copy-Item .env.example .env
   ```

   Create a GNews account at [gnews.io/register](https://gnews.io/register), verify your email, and copy the key from your GNews dashboard. Set `GNEWS_API_KEY` to that key in `.env`. Keep the real key private; `.env` is ignored by Git. For MongoDB Atlas, set `MONGODB_URI` to your authorized connection string and ensure your network access and database user are configured. Do not paste credentials into source files or public screenshots.
6. Check `NEWS_SCHEDULE_HOUR`, `NEWS_SCHEDULE_MINUTE`, and `NEWS_SCHEDULE_TIMEZONE` in `.env`. The defaults are 6:00 AM in `Asia/Kolkata`.
7. Run offline tests:

   ```powershell
   python -m unittest discover -s tests -v
   ```

8. Start the application:

   ```powershell
   python main.py
   ```

   This connects to MongoDB, starts the background scheduler, and serves the browser dashboard and Flask API at `http://127.0.0.1:5000`. The dashboard lets you choose an automatic news collection interval (one minute, five minutes, one hour, or one day); it refreshes the displayed articles shortly after each collection. The selected interval applies while the application process is running. The default schedule remains the configured daily time until changed in the dashboard.

   To change the schedule, choose an interval under **Automatically collect news** and select **Save schedule**. The browser refreshes the article list automatically after the scheduled collection, so no manual reload is needed. Choose longer intervals for routine use; one-minute collection makes frequent requests to GNews and may use up your provider quota. The app must remain running, and MongoDB and a valid GNews API key must be available.

For a first end-to-end run without waiting for the schedule, leave `python main.py` running, open a second terminal, and run:

```powershell
python -c "from scheduler import run_daily_news_job; print(run_daily_news_job())"
```

This makes a real GNews request and writes to the configured MongoDB database. Confirm the operation in the terminal and MongoDB Compass. Then use the Postman examples in Step 7. Stop the Flask application with Ctrl+C.

## Learning stages

The project will be built incrementally. Each stage will explain what is being built and why, the Python and MongoDB concepts involved, the data flow, how to run and test the code, common errors, and five related interview questions. Before continuing to the next stage, learners will be asked to explain the code in their own words.

Topics will include Python variables, data types, lists, dictionaries, tuples, sets, functions, loops, conditionals, exceptions, modules, JSON, file handling, environment variables, API requests, dates and times, and scheduling. MongoDB topics will include databases, collections, documents, `ObjectId`, CRUD operations, queries, filtering, sorting, and unique indexes.

## Steps 1–2: Application configuration

The first implementation step is `config.py`. It reads local settings from environment variables, supplies beginner-friendly defaults for local MongoDB and the 6:00 AM schedule, and checks that the schedule hour and minute are valid. `python-dotenv` loads settings from a local `.env` file. Copy `.env.example` to `.env` when setting up locally; `.env` is ignored by Git and must not contain values committed to the repository.

Install the current step's dependency from the project folder:

```text
python -m pip install -r requirements.txt
```

The configuration can be checked without connecting to MongoDB:

```text
python -c "import config; print(config.MONGODB_DATABASE, config.NEWS_SCHEDULE_HOUR, config.NEWS_SCHEDULE_MINUTE, config.NEWS_SCHEDULE_TIMEZONE)"
```

In Step 1, there was no MongoDB operation. Step 3 below adds the actual connection; an unset `MONGODB_URI` still defaults to a local MongoDB server.

### Concepts in this step

- **Python:** modules, imports, environment variables, strings and integers, functions, parameters, return values, conditionals, and exceptions.
- **MongoDB:** database name and connection URI as configuration concepts only; connection, collections, documents, and Compass inspection come in a later step.
- **Data flow:** `.env` or the process environment → `config.py` → validated settings used by the database and scheduler modules.

### Run and test

1. Install dependencies with the command above.
2. Optionally copy `.env.example` to `.env` and change the schedule values.
3. Run the configuration check command above. It should print the database name, hour, minute, and timezone.
4. Try setting `NEWS_SCHEDULE_HOUR=25` in `.env` and rerun the check. It should stop with a clear `ValueError`; restore the valid setting afterward.

**Common errors:** `ModuleNotFoundError: dotenv` means the requirements were not installed in the active Python environment. A schedule `ValueError` means the hour/minute is not a whole number or is outside its valid range. A successful config check does not prove MongoDB is installed, reachable, or authenticated.

### Interview questions

1. What is an environment variable, and why should secrets be kept out of source code?
2. What does `load_dotenv()` do?
3. Why does this configuration convert schedule values from strings to integers?
4. What is the purpose of validating the allowed range for an hour and a minute?
5. Does setting a MongoDB URI prove the database connection works? Why or why not?

**Steps 1–2 checkpoint:** explain what `config.py` reads, why it validates the schedule, and what it does not yet verify about MongoDB.

## Step 3: MongoDB connection and unique indexes

`database.py` connects to the MongoDB URI from `config.py`, sends a `ping` command to verify the server responds, selects the `tech_news` database, and creates the `news` and `daily_briefings` collections' unique indexes. MongoDB creates a collection when its first document is inserted; creating an index prepares the collection and does not insert news documents.

The `news.url` unique index prevents two documents from having the same article URL. The `daily_briefings.briefing_date` unique index permits at most one briefing document for a date. The connection uses a five-second server-selection timeout so an unavailable server does not make startup wait indefinitely. Connection and index setup failures raise a clear `ConnectionError` without including the URI or credentials in its message.

### Concepts in this step

- **Python:** imports, modules, a function with a return value, tuples, and handling an exception while preserving its cause.
- **MongoDB:** a database contains collections; collections contain documents; `MongoClient` manages a connection; a `ping` checks server responsiveness; an ascending unique index enforces uniqueness.
- **Data flow:** `config.py` supplies URI and database name → `database.py` connects and checks the server → index setup → returns the client and database for later application modules.

### Run and test

1. Make sure MongoDB is running locally, or set `MONGODB_URI` in your ignored `.env` to a MongoDB server you are authorized to use.
2. Install the project's dependencies:

   ```text
   python -m pip install -r requirements.txt
   ```

3. From the project folder, connect and print the database name:

   ```text
   python -c "from database import connect_to_mongodb; client, database = connect_to_mongodb(); print('Connected to:', database.name); client.close()"
   ```

   A successful connection prints `Connected to: tech_news`. In MongoDB Compass, connect using the same URI and refresh the database list. The index setup creates the collections if needed; inspect the indexes on `news` and `daily_briefings`. They may contain no documents yet.

**Common errors:** `ConnectionError` usually means MongoDB is stopped, the URI is wrong, the network is unavailable, or credentials are invalid. `ModuleNotFoundError: pymongo` means dependencies were not installed in the Python environment running the command. A unique-index creation error can mean existing documents already contain duplicate URLs or briefing dates; resolve those duplicates before creating the index. This step does not yet insert, fetch, or delete article documents.

### Interview questions

1. What is the difference between a MongoDB database, collection, and document?
2. What does `MongoClient` do, and what does the `ping` command verify?
3. Why is the article URL a useful field for a unique index?
4. What does a unique index do when an insert repeats an existing indexed value?
5. Why does `connect_to_mongodb()` return both a client and a database?

**Step 3 checkpoint:** explain what the `ping` checks, what each unique index prevents, and why the function returns both the client and the database.

## Step 4: Fetch, categorize, and store news

`news_service.py` uses the GNews `/api/v4/search` endpoint. It sends the configured search query, requests recent English-language articles, validates the JSON response, converts each usable article into the project's MongoDB document shape, assigns a keyword category, and inserts it into the `news` collection supplied by the caller. This version requests at most 10 results per call (`max=10`).

Create a GNews account to obtain an API key, then set `GNEWS_API_KEY` in your local `.env` file. Do not put a real key in `.env.example` or commit `.env`. `GNEWS_API_URL` and `GNEWS_QUERY` can also be changed through environment variables. The default query covers technology, AI, cybersecurity, cloud, quantum computing, developer tools, and startups. If you previously configured `NEWS_API_KEY`, rename it to `GNEWS_API_KEY` in your private `.env`.

The GNews response supplies title, description, source, URL, and publication date. The normalizer keeps these fields plus category and collection date; the standard GNews search article shape does not include an author, so `author` is stored as `null`. Description and publication date may be unavailable; an article with no title, valid HTTP(S) URL, or source name is skipped with a warning. The publication date becomes a Python datetime so PyMongo stores it as a BSON date. Keyword categories are listed in `CATEGORY_KEYWORDS` in `news_service.py`; specific categories are checked before broader AI matches.

`store_news()` inserts articles individually, relying on the unique URL index created in Step 3. It returns the number inserted and the number skipped as duplicates. An empty article list is safe and returns zero counts. API and malformed-response failures raise a safe `GNewsError`; MongoDB insertion failures are logged and re-raised rather than silently ignored.

### Concepts in this step

- **Python:** modules and imports, lists and dictionaries, loops, functions, parameters and return values, conditionals, exceptions, logging, environment variables, and date/time parsing.
- **MongoDB:** documents, collections, insert operations, and enforcing uniqueness with an index.
- **Data flow:** `.env` → `config.py` → HTTP request to GNews → JSON validation and normalization → keyword categorization → `database["news"]` insert → duplicate counts.

### Run and test

1. Set a valid `GNEWS_API_KEY` in your local `.env` and install requirements:

   ```text
   python -m pip install -r requirements.txt
   ```

2. With MongoDB running, test one fetch and insert from the project folder:

   ```text
   python -c "from database import connect_to_mongodb; from news_service import fetch_news, store_news; client, database = connect_to_mongodb(); articles = fetch_news(); print('Fetched:', len(articles)); print('Stored:', store_news(database['news'], articles)); client.close()"
   ```

3. Run the command again. Articles with URLs already in MongoDB should be reported in the `duplicates` count. Open MongoDB Compass and inspect the `tech_news.news` collection.

Do not share your API key in terminal screenshots or Postman collections. This step makes a real GNews API request when `fetch_news()` runs; tests can instead mock the HTTP response to avoid depending on a live API key or network.

**Common errors:** An unset or invalid GNews key results in a `GNewsError` (the provider may respond with an HTTP error). A timeout or network issue results in a safe request error. Invalid JSON and an unexpected response structure are rejected. Zero results is valid and produces an empty list. If insert reports duplicates, the unique URL index is working. MongoDB must be reachable before inserting.

### Interview questions

1. What is the difference between JSON text and a Python dictionary?
2. Why does a function use a timeout for an HTTP request?
3. Why are keyword categories ordered from specific to broad?
4. What is the difference between `published_at` and `collected_at`?
5. How does a unique MongoDB index help prevent duplicate article URLs?

**Step 4 checkpoint:** explain how the JSON response becomes a MongoDB document, how an article gets its category, and how the code handles a repeated article URL.

## Step 5: Score stories and generate a daily briefing

`briefing_service.py` reads news collected during the current local calendar day, using `NEWS_SCHEDULE_TIMEZONE` to calculate that day's UTC query boundaries. It counts articles by category and builds briefing sections for AI, agentic AI, quantum computing, cloud and software, cybersecurity, and technology business.

The scoring rule is intentionally small and explainable: each category has a fixed importance score, then an article receives up to five extra points for recency. The category points are 10 for agentic AI and quantum, 9 for cybersecurity and AI, 8 for cloud and major technology companies, 7 for startups and developer tools, 6 for programming, and 3 for other technology. Recency adds 5 points if under one day old, 4 under two days, 3 under three days, 2 under seven days, 1 under fourteen days, and 0 otherwise. The service sorts each section by score and publication time (using URL as a stable tie-breaker), then chooses at most two stories per section. This makes selection deterministic, not random. This score is only a beginner-friendly ranking heuristic, not a claim that it understands real-world impact.

Each selected story uses the source description as its summary. When a description is missing, the briefing says it is based on the headline only. “Why it matters,” the learning topic, and career skills are simple category-based prompts; they are not facts inferred from the source. The generated document includes the briefing date, generation time, article count, category counts, selected stories, learning suggestion, and career suggestion.

The service upserts one document per `briefing_date`, so rerunning the job updates that day's briefing without violating the unique briefing-date index. The first `created_at` timestamp is preserved. `format_briefing()` creates readable terminal output; `print_briefing()` prints it. The `tzdata` dependency provides IANA timezone data on Windows systems that do not include it by default.

### Concepts in this step

- **Python:** functions, dictionaries and lists, sorting with a key, loops, conditionals, date and time, timezone-aware datetimes, and exception handling.
- **MongoDB:** `find()` with a date-range query, counting grouped values in Python, and `update_one()` with `$set`, `$setOnInsert`, and `upsert=True`.
- **Data flow:** daily articles in `news` → local-day date filter → score and select by section → construct briefing document → upsert in `daily_briefings` → format for terminal.

### Run and test

1. Ensure MongoDB is running and has articles collected today, then run this from the project folder:

   ```text
   python -c "from database import connect_to_mongodb; from briefing_service import generate_daily_briefing, print_briefing; client, database = connect_to_mongodb(); briefing = generate_daily_briefing(database['news'], database['daily_briefings']); print_briefing(briefing); client.close()"
   ```

2. Inspect `tech_news.daily_briefings` in MongoDB Compass. Run the command again and confirm the collection still has one briefing for today's date.
3. If there are no articles collected today, a briefing is still saved with zero stories, helpful empty-section messages, and general learning/career suggestions.

**Common errors:** An invalid timezone name causes a clear `ValueError`. MongoDB read/write problems are logged and re-raised. An article missing a description uses an explicit headline-only note. If your MongoDB articles use a different `collected_at` field shape, they will not match the date-range query. A rerun updates the briefing content; it does not create a second briefing for that date.

### Interview questions

1. Why does the service filter by `collected_at` rather than `published_at` to form the daily batch?
2. How does the score combine category importance and recency?
3. Why are article descriptions used instead of inventing summaries?
4. What does MongoDB `upsert=True` do?
5. Why are timezone-aware day boundaries useful for a scheduled briefing?

**Before moving to the next step, explain how the service chooses stories, what the score means, and how rerunning generation affects the saved briefing.**

## Step 6: Schedule news collection

`scheduler.py` connects the existing services into one background job. By default, APScheduler runs `run_daily_news_job()` at `NEWS_SCHEDULE_HOUR` and `NEWS_SCHEDULE_MINUTE` in `NEWS_SCHEDULE_TIMEZONE`. From the dashboard, the schedule can be changed to every minute, five minutes, one hour, or one day. The job opens MongoDB, fetches and stores news, creates and prints the briefing, reports the fetch/insert/duplicate counts, and closes the MongoDB client even if an operation fails.

The scheduler runs in the background alongside the REST API in the same process. Starting it does not immediately fetch news; the first run is at the next configured schedule time. Changing the interval in the dashboard starts the new interval from that change. The dashboard automatically reloads its article list shortly after each scheduled collection. `max_instances=1` prevents overlapping copies of the job within this scheduler, and the one-process learning setup avoids separate app instances each starting their own scheduler. `stop_scheduler()` waits for an active job before shutting down.

### Concepts in this step

- **Python:** importing and calling functions from modules, `try`/`finally` for resource cleanup, logging, and background execution.
- **MongoDB:** the scheduled job reuses the connection, collections, unique indexes, inserts, and briefing upsert from earlier steps.
- **Data flow:** APScheduler clock → daily job → connect to MongoDB → fetch and store → generate and print briefing → close database client.

### Run and test

1. Confirm MongoDB is available and `GNEWS_API_KEY` is set in your local `.env`. Install the project requirements:

   ```text
   python -m pip install -r requirements.txt
   ```

2. Start the scheduler from the project folder:

   ```text
   python -c "import time; from scheduler import start_scheduler; scheduler = start_scheduler(); print('Scheduler is running. Press Ctrl+C to stop.'); time.sleep(60)"
   ```

   This keeps the process alive for one minute to demonstrate scheduler startup; it does not force a job to run immediately. To test the job manually, use:

   ```text
   python -c "from scheduler import run_daily_news_job; print(run_daily_news_job())"
   ```

   The manual command performs real API and MongoDB operations. Check the terminal output and MongoDB Compass for inserted articles and the saved daily briefing. Start the full application to try the four schedule intervals in the dashboard. One-minute collection makes frequent requests to GNews and may use up your provider quota.

**Common errors:** A missing API key, network/API problem, or MongoDB failure causes the job to fail and APScheduler logs the exception; the scheduler remains active for its next run. An invalid timezone prevents startup with a clear `ValueError`. If the process exits, the background scheduler stops. Do not start multiple application instances with a scheduler unless you intentionally coordinate them; the one-instance setup is for learning.

### Interview questions

1. What is the difference between a scheduled background job and a function called directly?
2. When will the first scheduled job run after `start_scheduler()`?
3. Why does the job close the MongoDB client in a `finally` block?
4. What does `max_instances=1` prevent?
5. Why should this beginner setup run only one application instance with a scheduler?

**Before moving to the next step, explain when the job runs, the order of operations inside it, and how the MongoDB client is closed if an operation fails.**

## Step 7: REST API with Flask

`main.py` exposes the saved articles and briefings through simple GET endpoints, provides a schedule endpoint for the dashboard, and serves the browser dashboard at `/`. Starting the application with `python main.py` connects to MongoDB, starts one background scheduler, and runs Flask at `http://127.0.0.1:5000`. Open that address in a browser to use the dashboard, or keep the terminal running while sending requests from Postman. Stop with Ctrl+C; the scheduler and API's MongoDB client are then shut down.

The dashboard in `templates/index.html` shows recent articles, lets a reader search by keyword or filter by category, and provides the automatic collection interval controls. It calls the same JSON API routes tested with Postman and reloads articles after each scheduled collection. Article text is inserted into the page using `textContent`, not interpreted as HTML.

### Endpoints

| Method | Endpoint | Purpose | Successful response |
|---|---|---|---|
| `GET` | `/health` | Check the API and MongoDB ping | `200` |
| `GET` | `/news?limit=20` | Latest articles, newest first | `200` |
| `GET` | `/news/<id>` | One article by MongoDB ObjectId | `200` |
| `GET` | `/news/category/<category>` | Articles in a known category | `200` |
| `GET` | `/news/search?keyword=python` | Search title, description, and category | `200` |
| `GET` | `/briefings?limit=10` | Previous briefings, newest first | `200` |
| `GET` | `/briefings/<YYYY-MM-DD>` | One briefing by date | `200` |

List endpoints accept a `limit` from 1 to 100. Responses convert MongoDB ObjectIds to strings and dates to ISO-formatted strings. Article responses call the ObjectId field `id`.

### Example Postman requests

After starting the app, set Postman's method to **GET** and try:

```text
http://127.0.0.1:5000/health
http://127.0.0.1:5000/
http://127.0.0.1:5000/news?limit=5
http://127.0.0.1:5000/news/search?keyword=python
http://127.0.0.1:5000/news/category/AI
http://127.0.0.1:5000/briefings
http://127.0.0.1:5000/briefings/2026-10-18
```

Copy an article's `id` from the `/news` response to test `/news/<id>`. Use a category exactly as shown in `news_service.py`, such as `Quantum%20Computing` for a URL-encoded space.

Example `/news` response:

```json
{
  "news": [
    {
      "id": "671234567890abcdef123456",
      "title": "Example AI development",
      "description": "A short description from the source.",
      "source": "Example News",
      "author": null,
      "url": "https://example.com/ai-story",
      "category": "AI",
      "published_at": "2026-10-18T08:30:00+00:00",
      "collected_at": "2026-10-18T09:00:00+00:00"
    }
  ],
  "count": 1
}
```

Example `/health` response:

```json
{
  "status": "ok",
  "database": "connected"
}
```

Example `/briefings/2026-10-18` response:

```json
{
  "briefing_date": "2026-10-18",
  "generated_at": "2026-10-18T00:30:00+00:00",
  "total_news": 1,
  "categories": {
    "AI": 1
  },
  "top_news": [
    {
      "section": "AI",
      "title": "Example AI development",
      "summary": "A short description from the source.",
      "why_it_matters": "AI developments can change how people build software and solve problems.",
      "source": "Example News",
      "url": "https://example.com/ai-story",
      "category": "AI",
      "published_at": "2026-10-18T08:30:00+00:00",
      "importance_score": 14
    }
  ],
  "learning_of_day": "Explore how a machine-learning model is trained and evaluated.",
  "career_opportunity": "Relevant skills to explore: machine learning and AI application development.",
  "created_at": "2026-10-18T00:30:00+00:00"
}
```

### Status codes and errors

- `400 Bad Request`: invalid ObjectId, category, date, keyword, or `limit`.
- `404 Not Found`: article or briefing does not exist, or the endpoint is unknown.
- `503 Service Unavailable`: MongoDB cannot serve the request or health check.
- `200 OK`: request succeeded, including list endpoints with no matching results (empty list and `count: 0`).

Error responses contain a simple message and do not include MongoDB connection details. The health endpoint checks MongoDB with `ping`; it returns `503` if MongoDB is unavailable.

### Concepts in this step

- **Python:** modules, functions, dictionaries, request parameters, conditionals, exception handling, JSON serialization, and application startup.
- **MongoDB:** `find()`, `find_one()`, query filters, sorting, limits, and ObjectIds.
- **Data flow:** Postman HTTP GET → Flask route and input validation → MongoDB query → convert BSON values to JSON-safe values → HTTP status and JSON response.

**Common errors:** If the app cannot start, check MongoDB and `MONGODB_URI`. An article ID must be copied from the response and be a valid ObjectId. Encode spaces in category URL paths. An empty list is a successful query with no matches, not a server failure. Ensure the Flask process remains running while testing in a browser or Postman.

### Interview questions

1. What is a REST endpoint, and why does this project use GET for these routes?
2. Why does the API convert MongoDB ObjectIds and datetimes before returning JSON?
3. When should an API return `400`, `404`, or `503`?
4. How does a MongoDB filter differ from fetching every document?
5. Why should an API error response avoid exposing connection strings or exception details?

**Before moving to the next step, explain how a Postman request travels through a Flask route to MongoDB and back as a JSON response, and give an example of when the API returns a 400, 404, and 503 status.**

## Browser UI test

`tests/test_ui.py` launches the Flask dashboard with mocked MongoDB data and uses Playwright Chromium to verify that the dashboard loads, renders an article, submits a keyword search, and displays the article link. It exercises a real browser and a local Flask HTTP server, but uses sample data rather than a live database.

Install the project requirements and the Playwright browser once:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Then run the browser UI test from the project folder:

```powershell
$env:RUN_BROWSER_TESTS = "1"
python -m unittest discover -s tests -p "test_ui.py" -v
```

Unset the opt-in flag when finished:

```powershell
Remove-Item Env:RUN_BROWSER_TESTS
```

The browser test is opt-in, so the regular offline unit-test command does not start a browser. If Chromium is not installed, run the Playwright install command above. This UI test verifies browser interactions with mocked data; a live application check still requires a running MongoDB and GNews credentials.

## Step 8: Describe the document shapes

`models.py` defines `TypedDict` types for normalized news articles, articles saved in MongoDB, selected briefing stories, and daily briefings. These types document the keys and value types used by the application. `news_service.py` uses `NewsArticle` for the normalized return value and the articles passed to the insert function.

`TypedDict` is for static type checking and editor help; it does not validate data at runtime or change how MongoDB stores it. MongoDB adds `_id` when an article is inserted, so the saved-document type includes that field separately. The briefing type describes the stored values before MongoDB adds its document identifier and creation timestamp.

### Concepts in this step

- **Python:** modules, imports, type annotations, dictionaries, and optional values such as a missing description or publication date.
- **MongoDB:** a document is a key/value record; the type definitions describe the expected document shape but do not replace MongoDB validation.
- **Data flow:** GNews JSON → normalized dictionary described by `NewsArticle` → MongoDB insert and generated `_id`; selected story dictionaries → daily briefing document.

### Run and test

From the project folder, run:

```text
python -c "from datetime import UTC, datetime; from models import NewsArticle; article: NewsArticle = {'title': 'Example', 'description': None, 'source': 'Example News', 'author': None, 'url': 'https://example.com/article', 'category': 'AI', 'published_at': None, 'collected_at': datetime.now(UTC)}; print(article)"
```

The existing `news_service.py` normalizer is annotated to return this shape. The runtime values are still ordinary Python dictionaries; no database connection is needed for this check.

**Common errors:** A `TypedDict` declaration does not check an incoming API response at runtime—that is why `news_service.py` still validates the actual JSON fields. When adding or renaming a stored field, update both the producer code and its document type.

### Interview questions

1. What is a `TypedDict`, and how is it different from a regular dictionary?
2. Does a type annotation validate a GNews response at runtime?
3. Why does MongoDB add an `_id` field?
4. Why can `published_at` be optional while `collected_at` is required?
5. When should a document shape and its type annotation be updated together?

**Step 8 checkpoint:** explain what `TypedDict` documents, what it does not validate, and why a saved MongoDB article has an `_id` not supplied by GNews.

## Step 9: Test the complete project flow

`tests/test_project.py` uses Python's built-in `unittest` framework and mocks the external GNews and MongoDB dependencies. These tests check article normalization and categories, API failure cases, duplicate handling, briefing selection and date filtering, scheduled job order and connection cleanup, REST responses, and validation errors.

Automated tests make repeatable checks without spending an API quota or requiring a running MongoDB server. They do not prove credentials, network access, MongoDB indexes, or live GNews behavior; use the manual run instructions and Postman/Compass demonstration for those.

### Concepts in this step

- **Python:** test cases, assertions, setup methods, and mocking functions that would otherwise call external services.
- **MongoDB:** tests verify expected query filters, unique-index duplicate handling, and briefing upsert calls without a real database.
- **Data flow:** test input → mocked source/database boundary → real service or route code → assert the returned value and expected side effects.

### Run and test

From the project folder, install dependencies and run:

```text
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Every test should report `ok`, followed by `OK`. Tests require no `.env`, GNews API key, or running MongoDB server. For the live project demonstration, start MongoDB, set a real key in `.env`, run `python main.py`, then use Postman and MongoDB Compass as described above.

**Common errors:** Run the command from the project root so Python can import the application modules. `ModuleNotFoundError` means project requirements are missing from that Python environment. Mocked tests passing do not verify access to an external API or database.

### Interview questions

1. What is a unit test, and how does it differ from manually testing in Postman?
2. Why mock GNews and MongoDB in an offline test?
3. What does an assertion verify?
4. Can a mocked test prove MongoDB is running or an API key is valid?
5. Why test both successful behavior and failure cases?

**Before we call the learning stages complete, explain what the automated tests verify and name one thing that still needs a live MongoDB/API demonstration.**

## Step 10: Final demonstration and complete data flow

Use this checklist for the classroom demonstration:

1. Start the local MongoDB service (or confirm the authorized Atlas cluster is reachable).
2. In VS Code, activate the project virtual environment and run `python main.py`.
3. In a second terminal, run `python -c "from scheduler import run_daily_news_job; print(run_daily_news_job())"` to demonstrate collection immediately rather than waiting for 6:00 AM.
4. Show the returned fetched/inserted/duplicate counts and the printed daily briefing.
5. Open MongoDB Compass using the same `MONGODB_URI`. Browse `tech_news`, inspect the `news` and `daily_briefings` documents, and show the unique `url` and `briefing_date` indexes.
6. In Postman, send `GET http://127.0.0.1:5000/health`, then try `/news`, `/news/search?keyword=python`, `/news/category/AI`, `/news/<id>` using an ID returned by `/news`, `/briefings`, and `/briefings/<YYYY-MM-DD>`.
7. Explain that an empty search result returns `200` with an empty list, a missing article or briefing returns `404`, invalid request input returns `400`, and an unavailable MongoDB returns `503`.
8. Show that the scheduler remains running in the application process and explain its configured timezone and next scheduled run. Stop the app with Ctrl+C.
9. Run `python -m unittest discover -s tests -v` and explain that these tests mock HTTP and MongoDB, while the demonstration above verifies the live integrations.
10. Explain the flow without relying on Copilot: schedule → GNews request → validated and categorized article dictionaries → MongoDB inserts with unique URL enforcement → local-day query → relevance/recency selection → daily briefing upsert → Flask/Postman JSON responses.

### GitHub and secret-safety check

- Commit `.env.example`, not `.env`. Replace its placeholder key only in the private local `.env`.
- Before committing, check `git status --short` and confirm `.env` is not listed. The repository `.gitignore` excludes `.env`, virtual environments, Python bytecode, and common generated files.
- Never put API keys, MongoDB passwords, or private connection strings into README examples, source code, screenshots, or a Postman collection that will be shared publicly.

### Interview questions

1. Describe the complete flow from the scheduler to a Postman JSON response.
2. Which operation prevents one article URL from being inserted twice?
3. How does the scheduler's timezone affect which articles appear in a daily briefing?
4. What does a live demonstration verify that mocked tests cannot?
5. How do you check that a secret is not included in a Git commit?

**Final checkpoint:** explain the complete project flow in your own words and identify which checks were automated and which required live MongoDB/GNews/Postman access.

## Step 11: Manually refresh today's briefing

`refresh_briefing.py` is a small command-line helper for regenerating today's briefing from articles already saved in MongoDB. It does not call GNews or insert new articles. The existing `generate_daily_briefing()` function recalculates the daily article counts and selected stories, then upserts the briefing for that date. The helper prints the result and closes the MongoDB client even if briefing generation fails.

This is useful after adjusting scoring or briefing text, or when a learner wants to rerun briefing generation without using another API request. It is a local command, not an unauthenticated REST endpoint.

### Concepts in this step

- **Python:** a small reusable function, module imports, `try/finally`, and running a module as a script.
- **MongoDB:** reading saved news and updating/inserting the date's briefing with the existing upsert.
- **Data flow:** command → connect to MongoDB → read saved articles → regenerate/upsert briefing → print it → close client. No external news request is made.

### Run and test

With MongoDB available, run from the project folder:

```text
python refresh_briefing.py
```

The command uses the configured timezone to determine today's date. If no articles have been collected today, it still saves and prints a briefing with empty sections and general learning/career suggestions. Run `python -m unittest discover -s tests -v` to test that the helper passes the right collections, prints the result, and closes the client on success and failure.

**Common errors:** MongoDB must be reachable, and `NEWS_SCHEDULE_TIMEZONE` must be valid. This command does not fetch articles; run the scheduled job or `run_daily_news_job()` first if today's news collection is empty. Generation errors are allowed to surface rather than being reported as success.

### Interview questions

1. How does a manual briefing refresh differ from the scheduled news job?
2. Why might you regenerate a briefing without fetching news again?
3. How does the upsert behave if today's briefing already exists?
4. Why does the helper close the MongoDB client in `finally`?
5. Why is a local command a safer beginner choice than an unauthenticated refresh endpoint?

**Before adding another feature, explain what this refresh command does, what it deliberately does not do, and how it handles the MongoDB client if generation fails.**
