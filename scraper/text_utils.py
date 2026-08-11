import html
import re

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def strip_html(raw):
    if not raw:
        return raw
    text = TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text
