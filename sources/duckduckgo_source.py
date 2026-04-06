"""DuckDuckGo web search (free, no API key). Surfaces Reddit, LinkedIn, etc. in results."""

from typing import Iterator

import config
from sources.base import Mention, Source
from sources.web_search_source import _platform_from_url


class DuckDuckGoSource(Source):
    """Fetch product mentions via DuckDuckGo HTML/API (free, no key)."""

    @property
    def name(self) -> str:
        return "duckduckgo"

    def fetch(
        self,
        product_query: str,
        limit: int | None = None,
        *,
        days: int | None = None,
        subreddits: list[str] | None = None,
        **kwargs: object,
    ) -> Iterator[Mention]:
        limit = limit or config.DUCKDUCKGO_LIMIT
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return
        try:
            with DDGS() as ddgs:
                for i, r in enumerate(ddgs.text(product_query, max_results=min(limit, 50))):
                    if i >= limit:
                        break
                    url = r.get("href") or r.get("link") or ""
                    yield Mention(
                        source="duckduckgo",
                        platform=_platform_from_url(url),
                        title=r.get("title", ""),
                        body=r.get("body", "") or r.get("snippet", ""),
                        url=url,
                        author=None,
                        created_at=None,
                        score=None,
                        extra={"duckduckgo": True},
                    )
        except Exception:
            return
