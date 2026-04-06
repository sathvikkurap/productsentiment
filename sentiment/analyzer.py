"""Sentiment analysis using VADER (fast, free, no GPU)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sources.base import Mention


@dataclass
class SentimentResult:
    """Sentiment for a single mention."""

    label: str  # "positive", "negative", "neutral"
    score: float  # compound
    positive: float
    negative: float
    neutral: float


# Singleton analyzer to avoid re-initialization
_analyzer = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer


def analyze_sentiment(mention: "Mention") -> SentimentResult:
    """Run sentiment on mention text. Uses VADER for speed and reliability."""
    text = (mention.title + " " + (mention.body or ""))[:8000]
    if not text.strip():
        return SentimentResult(
            label="neutral",
            score=0.0,
            positive=0.0,
            negative=0.0,
            neutral=1.0,
        )
    scores = _get_analyzer().polarity_scores(text)
    compound = scores["compound"]
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    return SentimentResult(
        label=label,
        score=compound,
        positive=scores["pos"],
        negative=scores["neg"],
        neutral=scores["neu"],
    )
