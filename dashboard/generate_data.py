import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "modeling"))

from model_store import load_model, model_exists
from time_buckets import load_documents_with_dates, write_topic_ids

from storage.db import get_connection

DATA_JS_PATH = Path(__file__).resolve().parent / "data.js"

# Real per-source metadata for the feed sidebar/badges (replaces the design's
# single placeholder "Cybersecurity News RSS" bucket with our two actual feeds).
SOURCE_META = {
    "reddit_cybersecurity": {"label": "r/cybersecurity", "badge": "REDDIT"},
    "reddit_netsec": {"label": "r/netsec", "badge": "REDDIT"},
    "reddit_hacking": {"label": "r/hacking", "badge": "REDDIT"},
    "reddit_asknetsec": {"label": "r/AskNetsec", "badge": "REDDIT"},
    "krebs_on_security": {"label": "Krebs on Security", "badge": "NEWS"},
    "bleeping_computer": {"label": "BleepingComputer", "badge": "NEWS"},
}

EXCERPT_MAX_CHARS = 240
WORD_RE = re.compile(r"^[a-zA-Z]+$")
KEYWORD_MIN_LEN = 4
MAX_KEYWORDS = 40


def topic_label(topic_model, topic_id):
    if topic_id == -1:
        return "Outliers"
    keywords = [word for word, _ in topic_model.get_topic(topic_id)[:3]]
    return " ".join(keywords)


def build_keyword_list(topic_model):
    # Highlight terms mined from the real corpus (aggregated c-TF-IDF weight
    # across all discovered topics) instead of a hand-picked sample list.
    scores = defaultdict(float)
    for topic_id, words in topic_model.get_topics().items():
        if topic_id == -1:
            continue
        for word, score in words[:5]:  # strongest terms per topic only, to cut tail noise
            if WORD_RE.match(word) and len(word) >= KEYWORD_MIN_LEN:
                scores[word] += score
    ranked = sorted(scores.items(), key=lambda item: -item[1])
    return [word for word, _ in ranked[:MAX_KEYWORDS]]


def truncate(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def load_all_documents(conn):
    cur = conn.execute(
        "SELECT id, source, title, text, url, published_at, topic_id FROM documents ORDER BY published_at DESC"
    )
    return cur.fetchall()


def to_epoch_ms(published_at):
    if not published_at:
        return None
    dt = datetime.fromisoformat(published_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def write_data_js(payload):
    DATA_JS_PATH.write_text(
        "const FEED_DATA = " + json.dumps(payload, indent=2) + ";\n",
        encoding="utf-8",
    )


def run():
    if not model_exists():
        raise SystemExit("No trained model found. Run `python modeling/train_topics.py` first.")

    topic_model = load_model()

    conn = get_connection()
    try:
        ids, texts, published_ats = load_documents_with_dates(conn)
        topics, probs = topic_model.transform(texts)
        write_topic_ids(conn, ids, topics)

        rows = load_all_documents(conn)
    finally:
        conn.close()

    keywords = build_keyword_list(topic_model)

    source_counts = defaultdict(int)
    for _id, source, _title, _text, _url, _published_at, _topic_id in rows:
        source_counts[source] += 1

    sources_payload = [
        {
            "key": source_key,
            "label": meta["label"],
            "badge": meta["badge"],
            "count": source_counts.get(source_key, 0),
        }
        for source_key, meta in SOURCE_META.items()
    ]

    topic_counts = defaultdict(int)
    posts_payload = []
    for doc_id, source, title, text, url, published_at, topic_id in rows:
        if topic_id is not None:
            topic_counts[topic_id] += 1
        meta = SOURCE_META.get(source, {"label": source, "badge": "NEWS"})
        posts_payload.append(
            {
                "id": doc_id,
                "sourceKey": source,
                "badge": meta["badge"],
                "sourceLabel": meta["label"],
                "title": title,
                "excerpt": truncate(text, EXCERPT_MAX_CHARS),
                "topic": topic_label(topic_model, topic_id) if topic_id is not None else "Unclassified",
                "ts": to_epoch_ms(published_at),
                "url": url,
            }
        )

    topics_payload = [
        {"label": topic_label(topic_model, topic_id), "count": count}
        for topic_id, count in sorted(topic_counts.items(), key=lambda item: -item[1])
    ]

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sources": sources_payload,
        "topics": topics_payload,
        "keywords": keywords,
        "posts": posts_payload,
    }
    write_data_js(payload)
    print(
        f"Wrote {len(posts_payload)} posts across {len(sources_payload)} sources "
        f"and {len(topics_payload)} topics to {DATA_JS_PATH}"
    )


if __name__ == "__main__":
    run()
