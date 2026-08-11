import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scraper"))

from storage.db import get_connection
from text_utils import strip_html


def run():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, text FROM documents").fetchall()
        updated = 0
        for doc_id, text in rows:
            cleaned = strip_html(text)
            if cleaned != text:
                conn.execute("UPDATE documents SET text = ? WHERE id = ?", (cleaned, doc_id))
                updated += 1
        conn.commit()
        print(f"Cleaned {updated} of {len(rows)} documents")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
