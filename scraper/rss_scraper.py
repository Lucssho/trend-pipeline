import calendar
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import feedparser

from storage.db import get_connection, init_db, count_documents
from text_utils import strip_html

FEEDS = {
    "reddit_cybersecurity": "https://www.reddit.com/r/cybersecurity/.rss",
    "reddit_netsec": "https://www.reddit.com/r/netsec/.rss",
    "reddit_hacking": "https://www.reddit.com/r/hacking/.rss",
    "reddit_asknetsec": "https://www.reddit.com/r/AskNetsec/.rss",
    "krebs_on_security": "https://krebsonsecurity.com/feed/",
    "bleeping_computer": "https://www.bleepingcomputer.com/feed/",
}

# Reddit's unauthenticated RSS endpoint enforces a strict per-IP rate limit
# (~1 request per 15-20s, observed via x-ratelimit-reset). Requests without a
# descriptive User-Agent are also more likely to get throttled.
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RSSDocumentScraper/1.0"
}
INTER_FEED_DELAY_SECONDS = 25
RATE_LIMIT_RETRY_DELAY_SECONDS = 20
MAX_RATE_LIMIT_RETRIES = 2


def make_id(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def to_iso_utc(struct_time):
    if struct_time is None:
        return None
    epoch = calendar.timegm(struct_time)
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def fetch_feed(url):
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        parsed = feedparser.parse(url, request_headers=REQUEST_HEADERS)
        if parsed.get("status") == 429 and attempt < MAX_RATE_LIMIT_RETRIES:
            print(f"  Rate limited fetching {url}, retrying in {RATE_LIMIT_RETRY_DELAY_SECONDS}s...")
            time.sleep(RATE_LIMIT_RETRY_DELAY_SECONDS)
            continue
        return parsed
    return parsed


def parse_feed(source, url):
    parsed = fetch_feed(url)
    docs = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    for entry in parsed.entries:
        link = entry.get("link")
        if not link:
            continue
        docs.append(
            {
                "id": make_id(link),
                "source": source,
                "title": entry.get("title", ""),
                "text": strip_html(entry.get("summary", "")),
                "url": link,
                "published_at": to_iso_utc(entry.get("published_parsed")),
                "scraped_at": scraped_at,
                "topic_id": None,
                "topic_label": None,
            }
        )
    return docs


def run():
    init_db()
    conn = get_connection()
    total_inserted = 0

    try:
        for i, (source, url) in enumerate(FEEDS.items()):
            if i > 0:
                time.sleep(INTER_FEED_DELAY_SECONDS)
            docs = parse_feed(source, url)
            print(f"Fetched {len(docs)} entries from {source}")
            for doc in docs:
                before = count_documents(conn)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO documents
                        (id, source, title, text, url, published_at, scraped_at, topic_id, topic_label)
                    VALUES (:id, :source, :title, :text, :url, :published_at, :scraped_at, :topic_id, :topic_label)
                    """,
                    doc,
                )
                conn.commit()
                after = count_documents(conn)
                if after > before:
                    total_inserted += 1

        final_count = count_documents(conn)
        print(f"\nNew documents inserted this run: {total_inserted}")
        print(f"Total documents in database: {final_count}")

        cur = conn.execute("SELECT title FROM documents ORDER BY scraped_at DESC LIMIT 3")
        print("\nExample titles:")
        for (title,) in cur.fetchall():
            print(f"- {title}")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
