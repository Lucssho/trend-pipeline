import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

from storage.db import get_connection

REDDIT_SOURCE_PREFIX = "reddit_"


def load_documents(conn):
    cur = conn.execute("SELECT id, source, title, text FROM documents")
    rows = cur.fetchall()

    ids, texts = [], []
    for doc_id, source, title, text in rows:
        model_text = title if source.startswith(REDDIT_SOURCE_PREFIX) else text
        if model_text and model_text.strip():
            ids.append(doc_id)
            texts.append(model_text)
    return ids, texts


def build_topic_model():
    vectorizer_model = CountVectorizer(stop_words="english")
    # Lower n_neighbors (default 15) so UMAP preserves local structure instead of
    # collapsing topically-similar-but-distinct documents (e.g. all of cybersecurity)
    # into one global blob. random_state pinned for reproducible retrains.
    umap_model = UMAP(
        n_neighbors=3,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    return BERTopic(
        min_topic_size=3,
        vectorizer_model=vectorizer_model,
        umap_model=umap_model,
        verbose=True,
    )


def run():
    conn = get_connection()
    try:
        ids, texts = load_documents(conn)
    finally:
        conn.close()

    print(f"Loaded {len(texts)} documents with non-empty text\n")

    topic_model = build_topic_model()
    topics, probs = topic_model.fit_transform(texts)

    topic_info = topic_model.get_topic_info()

    print("\nDiscovered topics:\n")
    for _, row in topic_info.iterrows():
        topic_id = row["Topic"]
        count = row["Count"]
        if topic_id == -1:
            print(f"Topic {topic_id} ({count} docs): Outliers (no topic assigned)")
            continue
        keywords = [word for word, _ in topic_model.get_topic(topic_id)]
        print(f"Topic {topic_id} ({count} docs): {', '.join(keywords)}")


if __name__ == "__main__":
    run()
