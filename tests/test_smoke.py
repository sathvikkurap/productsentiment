"""Smoke tests: imports and minimal pipeline run (no network if cached)."""

import sys
import tempfile
import unittest
from pathlib import Path

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class SmokeTests(unittest.TestCase):
    def test_imports(self):
        """All main modules import without error."""
        from insights.extractor import Insight
        from sentiment.analyzer import SentimentResult
        from sources import (
            Mention,
        )

        self.assertTrue(Mention)
        self.assertTrue(SentimentResult)
        self.assertTrue(Insight)

    def test_decode_html_entities(self):
        """HTML entities are decoded for display."""
        from utils.text import decode_html_entities

        self.assertEqual(decode_html_entities("&#x27;"), "'")
        self.assertEqual(decode_html_entities("&quot;"), '"')
        self.assertEqual(decode_html_entities("a &amp; b"), "a & b")

    def test_dedupe(self):
        """Deduplication removes duplicate URLs and content."""
        from sources.base import Mention
        from utils.dedupe import deduplicate_mentions

        m1 = Mention("r", "r", "Same", "body", "https://a.com", None, None, 1, None)
        m2 = Mention("r", "r", "Same", "body", "https://a.com", None, None, 2, None)
        m3 = Mention("r", "r", "Other", "text", "https://b.com", None, None, 0, None)
        out = deduplicate_mentions([m1, m2, m3])
        self.assertGreaterEqual(len(out), 1)
        urls = [x.url for x in out]
        self.assertIn("https://b.com", urls)

    def test_sentiment(self):
        """Sentiment returns valid label and scores."""
        from sentiment.analyzer import analyze_sentiment
        from sources.base import Mention

        m = Mention("r", "r", "I love this product!", "", "https://x.com", None, None, None, None)
        s = analyze_sentiment(m)
        self.assertIn(s.label, ("positive", "negative", "neutral"))
        self.assertGreaterEqual(s.score, -1)
        self.assertLessEqual(s.score, 1)
        self.assertLessEqual(s.positive + s.negative + s.neutral, 1.01)

    def test_insights_extract(self):
        """Insight extraction runs and returns list of Insight."""
        from insights.extractor import extract_insights
        from sentiment.analyzer import analyze_sentiment
        from sources.base import Mention

        m = Mention(
            "r", "reddit", "Notion is broken", "I hate it", "https://r.com", None, None, 5, None
        )
        sent = analyze_sentiment(m)
        insights = extract_insights([(m, sent)])
        self.assertIsInstance(insights, list)
        for i in insights:
            self.assertTrue(i.kind)
            self.assertTrue(i.summary)
            self.assertIsInstance(i.representative_quotes, list)
            self.assertIsInstance(i.platform_counts, dict)

    def test_filter_by_sentiment(self):
        """Sentiment filter keeps only matching label."""
        from run import _filter_by_sentiment
        from sentiment.analyzer import analyze_sentiment
        from sources.base import Mention

        m1 = Mention("r", "r", "Love it", "Great", "https://a.com", None, None, 1, None)
        m2 = Mention("r", "r", "Hate it", "Bad", "https://b.com", None, None, 1, None)
        m3 = Mention("r", "r", "Meh", "Ok", "https://c.com", None, None, 1, None)
        mentions = [m1, m2, m3]
        with_sentiment = [
            (m1, analyze_sentiment(m1)),
            (m2, analyze_sentiment(m2)),
            (m3, analyze_sentiment(m3)),
        ]
        filtered_m, filtered_ws = _filter_by_sentiment(mentions, with_sentiment, "negative")
        self.assertIsInstance(filtered_m, list)
        self.assertIsInstance(filtered_ws, list)
        for _, s in filtered_ws:
            self.assertEqual(s.label, "negative")
        # "all" returns unchanged
        all_m, all_ws = _filter_by_sentiment(mentions, with_sentiment, "all")
        self.assertEqual(len(all_m), 3)
        self.assertEqual(len(all_ws), 3)

    def test_cache_key_includes_options(self):
        """Cache key differs when options differ."""
        from utils import cache

        k0 = cache._cache_key("reddit", "Notion", None)
        k1 = cache._cache_key("reddit", "Notion", {"days": 7})
        k2 = cache._cache_key("reddit", "Notion", {"days": 30})
        self.assertNotEqual(k0, k1)
        self.assertNotEqual(k1, k2)
        self.assertEqual(
            cache._cache_key("r", "q", {"days": 7}), cache._cache_key("r", "q", {"days": 7})
        )

    def test_slug(self):
        """Slug produces safe filenames."""
        from run import _slug

        self.assertEqual(_slug("Notion"), "notion")
        self.assertEqual(_slug("Linear app"), "linear_app")
        self.assertTrue(len(_slug("A")) >= 1)
        self.assertEqual(_slug("  Figma  "), "figma")

    def test_exclude_filter(self):
        """Exclude words filter drops mentions containing any keyword."""
        from sources.base import Mention

        m1 = Mention("r", "r", "Great product", "Love it", "https://a.com", None, None, 1, None)
        m2 = Mention("r", "r", "Spam post", "Buy now", "https://b.com", None, None, 1, None)
        m3 = Mention("r", "r", "Normal post", "Clean content", "https://c.com", None, None, 1, None)
        mentions = [m1, m2, m3]
        lower_words = ["spam", "promo"]
        filtered = [
            m
            for m in mentions
            if not any(w in (m.title + " " + (m.body or "")).lower() for w in lower_words)
        ]
        self.assertEqual(len(filtered), 2)
        self.assertIn(m1, filtered)
        self.assertNotIn(m2, filtered)
        self.assertIn(m3, filtered)

    def test_check_config_runs(self):
        """Config check runs without error."""
        from unittest.mock import patch

        from run import _check_config

        with patch("run.console.print"):
            _check_config()

    def test_write_markdown_creates_dir(self):
        """Writing a report to a new subdir creates the directory and file."""
        from unittest.mock import patch

        from insights.extractor import extract_insights
        from run import write_markdown_report
        from sentiment.analyzer import SentimentResult
        from sources.base import Mention

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "reports" / "product.md"
            self.assertFalse(out_path.parent.exists())
            m = Mention("r", "r", "Test", "Body", "https://x.com", None, None, 1, None)
            sent = SentimentResult("positive", 0.5, 0.6, 0.1, 0.3)
            insights = extract_insights([(m, sent)])
            with patch("run.console.print"):
                write_markdown_report("Product", [m], [(m, sent)], insights, out_path)
            self.assertTrue(out_path.parent.exists())
            self.assertTrue(out_path.exists())
            self.assertIn("Product sentiment report", out_path.read_text())


if __name__ == "__main__":
    unittest.main()
