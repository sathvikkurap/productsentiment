# Changelog

## [Unreleased]

### Added

- **make setup**: One-command setup after clone (create .venv, install deps, copy .env.example → .env if missing). README Option B; CONTRIBUTING Setup updated.
- **make check**: Runs `run.py --check` to show which sources are available (no fetch). README Development section updated.

### Changed

- (none)

## [0.2.0] - 2025-03-17

### Added

- **`--check`**: Show which sources are available (no fetch); table with status and hints.
- **Insights CSV**: Use `--insights-output path.csv` to write insights as CSV for spreadsheets.
- **Export summary**: Single-run prints "Wrote: path1, path2" after writing files.
- **Makefile `help`**: Default `make` shows all targets; `make help` documents each command.
- **Troubleshooting**: README section for no mentions, Reddit 401/rate limit, subreddit errors.
- **Quick start script**: `scripts/quickstart.sh` creates venv, installs deps, runs `--check`.
- **Batch dedupe**: Duplicate product lines in `--batch FILE` are run once (order preserved).
- **LICENSE**: AGPL-3.0.
- **Tests**: `test_exclude_filter`, `test_slug`; 9 smoke tests total.
- **.gitignore**: Root ignore for .env, .venv, __pycache__, ruff/pytest cache, IDE, OS files.
- **Output dirs**: Report and export paths auto-create parent directories (e.g. `-o reports/notion.md`).
- **CI**: GitHub Actions run tests (Python 3.10–3.12) and lint (ruff) on push/PR.
- **Pre-commit**: `.pre-commit-config.yaml` for ruff (check + format); run `pre-commit install` then `pre-commit run --all-files`.
- **Tests**: `test_check_config_runs` (config check runs without error; output suppressed in test).
- **Tests**: `test_write_markdown_creates_dir` (writing a report to a new subdir creates the directory and file).
- **Docs**: CONTRIBUTING note to update `_version.py` and `pyproject.toml` when releasing.
- **Docs**: requirements.txt header and CONTRIBUTING note to keep deps in sync with pyproject.toml.
- **Docs**: README Development section mentions optional pre-commit for lint on commit.
- **Docs**: README Changelog section with link to CHANGELOG.md.
- **Docs**: README Setup reminder not to commit `.env` (secrets).
- **Docs**: README Setup states Python 3.10+ requirement.
- **Quick start**: `scripts/quickstart.sh` creates `.env` from `.env.example` if missing.
- **Docs**: README Usage notes `python run.py` or `python -m run` from project root.
- **CLI entry point**: After `pip install -e .`, run `productreviews` from any directory (thin `productreviews` package invokes `run.main`).
- **Docs**: CONTRIBUTING release checklist (version, CHANGELOG, test, lint, tag, publish) and Setup suggests `pip install -e ".[dev]"` for lint.
- **Docs**: README quick reference line for `--check`, `--version`, `--help`.

### Changed

- **run.py**: Use `datetime.now(timezone.utc)` instead of deprecated `datetime.utcnow()` for report timestamps.
- **Lint**: Makefile `make lint` uses `python -m ruff` (works with venv). Ruff config moved to `[tool.ruff.lint]`; imports and style fixed project-wide.
- **CI**: Lint job installs project with `pip install -e ".[dev]"` and runs `make lint` so CI matches local dev.
- **Docker**: Image installs package and uses `productreviews` entry point; `docker run ... productreviews "Notion"` unchanged.
- **Docs**: README project structure includes `productreviews/`, `_version.py`, `pyproject.toml`; Docker section notes image runs `productreviews` command.

## [0.1.0]

### Added

- **Sources**: Hacker News (Algolia), DuckDuckGo, Reddit (PRAW), optional Brave/SerpAPI web search.
- **Sentiment**: VADER-based analysis; one-line summary and breakdown table in console.
- **Insights**: Pain points, praise, feature requests, pricing/value, comparisons, themes; HTML entity decoding and theme noise filtering.
- **Output**: Markdown report (with key metrics table, platform breakdown, top subreddits, data range), full JSON, CSV, insights-only JSON.
- **Filters**: `--days`, `--subreddits`, `--min-text-length`, `--exclude` (keywords), `--sentiment`, `--reddit-min-score`.
- **Reddit**: Optional top-level comments (`--include-comments`), sort order (`--reddit-sort`), clearer error messages.
- **Batch mode**: `--batch FILE` with one product per line; output directory from `-o`.
- **Cache**: File cache keyed by source, query, and options (days, subreddits, etc.).
- **CLI**: `--version`, source hints when skipping unconfigured sources.
- **Docker**: Dockerfile and `.dockerignore`; optional `make docker-build` / `make docker-run`.
- **Dev**: `make test`, `make lint` (ruff), `pyproject.toml` with deps and Ruff config, smoke tests including slug and cache key.

### Notes

- All listed features are free-tier friendly; Reddit and web search require optional API keys.
