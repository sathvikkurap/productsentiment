# Product Sentiment Crawler

A **fully free** tool that crawls the web for product mentions (Reddit, Hacker News, DuckDuckGo, and optional Brave/SerpAPI), analyzes user sentiment, and surfaces **novel and valuable insights** for product creators—pain points, praise, feature requests, pricing discussion, comparisons, and recurring themes.

**Quick run (no API keys):** `python run.py 'Product' --sources hackernews,duckduckgo`  
Use `--check` to see available sources, `--version` for version, `--help` for all options.

## What it does

- **Gathers mentions** from:
  - **Hacker News** (Algolia API, free, no key)
  - **DuckDuckGo** (free, no key) — surfaces Reddit, LinkedIn, Twitter, blogs in results
  - **Reddit** (PRAW, free app credentials)
  - **Web** (Brave Search or SerpAPI when keys are set)
- **Deduplicates** by URL and content hash so the same discussion isn’t counted twice.
- **Rate limits and retries** — respectful of free APIs; exponential backoff on failures.
- **Optional file cache** — reuse recent fetches (set `CACHE_DIR` and `CACHE_MAX_AGE`).
- **Analyzes sentiment** (positive / negative / neutral) with VADER.
- **Extracts insights**:
  - **Pain points** — problems, bugs, frustration
  - **Praise** — what people love and recommend
  - **Feature requests** — wishes, “should add”, “would be nice”
  - **Pricing / value** — cost, value, subscriptions
  - **Comparisons** — alternatives, vs. competitors, switching
  - **Themes** — frequently discussed topics

Output: rich console summary, Markdown report (with key metrics table: total, positive/negative/neutral %, top platform), JSON (full pipeline), and/or CSV (mentions + sentiment). Quotes and report text are cleaned (HTML entities decoded); theme extraction filters URL/noise tokens.

## Setup (all free)

Requires **Python 3.10+**.

**Option A — quick start (Unix/macOS):**

```bash
cd productreviews
./scripts/quickstart.sh
source .venv/bin/activate
python run.py "Notion" --sources hackernews,duckduckgo --limit 20
```

**Option B — make setup (after clone):**

```bash
cd productreviews
make setup
source .venv/bin/activate   # then run: python run.py "Notion" --sources hackernews,duckduckgo
```

**Option C — manual:**

```bash
cd productreviews
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or: pip install -e .   (uses pyproject.toml)
cp .env.example .env
# .env can stay empty to use only free sources (Hacker News + DuckDuckGo)
# Do not commit .env (it's in .gitignore); it may contain API keys.
```

**No API keys required** to start: use `--sources hackernews,duckduckgo`.  
Optional: add Reddit (free app at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)) and/or Brave/SerpAPI for more coverage.  
`python run.py --version` prints the current version.  
`python run.py --check` shows which sources are available (no fetch).

## Usage

After `pip install -e .` you can run `productreviews` from anywhere; from the project root you can also use `python run.py` or `python -m run`.

```bash
# Free only: Hacker News + DuckDuckGo (no .env needed)
python run.py "Notion" --sources hackernews,duckduckgo

# All configured sources (default)
python run.py "Figma"

# Save Markdown, JSON, and CSV
python run.py "Linear app" -o report.md --json-output report.json --csv-output mentions.csv

# Reddit + HN + DuckDuckGo, 100 per source
python run.py "Vercel" --sources reddit,hackernews,duckduckgo --limit 100

# Disable cache for this run
python run.py "Product" --no-cache

# Last 30 days only (Reddit + HN)
python run.py "Notion" --days 30

# Reddit: only r/Notion and r/productivity
python run.py "Notion" --subreddits Notion,productivity --sources reddit

# Drop very short mentions (e.g. title+body < 50 chars)
python run.py "Figma" --min-text-length 50

# Reddit: fetch 5 top-level comments per post (more sentiment signal)
python run.py "Notion" --sources reddit --include-comments 5

# Reddit: sort by new or top
python run.py "Notion" --reddit-sort new

# Export only negative mentions (CSV/JSON/report)
python run.py "Product" --sentiment negative -o negatives.md --csv-output negatives.csv

# Batch: one product per line (use -o as output directory)
echo -e "Notion\nFigma\nLinear" > products.txt
python run.py --batch products.txt -o reports/ --json-output
# Writes reports/notion.md, reports/figma.md, reports/linear.md (+ .json/.csv if flags set)
```

### Arguments

