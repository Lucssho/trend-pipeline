import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from baseline_topics import build_topic_model, load_documents
from model_store import MODEL_DIR, save_model

from storage.db import get_connection


def run():
    conn = get_connection()
    try:
        ids, texts = load_documents(conn)
    finally:
        conn.close()

    print(f"Training BERTopic on {len(texts)} documents\n")

    topic_model = build_topic_model()
    topic_model.fit(texts)

    save_model(topic_model)

    topic_info = topic_model.get_topic_info()
    print("Discovered topics:\n")
    for _, row in topic_info.iterrows():
        topic_id = row["Topic"]
        count = row["Count"]
        if topic_id == -1:
            print(f"Topic {topic_id} ({count} docs): Outliers")
            continue
        keywords = [word for word, _ in topic_model.get_topic(topic_id)]
        print(f"Topic {topic_id} ({count} docs): {', '.join(keywords)}")

    print(f"\nModel saved to {MODEL_DIR}")


if __name__ == "__main__":
    run()
