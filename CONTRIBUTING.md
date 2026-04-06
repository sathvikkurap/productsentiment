# Contributing

Thanks for considering contributing to the Product Sentiment Crawler.

## Setup

```bash
git clone <repo>
cd productreviews
make setup                  # creates .venv, installs deps, copies .env.example → .env if needed
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"     # optional, for lint (ruff) and tests (pytest)
```

Optional: install [pre-commit](https://pre-commit.com/) and run `pre-commit install`. Then `pre-commit run --all-files` (or it runs on git commit) will run ruff check and format.

## Running tests

```bash
python -m unittest tests.test_smoke -v
# or
make test
```

Tests are in `tests/test_smoke.py` and cover imports, dedupe, sentiment, insights, filter, cache key, slug, and config check. No network is required for the current tests.

## Linting

```bash
ruff check .
ruff format --check .
# or
make lint
```

The project uses Ruff; config is in `pyproject.toml` (`[tool.ruff]`). Line length 100, target Python 3.10+.

## Adding a new source

1. Create a new file in `sources/` (e.g. `sources/news_source.py`).
2. Implement the `Source` interface:
   - `name` property (str)
   - `fetch(product_query, limit, *, days=None, subreddits=None, **kwargs)` yielding `Mention` objects.
3. Register the source in `run.py`: add to `SOURCES` and optionally to `SOURCE_HINTS` if it needs config.
4. Add any new env vars to `.env.example` and `config.py`.
5. Add a test or extend `test_imports` to cover the new module.

## Code style

- Use type hints for function arguments and returns where practical.
- Prefer the existing patterns (e.g. `Mention` dataclass, `Source` ABC, rich for console output).
- Keep new dependencies minimal and document them in `requirements.txt` and `pyproject.toml`.

## Version

When releasing, update the version in both `_version.py` and `pyproject.toml` so `run.py --version` and `pip show productreviews` stay in sync.

## Release checklist

When cutting a new release (e.g. v0.2.0):

1. **Version**: Set the new version in `_version.py` and `pyproject.toml`.
2. **CHANGELOG**: Under `## [Unreleased]`, add a new `## [X.Y.Z] - YYYY-MM-DD` section; move the relevant "Added" / "Changed" items into it; leave "Unreleased" for future work.
3. **Tests and lint**: Run `make test` and `make lint`.
4. **Tag**: e.g. `git tag v0.2.0` and push the tag.
5. **Publish** (optional): Build and publish to PyPI or your package index.

## Dependencies

When adding or changing runtime dependencies, update both `pyproject.toml` `[project].dependencies` and `requirements.txt` so both install paths work.

## Pull requests

- Run `make test` and `make lint` before submitting.
- Keep PRs focused; link any related issues.
