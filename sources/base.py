"""Base types for data sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator


@dataclass
class Mention:
    """A single mention or discussion about a product."""

    source: str  # e.g. "reddit", "web"
    platform: str  # e.g. "reddit", "linkedin", "twitter"
    title: str
    body: str
    url: str
    author: str | None
    created_at: datetime | None
    score: int | None  # upvotes, likes, etc.
    extra: dict | None = None

    def text_for_analysis(self) -> str:
        """Full text for sentiment/insight analysis."""
        parts = [self.title]
        if self.body:
            parts.append(self.body)
        return "\n".join(parts)


class Source(ABC):
    """Abstract data source that yields product mentions."""

    @abstractmethod
    def fetch(
        self,
        product_query: str,
        limit: int,
        *,
        days: int | None = None,
        subreddits: list[str] | None = None,
        **kwargs: object,
    ) -> Iterator[Mention]:
        """Fetch mentions for the given product query. Yields Mention objects.
        Optional: days (time range in days), subreddits (Reddit-only, e.g. ['Notion','productivity'])."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the source."""
        ...
