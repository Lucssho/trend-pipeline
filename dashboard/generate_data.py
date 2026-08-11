import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "modeling"))

from model_store import load_model, model_exists
from time_buckets import load_documents_with_dates, write_topic_ids

from storage.db import get_connection

DATA_JS_PATH = Path(__file__).resolve().parent / "data.js"


def parse_args():
    parser = argparse.ArgumentParser(description="Regenerate dashboard/data.js for a given day.")
    parser.add_argument("date", nargs="?", default=None, help="YYYY-MM-DD (default: today)")
    return parser.parse_args()


def topic_label(topic_model, topic_id):
    if topic_id == -1:
        return "Outliers"
    keywords = [word for word, _ in topic_model.get_topic(topic_id)[:3]]
    return " ".join(keywords)


def topic_counts_for_date(conn, target_date):
    cur = conn.execute(
        """
        SELECT topic_id, COUNT(*)
        FROM documents
        WHERE topic_id IS NOT NULL AND substr(published_at, 1, 10) = ?
        GROUP BY topic_id
        """,
        (target_date,),
    )
    return cur.fetchall()


def write_data_js(target_date, topics):
    payload = {"date": target_date, "topics": topics}
    DATA_JS_PATH.write_text(
        "const TOPIC_DATA = " + json.dumps(payload, indent=2) + ";\n",
        encoding="utf-8",
    )


def run():
    args = parse_args()
    target_date = args.date or date.today().isoformat()

    if not model_exists():
        raise SystemExit("No trained model found. Run `python modeling/train_topics.py` first.")

    topic_model = load_model()

    conn = get_connection()
    try:
        ids, texts, published_ats = load_documents_with_dates(conn)
        topics, probs = topic_model.transform(texts)
        write_topic_ids(conn, ids, topics)

        counts = topic_counts_for_date(conn, target_date)
    finally:
        conn.close()

    topics_payload = [
        {"label": topic_label(topic_model, topic_id), "count": count}
        for topic_id, count in sorted(counts, key=lambda item: -item[1])
    ]

    write_data_js(target_date, topics_payload)
    print(f"Wrote {len(topics_payload)} topic buckets for {target_date} to {DATA_JS_PATH}")


if __name__ == "__main__":
    run()
