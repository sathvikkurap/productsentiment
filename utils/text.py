"""Text normalization for display and analysis."""

import html
import re


def decode_html_entities(text: str) -> str:
    """Decode HTML entities (e.g. &#x27; -> ', &quot; -> \") for cleaner display."""
    if not text:
        return text
    # Unescape common entities
    return html.unescape(text)


def normalize_whitespace(text: str) -> str:
    """Collapse whitespace to single spaces and strip."""
    if not text:
        return text
    return re.sub(r"\s+", " ", text).strip()
