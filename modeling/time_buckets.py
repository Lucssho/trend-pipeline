import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from baseline_topics import REDDIT_SOURCE_PREFIX
from model_store import load_model, model_exists

from storage.db import get_connection


def load_documents_with_dates(conn):
    cur = conn.execute("SELECT id, source, title, text, published_at FROM documents")
    rows = cur.fetchall()

    ids, texts, published_ats = [], [], []
    for doc_id, source, title, text, published_at in rows:
        model_text = title if source.startswith(REDDIT_SOURCE_PREFIX) else text
        if model_text and model_text.strip():
            ids.append(doc_id)
            texts.append(model_text)
            published_ats.append(published_at)
    return ids, texts, published_ats


def write_topic_ids(conn, ids, topics):
    for doc_id, topic_id in zip(ids, topics):
        conn.execute(
            "UPDATE documents SET topic_id = ? WHERE id = ?", (int(topic_id), doc_id)
        )
    conn.commit()


def build_topic_labels(topic_model, topics):
    labels = {}
    for topic_id in set(topics):
        if topic_id == -1:
            labels[topic_id] = "Outliers"
        else:
            keywords = [word for word, _ in topic_model.get_topic(topic_id)[:3]]
            labels[topic_id] = ", ".join(keywords)
    return labels


def run():
    if not model_exists():
        raise SystemExit(
            "No trained model found. Run `python modeling/train_topics.py` first to fit and save one."
        )

    conn = get_connection()
    try:
        ids, texts, published_ats = load_documents_with_dates(conn)
        print(f"Loaded {len(texts)} documents with model input text\n")

        topic_model = load_model()
        topics, probs = topic_model.transform(texts)

        write_topic_ids(conn, ids, topics)
        print(f"Wrote topic_id for {len(ids)} documents\n")

        topic_labels = build_topic_labels(topic_model, topics)

        counts = defaultdict(int)
        for topic_id, published_at in zip(topics, published_ats):
            date = published_at[:10] if published_at else "unknown"
            counts[(date, topic_id)] += 1

        print(f"{'Date':<12} {'Topic':<40} {'Count':>5}")
        for (date, topic_id), count in sorted(counts.items(), key=lambda item: (item[0][0], item[0][1])):
            label = topic_labels[topic_id]
            print(f"{date:<12} {label:<40} {count:>5}")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
