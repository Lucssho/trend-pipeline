import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "documents.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT,
    url TEXT NOT NULL,
    published_at TEXT,
    scraped_at TEXT NOT NULL,
    topic_id INTEGER,
    topic_label TEXT
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    try:
        conn.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_document(conn, doc):
    conn.execute(
        """
        INSERT OR IGNORE INTO documents
            (id, source, title, text, url, published_at, scraped_at, topic_id, topic_label)
        VALUES (:id, :source, :title, :text, :url, :published_at, :scraped_at, :topic_id, :topic_label)
        """,
        doc,
    )
    return conn.total_changes


def count_documents(conn):
    cur = conn.execute("SELECT COUNT(*) FROM documents")
    return cur.fetchone()[0]
