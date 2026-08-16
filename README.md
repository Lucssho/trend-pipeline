# Trend Pipeline

A small pipeline that scrapes cybersecurity news and discussion from Reddit and RSS
feeds, discovers topics in it with [BERTopic](https://maartengr.github.io/BERTopic/),
and renders the result as a live-feed dashboard (`dashboard/index.html`) — a
scrolling, filterable list of real posts with source/topic stats and keyword
highlighting.

## How it fits together

```
scraper/rss_scraper.py        → fetches posts, stores them in data/documents.db
modeling/train_topics.py      → trains a BERTopic model on the stored documents
dashboard/generate_data.py    → assigns topics to documents, writes dashboard/data.js
dashboard/index.html          → static page that reads data.js and renders the feed
```

Sources currently scraped (`scraper/rss_scraper.py`, `FEEDS`):
r/cybersecurity, r/netsec, r/hacking, r/AskNetsec, Krebs on Security, and
BleepingComputer.

## Prerequisites

- Python 3.10+ (developed against 3.13)
- Internet access (to fetch RSS/Reddit feeds and download the sentence-transformer
  model BERTopic uses on first run)

## Setup

Clone the repo and set up a virtual environment:

```bash
git clone https://github.com/Lucssho/trend-pipeline.git
cd trend-pipeline
python -m venv .venv
```

Activate it:

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the pipeline

Run these from the project root, in order. Each step writes its output to
`data/`, which is gitignored — a fresh clone starts with no database and no
trained model, so this order matters the first time.

### 1. Scrape the feeds

```bash
python scraper/rss_scraper.py
```

Fetches the configured Reddit/RSS sources and stores new documents in
`data/documents.db` (created automatically on first run). Safe to re-run any
time — it dedupes on URL, so re-running only adds new posts.

### 2. Train the topic model

```bash
python modeling/train_topics.py
```

Trains a BERTopic model on everything currently in `data/documents.db` and
saves it to `data/bertopic_model/`. Re-run this whenever you want the topic
model to reflect newly scraped data.

### 3. Generate the dashboard data

```bash
python dashboard/generate_data.py
```

Loads the trained model, assigns a topic to every document, and writes
`dashboard/data.js` — the file the dashboard actually reads. Re-run this any
time after scraping/retraining to refresh what the dashboard shows.

### 4. Open the dashboard

The dashboard loads `data.js` via a `<script>` tag, which browsers block over
`file://` — serve the folder over HTTP instead:

```bash
python -m http.server 8099 --directory dashboard
```

Then open **http://localhost:8099/** in a browser.

## Refreshing later

To pull in new posts and update the dashboard, just repeat steps 1–3 (scrape →
retrain → regenerate) and reload the page — no need to redo the setup steps.

## Project structure

```
scraper/      RSS/Reddit fetching (rss_scraper.py) + HTML-stripping helper (text_utils.py)
modeling/     BERTopic training (train_topics.py, baseline_topics.py), model save/load
              (model_store.py), and topic-assignment helpers (time_buckets.py)
dashboard/    generate_data.py (data pipeline) + index.html (the dashboard itself)
storage/      SQLite connection/schema (db.py) — data/documents.db
scripts/      One-off maintenance scripts
```
