"""Data sources for product mentions and discussions."""

from .base import Mention, Source
from .duckduckgo_source import DuckDuckGoSource
from .hackernews_source import HackerNewsSource
from .reddit_source import RedditSource
from .web_search_source import WebSearchSource

__all__ = [
    "Mention",
    "Source",
    "RedditSource",
    "WebSearchSource",
    "HackerNewsSource",
    "DuckDuckGoSource",
]
