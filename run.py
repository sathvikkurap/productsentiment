#!/usr/bin/env python3
"""
Product Sentiment Crawler — crawl the web for product mentions, analyze sentiment,
and surface insights for product creators. All free-tier sources supported.

Usage:
  python run.py "Product Name"
  python run.py "Notion" --sources reddit,hackernews,duckduckgo,web --limit 100
  python run.py "Figma" -o report.md --json-output report.json
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from _version import __version__
except ImportError:
    __version__ = "0.0.0"

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn
from rich.table import Table

import config
from insights.extractor import Insight, extract_insights
from sentiment.analyzer import SentimentResult, analyze_sentiment
from sources import (
    DuckDuckGoSource,
    HackerNewsSource,
    RedditSource,
    WebSearchSource,
)
from sources.base import Mention
from utils.cache import load_cached_mentions, save_mentions_to_cache
from utils.dedupe import deduplicate_mentions
from utils.logging import get_logger
from utils.text import decode_html_entities

log = get_logger(__name__)
console = Console()

# Registry: source name -> (Source class, requires_config)
SOURCES = {
    "reddit": (RedditSource, lambda: bool(config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET)),
    "hackernews": (HackerNewsSource, lambda: True),
    "duckduckgo": (DuckDuckGoSource, lambda: True),
    "web": (WebSearchSource, lambda: bool(config.BRAVE_API_KEY or config.SERPAPI_KEY)),
}

SOURCE_HINTS = {
    "reddit": " Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env",
    "web": " Set BRAVE_API_KEY or SERPAPI_KEY in .env",
}


def get_source_instances(requested: list[str]) -> list:
    """Return enabled source instances. Skip unavailable (e.g. missing keys)."""
    out = []
    for name in requested:
        name = name.strip().lower()
        if name not in SOURCES:
            continue
        cls, is_available = SOURCES[name]
        if is_available():
            out.append(cls())
        else:
            hint = SOURCE_HINTS.get(name, "")
            console.print(f"[dim]Skipping {name} (not configured).{hint}[/]")
    return out


def gather_mentions(
    product_query: str,
    sources: list[str],
    limit: int,
    use_cache: bool,
    cache_dir: Path | None,
    verbose: bool = False,
    days: int | None = None,
    subreddits: list[str] | None = None,
    include_comments: int = 0,
    reddit_sort: str = "relevance",
    reddit_min_score: int = 0,
) -> list[Mention]:
    """Fetch mentions from enabled sources, with optional cache and dedupe."""
    source_objs = get_source_instances(sources)
    if not source_objs:
        console.print(
            "[yellow]No sources enabled. Free options: --sources hackernews,duckduckgo. "
            "For Reddit add REDDIT_* to .env; for web add BRAVE_API_KEY or SERPAPI_KEY.[/]"
        )
        return []

    all_mentions: list[Mention] = []
    cache_age = config.CACHE_MAX_AGE if use_cache and config.CACHE_MAX_AGE > 0 else 0
    cache_path = Path(config.CACHE_DIR) if (use_cache and config.CACHE_DIR) else None
    cache_options = {
        "days": days,
        "subreddits": sorted(subreddits or []),
        "include_comments": include_comments,
        "reddit_sort": reddit_sort,
        "reddit_min_score": reddit_min_score,
    }
    per_source: dict[str, int] = {}

    with Progress(SpinnerColumn(), TaskProgressColumn(), console=console) as progress:
        task = progress.add_task("Fetching mentions...", total=len(source_objs))
        for src in source_objs:
            # Try cache first (key includes options so different days/subreddits get different cache)
            if cache_path and cache_age > 0:
                cached = load_cached_mentions(
                    cache_path, src.name, product_query, cache_age, options=cache_options
                )
                if cached is not None:
                    all_mentions.extend(cached)
                    per_source[src.name] = len(cached)
                    progress.update(task, description=f"Fetching... {_progress_desc(per_source)}")
                    progress.advance(task)
                    continue
            try:
                log.debug("Fetching from %s (limit=%s, days=%s)", src.name, limit, days)
                batch: list[Mention] = []
                for m in src.fetch(
                    product_query,
                    limit=limit,
                    days=days,
                    subreddits=subreddits or [],
                    include_comments=include_comments,
                    reddit_sort=reddit_sort,
                    reddit_min_score=reddit_min_score,
                ):
                    batch.append(m)
                if batch and cache_path and cache_age > 0:
                    save_mentions_to_cache(
                        cache_path, src.name, product_query, batch, options=cache_options
                    )
                all_mentions.extend(batch)
                per_source[src.name] = len(batch)
                progress.update(task, description=f"Fetching... {_progress_desc(per_source)}")
            except Exception as e:
                console.print(f"[red]Error from {src.name}: {e}[/]")
                per_source[src.name] = 0
            progress.advance(task)

    # Deduplicate by URL and content hash
    all_mentions = deduplicate_mentions(all_mentions)
    return all_mentions


def _progress_desc(per_source: dict[str, int]) -> str:
    parts = [f"{k}: {v}" for k, v in per_source.items()]
    return ", ".join(parts) if parts else "Fetching mentions..."


def run_pipeline(
    product_query: str,
    sources: list[str],
    limit: int,
    use_cache: bool,
    cache_dir: Path | None,
    verbose: bool = False,
    days: int | None = None,
    subreddits: list[str] | None = None,
    min_text_length: int = 0,
    exclude_words: list[str] | None = None,
    include_comments: int = 0,
    reddit_sort: str = "relevance",
    reddit_min_score: int = 0,
):
    """Gather mentions, analyze sentiment, extract insights."""
    mentions = gather_mentions(
        product_query,
        sources,
        limit,
        use_cache,
        cache_dir,
        verbose,
        days=days,
        subreddits=subreddits,
        include_comments=include_comments,
        reddit_sort=reddit_sort,
        reddit_min_score=reddit_min_score,
    )
    if not mentions:
        console.print("[red]No mentions found. Try different sources or query.[/]")
        return None, None, []

    if min_text_length > 0:
        before = len(mentions)
        mentions = [
            m for m in mentions if len((m.title + " " + (m.body or "")).strip()) >= min_text_length
        ]
        if before != len(mentions):
            console.print(
                f"[dim]Filtered to {len(mentions)} mentions (min text length {min_text_length}).[/]"
            )

    if exclude_words:
        before = len(mentions)
        lower_words = [w.strip().lower() for w in exclude_words if w.strip()]
        if lower_words:
            mentions = [
                m
                for m in mentions
                if not any(w in (m.title + " " + (m.body or "")).lower() for w in lower_words)
            ]
            if before != len(mentions):
                console.print(f"[dim]Filtered to {len(mentions)} mentions (excluded keywords).[/]")

    console.print(f"[green]Collected {len(mentions)} mentions (after dedupe).[/]")

    with Progress(SpinnerColumn(), TaskProgressColumn(), console=console) as progress:
        task = progress.add_task("Analyzing sentiment...", total=len(mentions))
        with_sentiment: list[tuple[Mention, SentimentResult]] = []
        for m in mentions:
            sent = analyze_sentiment(m)
            with_sentiment.append((m, sent))
            progress.advance(task)
    console.print("[green]Sentiment analysis done.[/]")

    insights = extract_insights(with_sentiment)
    return mentions, with_sentiment, insights


def print_summary(
    mentions: list[Mention],
    with_sentiment: list[tuple[Mention, SentimentResult]],
    insights: list[Insight],
) -> None:
    if not with_sentiment:
        return

    labels = Counter(s.label for _, s in with_sentiment)
    total = len(with_sentiment)

    def pct(k: str) -> float:
        return round(100 * labels.get(k, 0) / total, 1) if total else 0

    console.print(
        f"[dim]Sentiment: [/]positive [green]{pct('positive')}%[/] | "
        f"negative [red]{pct('negative')}%[/] | neutral [dim]{pct('neutral')}%[/]"
    )
    table = Table(title="Sentiment breakdown")
    table.add_column("Label", style="cyan")
    table.add_column("Count", justify="right")
    for label, count in labels.most_common():
        table.add_row(label, str(count))
    console.print(table)

    platforms = Counter(m.platform for m in mentions)
    pt = Table(title="By platform")
    pt.add_column("Platform", style="cyan")
    pt.add_column("Count", justify="right")
    for plat, count in platforms.most_common():
        pt.add_row(plat, str(count))
    console.print(pt)

    console.print(Panel("[bold]Insights for product creators[/]", title="Insights"))
    for i, ins in enumerate(insights, 1):
        kind_title = ins.kind.replace("_", " ").title()
        console.print(f"\n[bold]{i}. {kind_title}[/] [dim](n={ins.count})[/]")
        console.print(ins.summary)
        if ins.representative_quotes:
            console.print("  [dim]Sample quotes:[/]")
            for q in ins.representative_quotes[:4]:
                console.print(f"  • {decode_html_entities(q)[:180]}{'...' if len(q) > 180 else ''}")
        if ins.platform_counts:
            console.print(f"  [dim]Platforms: {ins.platform_counts}[/]")
        if ins.source_urls:
            for u in ins.source_urls[:3]:
                console.print(f"  [link={u}]{u}[/]")


def write_markdown_report(
    product_query: str,
    mentions: list[Mention],
    with_sentiment: list[tuple[Mention, SentimentResult]],
    insights: list[Insight],
    path: Path,
    data_range: str | None = None,
) -> None:
    platform_breakdown = dict(Counter(m.platform for m in mentions))
    top_subs: dict[str, int] = {}
    for m in mentions:
        sub = (m.extra or {}).get("subreddit")
        if sub:
            top_subs[sub] = top_subs.get(sub, 0) + 1
    top_subs = dict(sorted(top_subs.items(), key=lambda x: -x[1])[:15])

    total = len(mentions)
    labels = Counter(s.label for _, s in with_sentiment) if with_sentiment else {}

    def pct(k: str) -> float:
        return round(100 * labels.get(k, 0) / total, 1) if total else 0

    top_platform = (
        max(platform_breakdown.items(), key=lambda x: x[1])[0] if platform_breakdown else "—"
    )
    lines = [
        f"# Product sentiment report: {product_query}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}Z",
        "",
    ]
    if data_range:
        lines.append(f"*Data range: {data_range}*")
        lines.append("")
    lines.extend(
        [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total mentions | {total} |",
            f"| Positive | {pct('positive')}% |",
            f"| Negative | {pct('negative')}% |",
            f"| Neutral | {pct('neutral')}% |",
            f"| Top platform | {top_platform} |",
            "",
            "### By platform",
            "",
        ]
    )
    for plat, count in sorted(platform_breakdown.items(), key=lambda x: -x[1]):
        lines.append(f"- **{plat}**: {count}")
    if top_subs:
        lines.extend(["", "### Top subreddits", ""])
        for sub, count in list(top_subs.items())[:15]:
            lines.append(f"- **r/{sub}**: {count}")
    lines.extend(
        [
            "",
            "---",
            "",
            "## Sentiment summary",
            "",
        ]
    )
    if with_sentiment:
        labels = Counter(s.label for _, s in with_sentiment)
        for label, count in labels.most_common():
            lines.append(f"- **{label}**: {count}")
        lines.append("")
    lines.append("## Insights for product creators")
    lines.append("")
    for ins in insights:
        lines.append(f"### {ins.kind.replace('_', ' ').title()} (n={ins.count})")
        lines.append("")
        lines.append(ins.summary)
        lines.append("")
        if ins.representative_quotes:
            lines.append("**Sample quotes:**")
            for q in ins.representative_quotes:
                lines.append(f"- {decode_html_entities(q)}")
            lines.append("")
        if ins.platform_counts:
            lines.append(f"*Platforms: {ins.platform_counts}*")
            lines.append("")
        if ins.source_urls:
            lines.append("**Sources:**")
            for u in ins.source_urls:
                lines.append(f"- {u}")
            lines.append("")
        lines.append("---")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]Report written to {path}[/]")


def _filter_by_sentiment(
    mentions: list[Mention],
    with_sentiment: list[tuple[Mention, SentimentResult]],
    label: str,
) -> tuple[list[Mention], list[tuple[Mention, SentimentResult]]]:
    """Keep only mentions with the given sentiment label (e.g. 'negative')."""
    if not label or label == "all":
        return mentions, with_sentiment
    sent_by_id = {id(m): s for m, s in with_sentiment}
    filtered_mentions = [
        m for m in mentions if sent_by_id.get(id(m)) and sent_by_id[id(m)].label == label
    ]
    filtered_ws = [(m, s) for m, s in with_sentiment if s.label == label]
    return filtered_mentions, filtered_ws


def write_json_output(
    product_query: str,
    mentions: list[Mention],
    with_sentiment: list[tuple[Mention, SentimentResult]],
    insights: list[Insight],
    path: Path,
    data_range: str | None = None,
) -> None:
    """Write full pipeline output as JSON for downstream use."""

    def mention_to_dict(m: Mention) -> dict:
        return {
            "source": m.source,
            "platform": m.platform,
            "title": decode_html_entities(m.title),
            "body": decode_html_entities((m.body or "")[:5000]),
            "url": m.url or "",
            "author": m.author,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "score": m.score,
            "extra": m.extra or {},
        }

    platform_breakdown = dict(Counter(m.platform for m in mentions))
    top_subreddits: dict[str, int] = {}
    for m in mentions:
        sub = (m.extra or {}).get("subreddit")
        if sub:
            top_subreddits[sub] = top_subreddits.get(sub, 0) + 1
    top_subreddits = dict(sorted(top_subreddits.items(), key=lambda x: -x[1])[:20])

    payload = {
        "product_query": product_query,
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "total_mentions": len(mentions),
        "sentiment_summary": dict(Counter(s.label for _, s in with_sentiment)),
        "platform_breakdown": platform_breakdown,
        "top_subreddits": top_subreddits,
        **({"data_range": data_range} if data_range else {}),
        "mentions": [mention_to_dict(m) for m in mentions],
        "mentions_with_sentiment": [
            {
                "mention": mention_to_dict(m),
                "sentiment": {
                    "label": s.label,
                    "score": s.score,
                    "positive": s.positive,
                    "negative": s.negative,
                    "neutral": s.neutral,
                },
            }
            for m, s in (with_sentiment or [])
        ],
        "insights": [ins.to_dict() for ins in insights],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]JSON written to {path}[/]")


def write_insights_output(
    product_query: str,
    with_sentiment: list[tuple[Mention, SentimentResult]],
    insights: list[Insight],
    path: Path,
) -> None:
    """Write insights to JSON or CSV (by path suffix)."""
    if path.suffix.lower() == ".csv":
        _write_insights_csv(insights, path)
    else:
        payload = {
            "product_query": product_query,
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
            "sentiment_summary": dict(Counter(s.label for _, s in with_sentiment)),
            "insights": [ins.to_dict() for ins in insights],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]Insights JSON written to {path}[/]")


def _write_insights_csv(insights: list[Insight], path: Path) -> None:
    """Write insights table to CSV."""
    import csv

    rows = [["kind", "summary", "count", "sentiment", "platform_counts", "sample_quotes"]]
    for ins in insights:
        quotes = " | ".join(ins.representative_quotes[:3]) if ins.representative_quotes else ""
        rows.append(
            [
                ins.kind,
                ins.summary[:500] if ins.summary else "",
                ins.count,
                ins.sentiment,
                json.dumps(ins.platform_counts) if ins.platform_counts else "",
                quotes,
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    console.print(f"[green]Insights CSV written to {path}[/]")


def _check_config() -> None:
    """Print which sources are available and exit."""
    from rich.table import Table

    table = Table(title="Source availability")
    table.add_column("Source", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Note")
    for name in ["hackernews", "duckduckgo", "reddit", "web"]:
        if name not in SOURCES:
            continue
        cls, is_available = SOURCES[name]
        if is_available():
            table.add_row(name, "OK", "Ready")
        else:
            hint = SOURCE_HINTS.get(name, "")
            table.add_row(name, "—", f"Not configured.{hint}")
    console.print(table)
    console.print(
        "[dim]Run with --sources SOURCE1,SOURCE2 (e.g. hackernews,duckduckgo need no config).[/]"
    )


def _slug(product: str) -> str:
    """Safe filename slug from product query."""
    s = re.sub(r"[^\w\-]", "_", product.lower()).strip("_")[:50]
    return s or "product"


def write_csv_output(
    mentions: list[Mention],
    with_sentiment: list[tuple[Mention, SentimentResult]],
    path: Path,
) -> None:
    """Write mentions with sentiment to CSV for spreadsheets."""
    import csv

    rows = [
        [
            "platform",
            "source",
            "title",
            "body",
            "url",
            "author",
            "score",
            "sentiment",
            "sentiment_score",
        ]
    ]
    sent_by_idx = {id(m): s for m, s in (with_sentiment or [])}
    for m in mentions:
        s = sent_by_idx.get(id(m))
        title = decode_html_entities(m.title)
        body = decode_html_entities((m.body or "")[:2000]).replace("\n", " ")
        rows.append(
            [
                m.platform,
                m.source,
                title,
                body,
                m.url or "",
                m.author or "",
                str(m.score) if m.score is not None else "",
                s.label if s else "",
                f"{s.score:.3f}" if s else "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    console.print(f"[green]CSV written to {path}[/]")


def main():
    parser = argparse.ArgumentParser(
        description="Crawl the web for product mentions and surface sentiment insights (free sources).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check config and list which sources are available; then exit.",
    )
    parser.add_argument(
        "product",
        nargs="?",
        default="",
        help="Product name or search query (omit when using --batch)",
    )
    parser.add_argument(
        "--batch",
        type=Path,
        default=None,
        metavar="FILE",
        help="Run for each line in FILE (one product per line; # comments ignored). Use -o as output directory.",
    )
    parser.add_argument(
        "--sources",
        default="hackernews,duckduckgo,reddit,web",
        help="Comma-separated: hackernews, duckduckgo, reddit, web (default: hackernews,duckduckgo,reddit,web)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=80,
        help="Max mentions per source (default 80)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="N",
        help="Limit to last N days (Reddit: time_filter; HN: created_at filter)",
    )
    parser.add_argument(
        "--subreddits",
        type=str,
        default=None,
        metavar="r1,r2",
        help="Reddit only: search these subreddits (e.g. Notion,productivity)",
    )
    parser.add_argument(
        "--min-text-length",
        type=int,
        default=0,
        metavar="L",
        help="Drop mentions with combined title+body length < L (default 0)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=None,
        metavar="word1,word2",
        help="Drop mentions containing any of these words (case-insensitive, comma-separated)",
    )
    parser.add_argument(
        "--include-comments",
        type=int,
        default=0,
        metavar="N",
        help="Reddit only: fetch up to N top-level comments per post (default 0)",
    )
    parser.add_argument(
        "--reddit-sort",
        type=str,
        default="relevance",
        choices=["relevance", "hot", "new", "top", "comments", "rising"],
        help="Reddit search sort order (default: relevance)",
    )
    parser.add_argument(
        "--reddit-min-score",
        type=int,
        default=0,
        metavar="N",
        help="Reddit only: skip submissions with score < N (default 0)",
    )
    parser.add_argument(
        "--sentiment",
        type=str,
        default="all",
        choices=["all", "positive", "negative", "neutral"],
        help="Export only mentions with this sentiment (default: all)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write Markdown report to this file",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Write full JSON (mentions + sentiment + insights) to this file",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=None,
        help="Write mentions + sentiment to CSV",
    )
    parser.add_argument(
        "--insights-output",
        type=Path,
        default=None,
        help="Write insights-only JSON (small file for dashboards)",
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Skip printing summary to console",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable file cache (default: use cache if CACHE_DIR set)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()
    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)
        get_logger("sources").setLevel(logging.DEBUG)
        get_logger("run").setLevel(logging.DEBUG)
        log.debug("Verbose logging enabled")

    if args.check:
        _check_config()
        return

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    use_cache = not args.no_cache and bool(config.CACHE_DIR)
    cache_dir = Path(config.CACHE_DIR) if config.CACHE_DIR else None
    subreddits = None
    if args.subreddits:
        subreddits = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    exclude_words = [w.strip() for w in (args.exclude or "").split(",") if w.strip()]
    data_range = f"last {args.days} days" if args.days else None

    if args.batch:
        if not args.batch.exists():
            console.print(f"[red]Batch file not found: {args.batch}[/]")
            sys.exit(1)
        products = [
            line.strip()
            for line in args.batch.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        products = list(dict.fromkeys(products))  # dedupe, preserve order
        if not products:
            console.print("[red]No product lines in batch file.[/]")
            sys.exit(1)
        out_dir = (
            (args.output if args.output.is_dir() else args.output.parent)
            if args.output
            else Path(".")
        )
        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, product in enumerate(products):
            console.print(f"\n[bold][{i + 1}/{len(products)}] {product}[/]")
            mentions, with_sentiment, insights = run_pipeline(
                product,
                sources,
                args.limit,
                use_cache,
                cache_dir,
                verbose=args.verbose,
                days=args.days,
                subreddits=subreddits,
                min_text_length=args.min_text_length or 0,
                exclude_words=exclude_words,
                include_comments=args.include_comments or 0,
                reddit_sort=args.reddit_sort or "relevance",
                reddit_min_score=getattr(args, "reddit_min_score", 0) or 0,
            )
            if mentions is None:
                continue
            export_mentions = mentions
            export_with_sentiment = with_sentiment or []
            if getattr(args, "sentiment", None) and args.sentiment != "all":
                export_mentions, export_with_sentiment = _filter_by_sentiment(
                    mentions, export_with_sentiment, args.sentiment
                )
            if not args.no_print:
                print_summary(export_mentions, export_with_sentiment, insights)
            slug = _slug(product)
            write_markdown_report(
                product,
                export_mentions,
                export_with_sentiment,
                insights,
                out_dir / f"{slug}.md",
                data_range=data_range,
            )
            if args.json_output:
                write_json_output(
                    product,
                    export_mentions,
                    export_with_sentiment,
                    insights,
                    out_dir / f"{slug}.json",
                    data_range=data_range,
                )
            if args.csv_output:
                write_csv_output(export_mentions, export_with_sentiment, out_dir / f"{slug}.csv")
            if args.insights_output:
                write_insights_output(
                    product, export_with_sentiment, insights, out_dir / f"{slug}_insights.json"
                )
        console.print(f"\n[green]Batch done. Reports in {out_dir}[/]")
        return

    product = args.product.strip()
    if not product:
        parser.print_help()
        console.print("\n[yellow]Example: python run.py 'Notion'[/]")
        sys.exit(1)

    mentions, with_sentiment, insights = run_pipeline(
        product,
        sources,
        args.limit,
        use_cache,
        cache_dir,
        verbose=args.verbose,
        days=args.days,
        subreddits=subreddits,
        min_text_length=args.min_text_length or 0,
        exclude_words=exclude_words,
        include_comments=args.include_comments or 0,
        reddit_sort=args.reddit_sort or "relevance",
        reddit_min_score=getattr(args, "reddit_min_score", 0) or 0,
    )
    if mentions is None:
        sys.exit(1)

    # Optional sentiment filter for output (and console summary)
    export_mentions = mentions
    export_with_sentiment = with_sentiment or []
    if getattr(args, "sentiment", None) and args.sentiment != "all":
        export_mentions, export_with_sentiment = _filter_by_sentiment(
            mentions, export_with_sentiment, args.sentiment
        )
        if args.sentiment and args.sentiment != "all" and export_mentions:
            console.print(
                f"[dim]Exporting only [bold]{args.sentiment}[/] mentions ({len(export_mentions)}).[/]"
            )

    if not args.no_print:
        print_summary(export_mentions, export_with_sentiment, insights)

    written: list[Path] = []
    if args.output:
        write_markdown_report(
            product,
            export_mentions,
            export_with_sentiment,
            insights,
            args.output,
            data_range=data_range,
        )
        written.append(args.output)
    if args.json_output:
        write_json_output(
            product,
            export_mentions,
            export_with_sentiment,
            insights,
            args.json_output,
            data_range=data_range,
        )
        written.append(args.json_output)
    if args.csv_output:
        write_csv_output(export_mentions, export_with_sentiment, args.csv_output)
        written.append(args.csv_output)
    if args.insights_output:
        write_insights_output(product, export_with_sentiment, insights, args.insights_output)
        written.append(args.insights_output)
    if written:
        console.print(f"[dim]Wrote: {', '.join(str(p) for p in written)}[/]")


if __name__ == "__main__":
    main()
