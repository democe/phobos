import logging
import re
from datetime import datetime, timezone

from sources.base import Item

logger = logging.getLogger(__name__)

_SESSION_URL = "https://x.com/home"
_STATUS_PATH_RE = re.compile(r"^/([^/]+)/status/(\d+)")

_DEFAULT_COUNT = 20
_DEFAULT_MAX_SCROLLS = 8
_DEFAULT_SCROLL_PAUSE_MS = 1200
_SESSION_PRIME_WAIT_MS = 1200


def fetch(config: dict, browser) -> list[Item]:
    context = browser.new_context(
        viewport={"width": 1280, "height": 2200},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    items: list[Item] = []
    try:
        _apply_auth_cookies(context, config)
        _prime_session(context)
        allowed_authors = None
        if config.get("filter_usernames", False):
            allowed_authors = {
                username.lstrip("@").lower()
                for username in config.get("usernames", [])
                if username and username.strip()
            } or None

        items = _scrape_home_feed(
            context=context,
            count=config.get("count", _DEFAULT_COUNT),
            max_scrolls=config.get("max_scrolls", _DEFAULT_MAX_SCROLLS),
            scroll_pause_ms=config.get("scroll_pause_ms", _DEFAULT_SCROLL_PAUSE_MS),
            allowed_authors=allowed_authors,
        )
    except Exception as e:
        logger.warning("Failed to fetch tweets from home feed: %s", e)
    finally:
        context.close()

    return items


def _apply_auth_cookies(context, config: dict) -> None:
    auth_token = config["auth_token"]
    ct0 = config["ct0"]
    cookies = []
    for domain in (".x.com", ".twitter.com"):
        cookies.extend(
            [
                {
                    "name": "auth_token",
                    "value": auth_token,
                    "domain": domain,
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                },
                {
                    "name": "ct0",
                    "value": ct0,
                    "domain": domain,
                    "path": "/",
                    "secure": True,
                },
            ]
        )
    context.add_cookies(cookies)


def _prime_session(context) -> None:
    page = context.new_page()
    try:
        page.goto(_SESSION_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(_SESSION_PRIME_WAIT_MS)
        # Refresh once to let X rotate/refresh transient session state.
        page.reload(wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(_SESSION_PRIME_WAIT_MS)
    finally:
        page.close()


def _scrape_home_feed(
    context,
    count: int,
    max_scrolls: int,
    scroll_pause_ms: int,
    allowed_authors: set[str] | None = None,
) -> list[Item]:
    page = context.new_page()
    items: list[Item] = []
    seen_ids: set[str] = set()
    no_growth_rounds = 0

    try:
        page.goto(_SESSION_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(scroll_pause_ms)

        for _ in range(max_scrolls):
            fresh_in_round = 0
            for item in _extract_tweets_from_page(
                page, allowed_authors=allowed_authors
            ):
                if item.id in seen_ids:
                    continue
                seen_ids.add(item.id)
                items.append(item)
                fresh_in_round += 1
                if len(items) >= count:
                    return items[:count]

            if fresh_in_round == 0:
                no_growth_rounds += 1
                if no_growth_rounds >= 2:
                    break
            else:
                no_growth_rounds = 0

            _scroll_timeline(page, scroll_pause_ms)
    finally:
        page.close()

    return items[:count]


def _extract_tweets_from_page(
    page, allowed_authors: set[str] | None = None
) -> list[Item]:
    rows = page.eval_on_selector_all(
        "article[data-testid='tweet']",
        """(articles) => articles.map((article) => {
            const link = article.querySelector("a[href*='/status/']");
            if (!link) return null;
            const href = link.getAttribute("href") || "";
            const textEl = article.querySelector("[data-testid='tweetText']");
            const text = textEl ? textEl.innerText.trim() : "";
            if (!text) return null;
            const timeEl = article.querySelector("time");
            const timestamp = timeEl ? timeEl.getAttribute("datetime") : null;
            return { href, text, timestamp };
        }).filter(Boolean)""",
    )

    items: list[Item] = []
    for row in rows:
        author, tweet_id = _extract_tweet_parts((row or {}).get("href", ""))
        if not author or not tweet_id:
            continue

        text = ((row or {}).get("text") or "").strip()
        if not text:
            continue

        if allowed_authors and author.lower() not in allowed_authors:
            continue

        timestamp = (row or {}).get("timestamp") or datetime.now(
            timezone.utc
        ).isoformat()
        items.append(
            Item(
                id=tweet_id,
                source="twitter",
                content=text,
                timestamp=timestamp,
            )
        )
    return items


def _scroll_timeline(page, pause_ms: int) -> None:
    page.evaluate("window.scrollBy(0, Math.max(window.innerHeight * 1.8, 1400));")
    page.wait_for_timeout(pause_ms)


def _extract_tweet_parts(href: str) -> tuple[str | None, str | None]:
    m = _STATUS_PATH_RE.search(href or "")
    if not m:
        return None, None
    return m.group(1), m.group(2)
