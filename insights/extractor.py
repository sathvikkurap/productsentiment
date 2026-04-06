"""Extract themes and novel insights from sentiment-labeled mentions."""

import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentiment.analyzer import SentimentResult
    from sources.base import Mention


@dataclass
class Insight:
    """A surfaced insight for product creators."""

    kind: str
    summary: str
    representative_quotes: list[str]
    sentiment: str
    platform_counts: dict[str, int]
    source_urls: list[str]
    count: int = 0  # number of mentions backing this insight

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Pain: problems, bugs, frustration, disappointment
PAIN_PATTERNS = re.compile(
    r"\b(problem|problems|issue|issues|bug|bugs|broken|hate|terrible|horrible|frustrat|disappoint|"
    r"missing|lack|lacking|doesn't work|won't work|does not work|will not work|"
    r"slow|crash|crashing|unusable|worst|awful|ridiculous)\b",
    re.I,
)
# Praise: love, recommend, great experience
PRAISE_PATTERNS = re.compile(
    r"\b(love|great|awesome|best|recommend|smooth|easy|perfect|excellent|game changer|"
    r"fantastic|amazing|solid|reliable|simple|intuitive|fast|clean)\b",
    re.I,
)
# Feature requests / wishes
FEATURE_PATTERNS = re.compile(
    r"\b(would be (nice|great|good)|hope (they|it) (add|support|fix)|wish (it|they) (had|would)|"
    r"need(s)? (to|a)|should (add|support|have|fix)|want (to|ed)?|"
    r"if only|would love (to|if)|looking for(ward)? to)\b",
    re.I,
)
# Pricing / value
PRICING_PATTERNS = re.compile(
    r"\b(price|pricing|cost|expensive|cheap|free tier|subscription|worth it|overpriced|"
    r"value for money|too much|affordable|budget)\b",
    re.I,
)
# Competitor / comparison
COMPARISON_PATTERNS = re.compile(
    r"\b(vs\.?|versus|compared to|instead of|alternative to|better than|worse than|"
    r"switch(ed|ing)? from|replacement for|like .{1,20} but)\b",
    re.I,
)


def _clean_snippet(text: str, max_len: int = 220) -> str:
    from utils.text import decode_html_entities, normalize_whitespace

    text = decode_html_entities(text)
    text = normalize_whitespace(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def _add_insight(
    insights: list[Insight],
    kind: str,
    summary: str,
    quotes: list[tuple[str, str, str]],
    sentiment: str,
    max_quotes: int = 8,
    max_urls: int = 12,
) -> None:
    if not quotes:
        return
    by_platform = Counter(p[1] for p in quotes)
    urls = list(dict.fromkeys(q[2] for q in quotes if q[2]))[:max_urls]
    insights.append(
        Insight(
            kind=kind,
            summary=summary,
            representative_quotes=[q[0] for q in quotes[:max_quotes]],
            sentiment=sentiment,
            platform_counts=dict(by_platform),
            source_urls=urls,
            count=len(quotes),
        )
    )


def extract_insights(
    mentions_with_sentiment: list[tuple["Mention", "SentimentResult"]],
) -> list[Insight]:
    """Group and summarize mentions into actionable insights."""
    insights: list[Insight] = []
    pain_quotes: list[tuple[str, str, str]] = []
    praise_quotes: list[tuple[str, str, str]] = []
    feature_quotes: list[tuple[str, str, str]] = []
    pricing_quotes: list[tuple[str, str, str]] = []
    comparison_quotes: list[tuple[str, str, str]] = []
    platform_counter: Counter = Counter()
    theme_words: Counter = Counter()
    stop = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "been",
        "were",
        "what",
        "when",
        "which",
        "their",
        "there",
        "would",
        "could",
        "should",
        "about",
        "other",
        "some",
        "more",
        "like",
        "just",
        "only",
        "very",
        "really",
        "much",
        "many",
        "into",
        "your",
        "will",
        "quot",
        "https",
        "http",
        "html",
        "www",
        "com",
        "org",
        "net",
        "said",
        "says",
    }

    for mention, sent in mentions_with_sentiment:
        platform_counter[mention.platform] += 1
        text = mention.text_for_analysis()
        snippet = _clean_snippet(text)
        url = mention.url or ""

        for word in re.findall(r"\b[a-zA-Z]{4,}\b", text.lower()):
            if word not in stop:
                theme_words[word] += 1

        if PAIN_PATTERNS.search(text) or sent.label == "negative":
            pain_quotes.append((snippet, mention.platform, url))
        if PRAISE_PATTERNS.search(text) or sent.label == "positive":
            praise_quotes.append((snippet, mention.platform, url))
        if FEATURE_PATTERNS.search(text):
            feature_quotes.append((snippet, mention.platform, url))
        if PRICING_PATTERNS.search(text):
            pricing_quotes.append((snippet, mention.platform, url))
        if COMPARISON_PATTERNS.search(text):
            comparison_quotes.append((snippet, mention.platform, url))

    _add_insight(
        insights,
        "pain_point",
        "Users report problems, disappointments, or missing capabilities. High signal for product and support improvements.",
        pain_quotes,
        "negative",
        max_quotes=8,
        max_urls=12,
    )
    _add_insight(
        insights,
        "praise",
        "Positive highlights and recommendations. Use to double down on what resonates.",
        praise_quotes,
        "positive",
        max_quotes=8,
        max_urls=12,
    )
    _add_insight(
        insights,
        "feature_request",
        "Expressed wishes and suggested improvements. Direct input for roadmap and prioritization.",
        feature_quotes,
        "neutral",
        max_quotes=8,
        max_urls=12,
    )
    _add_insight(
        insights,
        "pricing_value",
        "Discussion of pricing, value, and cost. Relevant for positioning and packaging.",
        pricing_quotes,
        "neutral",
        max_quotes=6,
        max_urls=10,
    )
    _add_insight(
        insights,
        "comparison_competitor",
        "Comparisons and alternatives. Surfaces competitive landscape and switching triggers.",
        comparison_quotes,
        "neutral",
        max_quotes=6,
        max_urls=10,
    )

    if theme_words:
        # Skip URL-like or noise tokens
        skip = stop | {"href", "span", "div", "page", "link"}
        top_themes = [(w, c) for w, c in theme_words.most_common(25) if w not in skip][:12]
        themes_str = ", ".join(w for w, _ in top_themes)
        if themes_str:
            insights.append(
                Insight(
                    kind="theme",
                    summary=f"Frequently discussed topics: {themes_str}.",
                    representative_quotes=[],
                    sentiment="",
                    platform_counts=dict(platform_counter),
                    source_urls=[],
                    count=sum(platform_counter.values()),
                )
            )

    return insights
