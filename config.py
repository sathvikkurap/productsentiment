"""Load configuration from environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# Reddit
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "ProductSentimentCrawler/1.0")

# Web search (optional)
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Crawl limits
REDDIT_SEARCH_LIMIT = int(os.getenv("REDDIT_SEARCH_LIMIT", "200"))
WEB_SEARCH_LIMIT = int(os.getenv("WEB_SEARCH_LIMIT", "50"))
HN_SEARCH_LIMIT = int(os.getenv("HN_SEARCH_LIMIT", "100"))
DUCKDUCKGO_LIMIT = int(os.getenv("DUCKDUCKGO_LIMIT", "50"))

# Cache (seconds; 0 = disable)
CACHE_MAX_AGE = int(os.getenv("CACHE_MAX_AGE", "3600"))  # 1 hour
CACHE_DIR = os.getenv("CACHE_DIR", "")  # empty = no file cache
