"""Reddit data source using PRAW."""

from datetime import datetime
from typing import Iterator

import config
from sources.base import Mention, Source


class RedditSource(Source):
    """Fetch product discussions from Reddit via PRAW."""

    @property
    def name(self) -> str:
        return "reddit"

    def _reddit_client(self):
        import praw

        return praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT,
        )

    def fetch(
        self,
        product_query: str,
        limit: int | None = None,
        *,
        days: int | None = None,
        subreddits: list[str] | None = None,
        **kwargs: object,
    ) -> Iterator[Mention]:
        limit = limit or config.REDDIT_SEARCH_LIMIT
        if not config.REDDIT_CLIENT_ID or not config.REDDIT_CLIENT_SECRET:
            return
        try:
            reddit = self._reddit_client()
        except Exception:
            return
        # Reddit time_filter: hour, day, week, month, year, all
        time_filter = "year"
        if days is not None:
            if days <= 1:
                time_filter = "day"
            elif days <= 7:
                time_filter = "week"
            elif days <= 31:
                time_filter = "month"
            else:
                time_filter = "year"
        subreddit_name = "all"
        if subreddits:
            # e.g. ["Notion", "productivity"] -> "Notion+productivity"
            subreddit_name = "+".join(s.strip().strip("/") for s in subreddits if s.strip())
        if not subreddit_name:
            subreddit_name = "all"
        sort_order = kwargs.get("reddit_sort") or "relevance"
        if sort_order not in ("relevance", "hot", "new", "top", "comments", "rising"):
            sort_order = "relevance"
        include_comments = int(kwargs.get("include_comments") or 0)
        min_score = int(kwargs.get("reddit_min_score") or 0)

        try:
            for submission in reddit.subreddit(subreddit_name).search(
                product_query,
                limit=min(limit, 1000),
                time_filter=time_filter,
                sort=sort_order,
            ):
                if min_score > 0 and (submission.score or 0) < min_score:
                    continue
                created = (
                    datetime.fromtimestamp(submission.created_utc)
                    if submission.created_utc
                    else None
                )
                extra = {
                    "num_comments": submission.num_comments,
                    "subreddit": submission.subreddit.display_name,
                }
                yield Mention(
                    source="reddit",
                    platform="reddit",
                    title=submission.title or "",
                    body=(submission.selftext or "")[:10000],
                    url=f"https://reddit.com{submission.permalink}" if submission.permalink else "",
                    author=submission.author.name if submission.author else None,
                    created_at=created,
                    score=submission.score,
                    extra=extra,
                )
                # Optional: top-level comments as separate mentions for more sentiment signal
                if include_comments > 0 and submission.permalink:
                    try:
                        submission.comments.replace_more(limit=0)
                        for comm in list(submission.comments)[:include_comments]:
                            if not getattr(comm, "body", None):
                                continue
                            yield Mention(
                                source="reddit",
                                platform="reddit",
                                title=f"Comment: {(submission.title or '')[:80]}",
                                body=(comm.body or "")[:8000],
                                url=f"https://reddit.com{submission.permalink}"
                                if submission.permalink
                                else "",
                                author=comm.author.name if comm.author else None,
                                created_at=datetime.fromtimestamp(comm.created_utc)
                                if getattr(comm, "created_utc", None)
                                else None,
                                score=getattr(comm, "score", None),
                                extra={
                                    "is_comment": True,
                                    "subreddit": submission.subreddit.display_name,
                                },
                            )
                    except Exception:
                        pass
        except ValueError:
            raise
        except Exception as e:
            err = str(e).lower()
            if "rate" in err or "429" in err:
                raise RuntimeError(
                    "Reddit: rate limited. Wait a few minutes or reduce --limit."
                ) from e
            if "401" in err or "invalid" in err or "oauth" in err or "client" in err:
                raise ValueError(
                    "Reddit: invalid credentials. Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env."
                ) from e
            if "404" in err or "subreddit" in err or "private" in err or "banned" in err:
                raise ValueError(
                    f"Reddit: subreddit '{subreddit_name}' not found, private, or invalid."
                ) from e
            return
