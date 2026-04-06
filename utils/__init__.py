"""Shared utilities: retries, rate limit, cache, dedupe, logging, text."""

from .dedupe import deduplicate_mentions
from .fetch import fetch_json, fetch_text
from .logging import get_logger
from .text import decode_html_entities, normalize_whitespace

__all__ = [
    "deduplicate_mentions",
    "fetch_json",
    "fetch_text",
    "get_logger",
    "decode_html_entities",
    "normalize_whitespace",
]
