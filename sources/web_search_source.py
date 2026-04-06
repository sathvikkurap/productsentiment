"""Web search source: Brave and/or SerpAPI for cross-platform mentions."""

from typing import Iterator

import config
from sources.base import Mention, Source


def _platform_from_url(url: str) -> str:
    """Infer platform from URL for labeling."""
    url_lower = url.lower()
    if "reddit.com" in url_lower:
        return "reddit"
    if "linkedin.com" in url_lower:
        return "linkedin"
    if "facebook.com" in url_lower or "fb.com" in url_lower:
        return "facebook"
    if "instagram.com" in url_lower:
        return "instagram"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    return "web"


class WebSearchSource(Source):
    """Fetch product mentions via Brave Search or SerpAPI (surfaces Reddit, LinkedIn, etc. in results)."""

    @property
    def name(self) -> str:
        return "web_search"

    def fetch(
        self,
        product_query: str,
        limit: int | None = None,
        *,
        days: int | None = None,
        subreddits: list[str] | None = None,
        **kwargs: object,
    ) -> Iterator[Mention]:
        limit = limit or config.WEB_SEARCH_LIMIT
        seen_urls = set()
        if config.BRAVE_API_KEY:
            for m in self._fetch_brave(product_query, limit):
                if m.url not in seen_urls:
                    seen_urls.add(m.url)
                    yield m
        if config.SERPAPI_KEY and len(seen_urls) < limit:
            for m in self._fetch_serpapi(product_query, limit - len(seen_urls)):
                if m.url not in seen_urls:
                    seen_urls.add(m.url)
                    yield m

    def _fetch_brave(self, query: str, limit: int) -> Iterator[Mention]:
        """Brave Search API."""
        import requests

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": config.BRAVE_API_KEY}
        params = {"q": query, "count": min(limit, 20)}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return
        for web in data.get("web", {}).get("results", [])[:limit]:
            yield Mention(
                source="web_search",
                platform=_platform_from_url(web.get("url", "")),
                title=web.get("title", ""),
                body=web.get("description", ""),
                url=web.get("url", ""),
                author=None,
                created_at=None,
                score=None,
                extra={"brave": True},
            )

    def _fetch_serpapi(self, query: str, limit: int) -> Iterator[Mention]:
        """SerpAPI Google search (can include Reddit, LinkedIn in organic results)."""
        import requests

        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": config.SERPAPI_KEY,
            "num": min(limit, 30),
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return
        for org in data.get("organic_results", [])[:limit]:
            yield Mention(
                source="web_search",
                platform=_platform_from_url(org.get("link", "")),
                title=org.get("title", ""),
                body=org.get("snippet", ""),
                url=org.get("link", ""),
                author=None,
                created_at=None,
                score=None,
                extra={"serpapi": True},
            )
