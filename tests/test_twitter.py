from datetime import datetime, timezone

from sources import twitter

TWITTER_CONFIG = {
    "auth_token": "a" * 40,
    "ct0": "b" * 160,
    "usernames": ["@user1"],
    "count": 20,
    "prompt": "summarize",
}


class FakePage:
    def __init__(self, rows_per_eval=None):
        self.rows_per_eval = rows_per_eval or []
        self.eval_calls = 0
        self.goto_urls = []
        self.closed = False
        self.reloaded = 0
        self.scrolls = 0
        self.waits = []

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_urls.append(url)

    def wait_for_timeout(self, ms):
        self.waits.append(ms)

    def reload(self, wait_until=None, timeout=None):
        self.reloaded += 1

    def close(self):
        self.closed = True

    def eval_on_selector_all(self, selector, script):
        idx = self.eval_calls
        self.eval_calls += 1
        if idx < len(self.rows_per_eval):
            return self.rows_per_eval[idx]
        return []

    def evaluate(self, js):
        self.scrolls += 1


class FakeContext:
    def __init__(self, pages):
        self.pages = list(pages)
        self.cookies = None
        self.closed = False

    def add_cookies(self, cookies):
        self.cookies = cookies

    def new_page(self):
        return self.pages.pop(0)

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, context):
        self.context = context

    def new_context(self, **kwargs):
        return self.context


def _tweet_row(tweet_id: str, text: str, author: str = "user1", timestamp: str | None = None) -> dict:
    row = {
        "href": f"/{author}/status/{tweet_id}",
        "text": text,
    }
    if timestamp is not None:
        row["timestamp"] = timestamp
    return row


def test_extract_tweet_parts():
    assert twitter._extract_tweet_parts("/abc/status/1234567890") == ("abc", "1234567890")
    assert twitter._extract_tweet_parts("/abc/likes") == (None, None)


def test_extract_tweets_from_page_uses_timestamp_or_now():
    now = datetime.now(timezone.utc)
    page = FakePage(
        rows_per_eval=[
            [
                _tweet_row("1001", "Hello", timestamp="2026-02-19T10:00:00.000Z"),
                _tweet_row("1002", "No time"),
            ]
        ]
    )
    items = twitter._extract_tweets_from_page(page)
    assert len(items) == 2
    assert items[0].id == "1001"
    assert items[0].content == "Hello"
    assert items[0].timestamp == "2026-02-19T10:00:00.000Z"
    assert datetime.fromisoformat(items[1].timestamp.replace("Z", "+00:00")) >= now


def test_extract_tweets_from_page_filters_by_author():
    page = FakePage(
        rows_per_eval=[
            [
                _tweet_row("2001", "From user1", author="user1"),
                _tweet_row("2002", "From other", author="other"),
            ]
        ]
    )
    items = twitter._extract_tweets_from_page(page, allowed_authors={"user1"})
    assert len(items) == 1
    assert items[0].id == "2001"


def test_scrape_home_feed_dedupes_and_stops_at_count():
    page = FakePage(
        rows_per_eval=[
            [_tweet_row("3001", "A"), _tweet_row("3002", "B")],
            [_tweet_row("3002", "B"), _tweet_row("3003", "C")],
            [_tweet_row("3003", "C")],
        ]
    )
    context = FakeContext([page])
    items = twitter._scrape_home_feed(
        context=context,
        count=3,
        max_scrolls=6,
        scroll_pause_ms=1,
    )
    assert [x.id for x in items] == ["3001", "3002", "3003"]
    assert page.goto_urls[0] == "https://x.com/home"
    assert page.closed is True


def test_scrape_home_feed_exits_early_on_no_growth():
    # Same rows every eval call — no new tweets after the first round.
    rows = [_tweet_row("4001", "Same")]
    page = FakePage(rows_per_eval=[rows, rows, rows, rows, rows])
    context = FakeContext([page])
    twitter._scrape_home_feed(
        context=context,
        count=20,
        max_scrolls=10,
        scroll_pause_ms=1,
    )
    # Should stop after 2 no-growth rounds, not exhaust max_scrolls.
    assert page.scrolls < 10


def test_fetch_applies_cookies_primes_session_and_uses_feed_mode(mocker):
    prime_page = FakePage()
    context = FakeContext([prime_page])
    browser = FakeBrowser(context)

    scrape = mocker.patch(
        "sources.twitter._scrape_home_feed",
        return_value=[
            twitter.Item(
                id="5001",
                source="twitter",
                content="Tweet",
                timestamp="2026-02-19T10:00:00.000Z",
            )
        ],
    )

    items = twitter.fetch(TWITTER_CONFIG, browser=browser)

    assert len(items) == 1
    assert items[0].id == "5001"
    assert context.closed is True
    assert prime_page.goto_urls[0] == "https://x.com/home"
    assert prime_page.reloaded == 1
    assert scrape.call_args.kwargs["allowed_authors"] is None
    assert any(c["name"] == "auth_token" and c["domain"] == ".x.com" for c in context.cookies)
    assert any(c["name"] == "ct0" and c["domain"] == ".x.com" for c in context.cookies)


def test_fetch_builds_allowed_authors_when_filter_enabled(mocker):
    mocker.patch("sources.twitter._scrape_home_feed", return_value=[])

    cfg = {**TWITTER_CONFIG, "filter_usernames": True, "usernames": ["@Alice", "@bob"]}
    prime_page = FakePage()
    context = FakeContext([prime_page])
    browser = FakeBrowser(context)

    twitter.fetch(cfg, browser=browser)

    call_kwargs = twitter._scrape_home_feed.call_args.kwargs
    assert call_kwargs["allowed_authors"] == {"alice", "bob"}