| Argument | Description |
|----------|-------------|
| `product` | Product name or search query (omit when using `--batch`). |
| `--batch` | Path to a file: one product per line (`#` lines ignored). Writes `{slug}.md` (and optional .json/.csv) into the output directory. |
| `--sources` | Comma-separated: `hackernews`, `duckduckgo`, `reddit`, `web` (default: all four; unavailable ones skipped). |
| `--limit` | Max mentions per source (default 80). |
| `--days` | Limit to last N days (Reddit time_filter; HN created_at filter). |
| `--subreddits` | Reddit only: comma-separated subreddit names (e.g. `Notion,productivity`). |
| `--min-text-length` | Drop mentions with combined title+body length below this (default 0). |
| `--exclude` | Drop mentions containing any of these words (comma-separated, case-insensitive). |
| `--include-comments` | Reddit only: fetch up to N top-level comments per post (default 0). |
| `--reddit-sort` | Reddit search sort: `relevance`, `hot`, `new`, `top`, `comments`, `rising` (default: relevance). |
| `--reddit-min-score` | Reddit only: skip submissions with score below this (default: 0). |
| `--sentiment` | Export only this sentiment: `all`, `positive`, `negative`, `neutral` (default: all). |
| `--output`, `-o` | Write Markdown report to this file. |
| `--json-output` | Write full JSON (mentions, sentiment, insights) to this file. |
| `--csv-output` | Write mentions + sentiment to CSV (for spreadsheets). |
| `--insights-output` | Write insights to JSON or CSV (use `.csv` extension for spreadsheet). |
| `--check` | Show which sources are available (no fetch); then exit. |
| `--no-print` | Don’t print summary to console. |
| `--no-cache` | Ignore file cache for this run. |
| `--verbose`, `-v` | Verbose logging. |

## Platforms (free vs optional)

| Source | Cost | Notes |
|--------|------|--------|
| **Hacker News** | Free, no key | Algolia public API. |
| **DuckDuckGo** | Free, no key | Web search; results often include Reddit, LinkedIn, Twitter, etc. |
| **Reddit** | Free | PRAW; create a script app, set `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`. |
| **Web** | Free tier | Brave or SerpAPI in `.env`; surfaces more platforms via search. |

LinkedIn, Facebook, Instagram are only included when they appear in **search results** (e.g. DuckDuckGo or Brave). The tool does not scrape those platforms directly.

## Project structure

```
productreviews/
├── config.py              # Env-based config
├── run.py                 # Main CLI logic
├── _version.py
├── pyproject.toml
├── requirements.txt
├── .env.example
├── productreviews/        # Thin wrapper for 'productreviews' console script
├── sources/
│   ├── base.py            # Mention, Source ABC
│   ├── reddit_source.py
│   ├── hackernews_source.py
│   ├── duckduckgo_source.py
│   └── web_search_source.py  # Brave / SerpAPI
├── sentiment/
│   └── analyzer.py       # VADER (singleton)
├── insights/
│   └── extractor.py      # Pain, praise, feature requests, pricing, comparison, themes
├── utils/
│   ├── fetch.py           # HTTP with retries and rate limit
│   ├── dedupe.py          # URL + content-hash dedupe
│   ├── cache.py           # Optional file cache
│   ├── text.py            # HTML entity decode, normalize whitespace
│   └── logging.py
├── tests/
│   └── test_smoke.py
└── scripts/
    └── quickstart.sh
```

## Tests

```bash
python -m unittest tests.test_smoke -v
```

## Development

```bash
make              # Show make targets (help)
make check        # Show which sources are available (no fetch)
make test         # Run tests (or: python -m unittest tests.test_smoke -v)
make lint         # Lint (requires dev deps: pip install -e ".[dev]")
make run-example  # Quick run (free sources, no .env)

# Install deps (with venv active)
make install

# Optional: run lint on commit (install pre-commit, then)
pre-commit install && pre-commit run --all-files
```

## Docker

The image installs the package and runs the `productreviews` command (same as after `pip install -e .`).

```bash
# Build
docker build -t productreviews .

# Run (free sources only)
docker run --rm productreviews "Notion" --sources hackernews,duckduckgo --limit 20

# With .env for Reddit/API keys (mount and write output to host)
docker run --rm -v $(pwd)/.env:/app/.env -v $(pwd)/out:/out productreviews "Notion" -o /out/report.md --json-output /out/report.json
```

Cache is keyed by source, query, and options (days, subreddits, include_comments, reddit_sort), so different runs use different cache entries.

## Troubleshooting

| Issue | What to try |
|-------|--------------|
| **No mentions found** | Broaden the query (e.g. "Notion" → "Notion app"); try `--sources hackernews,duckduckgo`; check `python run.py --check` to see which sources are active. |
| **Reddit 401 / invalid credentials** | Create a script app at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps); set `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in `.env`. |
| **Reddit rate limited** | Wait a few minutes; reduce `--limit`; avoid running many times in a short period. |
| **Subreddit not found / private** | Check `--subreddits` spelling (e.g. `Notion` not `r/Notion`); that subreddit may be private or banned. |
| **DuckDuckGo / HN slow or empty** | Normal for some queries; try Reddit or web search if you have API keys. |

Run `python run.py --check` to confirm which sources are available before a full run.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for running tests, linting, and adding new sources.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and unreleased changes.

## License

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html) (AGPL-3.0). See [LICENSE](LICENSE) for the full text.

When you run the crawler, comply with each service’s terms (Reddit, Algolia, DuckDuckGo, Brave, SerpAPI) and their rate limits.
