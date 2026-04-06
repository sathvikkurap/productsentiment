"""Optional file-based cache for fetched mentions (keyed by source + query + options)."""

import hashlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sources.base import Mention


def _cache_key(source: str, query: str, options: dict[str, Any] | None = None) -> str:
    raw = f"{source}:{query.strip().lower()}"
    if options:
        raw += ":" + json.dumps(options, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _mention_to_dict(m: "Mention") -> dict:
    return {
        "source": m.source,
        "platform": m.platform,
        "title": m.title,
        "body": m.body or "",
        "url": m.url or "",
        "author": m.author,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "score": m.score,
        "extra": m.extra or {},
    }


def _dict_to_mention(d: dict) -> "Mention":
    from datetime import datetime

    from sources.base import Mention

    created = None
    if d.get("created_at"):
        try:
            created = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
        except Exception:
            pass
    return Mention(
        source=d.get("source", "unknown"),
        platform=d.get("platform", "web"),
        title=d.get("title", ""),
        body=d.get("body") or "",
        url=d.get("url", ""),
        author=d.get("author"),
        created_at=created,
        score=d.get("score"),
        extra=d.get("extra") or None,
    )


def load_cached_mentions(
    cache_dir: Path,
    source: str,
    query: str,
    max_age_seconds: int,
    options: dict[str, Any] | None = None,
) -> list["Mention"] | None:
    """Load mentions from cache if present and fresh. Otherwise return None."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(source, query, options)
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - data.get("cached_at", 0) > max_age_seconds:
            return None
        return [_dict_to_mention(x) for x in data.get("mentions", [])]
    except Exception:
        return None


def save_mentions_to_cache(
    cache_dir: Path,
    source: str,
    query: str,
    mentions: list["Mention"],
    options: dict[str, Any] | None = None,
) -> None:
    """Persist mentions to cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(source, query, options)
    path = cache_dir / f"{key}.json"
    data = {
        "cached_at": time.time(),
        "source": source,
        "query": query,
        "options": options or {},
        "mentions": [_mention_to_dict(m) for m in mentions],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
