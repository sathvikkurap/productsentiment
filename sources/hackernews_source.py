"""Hacker News via Algolia API (free, no key required)."""

from datetime import datetime
from typing import Iterator

import config
from sources.base import Mention, Source
from utils.fetch import fetch_json


class HackerNewsSource(Source):
    """Fetch product discussions from Hacker News using Algolia public API."""

    BASE = "https://hn.algolia.com/api/v1"

    @property
    def name(self) -> str:
        return "hackernews"

    def fetch(
        self,
        product_query: str,
        limit: int | None = None,
        *,
        days: int | None = None,
        subreddits: list[str] | None = None,
        **kwargs: object,
    ) -> Iterator[Mention]:
        limit = limit or config.HN_SEARCH_LIMIT
        url = f"{self.BASE}/search"
        params = {"query": product_query, "tags": "story", "hitsPerPage": min(limit, 100)}
        if days is not None and days > 0:
            import time

            since_ts = int(time.time()) - (days * 86400)
            params["numericFilters"] = f"created_at_i>={since_ts}"
        page = 0
        collected = 0
        while collected < limit:
            params["page"] = page
            data = fetch_json(url, params=params, timeout=15)
            if not data or "hits" not in data:
                break
            hits = data["hits"]
            if not hits:
                break
            for h in hits:
                if collected >= limit:
                    break
                title = h.get("title") or ""
                story_text = h.get("story_text") or h.get("content") or ""
                body = story_text if isinstance(story_text, str) else ""
                created_at = None
                if h.get("created_at_i"):
                    created_at = datetime.utcfromtimestamp(h["created_at_i"])
                obj_id = h.get("objectID", "")
                url_link = f"https://news.ycombinator.com/item?id={obj_id}" if obj_id else ""
                yield Mention(
                    source="hackernews",
                    platform="hackernews",
                    title=title,
                    body=body,
                    url=url_link,
                    author=h.get("author"),
                    created_at=created_at,
                    score=h.get("points"),
                    extra={"num_comments": h.get("num_comments"), "objectID": obj_id},
                )
                collected += 1
            if len(hits) < params.get("hitsPerPage", 20):
                break
            page += 1
            if page >= data.get("nbPages", 1):
                break
