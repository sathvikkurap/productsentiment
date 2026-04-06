"""HTTP fetch with retries and rate limiting."""

import time
from typing import Any

import requests

# Module-level rate limit: min seconds between requests per domain
_last_request: dict[str, float] = {}
_min_interval = 0.5  # be nice to free APIs


def _rate_limit(domain: str) -> None:
    key = domain
    now = time.monotonic()
    if key in _last_request:
        elapsed = now - _last_request[key]
        if elapsed < _min_interval:
            time.sleep(_min_interval - elapsed)
    _last_request[key] = time.monotonic()


def fetch_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    max_retries: int = 3,
) -> dict[str, Any] | None:
    """GET URL, parse JSON. Retries with backoff. Returns None on failure."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc or "default"
    for attempt in range(max_retries):
        try:
            _rate_limit(domain)
            r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == max_retries - 1:
                return None
            time.sleep(2**attempt)
    return None


def fetch_text(
    url: str,
    params: dict[str, Any] | None = None,
    timeout: int = 20,
    max_retries: int = 2,
) -> str | None:
    """GET URL, return text. Retries with backoff."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc or "default"
    for attempt in range(max_retries):
        try:
            _rate_limit(domain)
            r = requests.get(url, params=params or {}, timeout=timeout)
            r.raise_for_status()
            return r.text
        except requests.RequestException:
            if attempt == max_retries - 1:
                return None
            time.sleep(2**attempt)
    return None
