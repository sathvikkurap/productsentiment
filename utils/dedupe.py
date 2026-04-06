"""Deduplicate mentions by URL and by content hash."""

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sources.base import Mention


def _content_hash(m: "Mention") -> str:
    text = (m.title + "\n" + (m.body or "")).strip().lower()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def deduplicate_mentions(mentions: list["Mention"]) -> list["Mention"]:
    """Dedupe by URL first, then by content hash. Preserve order."""
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    out: list["Mention"] = []
    for m in mentions:
        url_key = (m.url or "").strip().lower()
        if url_key and url_key in seen_urls:
            continue
        if url_key:
            seen_urls.add(url_key)
        h = _content_hash(m)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        out.append(m)
    return out
