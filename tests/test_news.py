# tests/test_news.py
from sources import news
from unittest.mock import MagicMock

NEWS_CONFIG = {
    "urls": ["https://example.com/news"],
    "prompt": "summarize",
}

def test_fetch_returns_one_item_per_url(mocker):
    mock_page = MagicMock()
    mock_page.inner_text.return_value = "Big story today. Another headline."
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mocker.patch("sources.news.trafilatura.extract", return_value=None)

    items = news.fetch(NEWS_CONFIG, browser=mock_browser)
    assert len(items) == 1
    assert "Big story today" in items[0].content

def test_fetch_item_id_is_url_hash(mocker):
    import hashlib
    mock_page = MagicMock()
    mock_page.inner_text.return_value = "content"
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mocker.patch("sources.news.trafilatura.extract", return_value=None)

    items = news.fetch(NEWS_CONFIG, browser=mock_browser)
    expected_id = hashlib.md5("https://example.com/news".encode()).hexdigest()
    assert items[0].id == expected_id

def test_fetch_skips_failed_url(mocker):
    mock_page = MagicMock()
    mock_page.goto.side_effect = Exception("timeout")
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mocker.patch("sources.news.trafilatura.extract", return_value=None)

    items = news.fetch(NEWS_CONFIG, browser=mock_browser)
    assert items == []

def test_fetch_caps_content_at_8000_chars(mocker):
    mock_page = MagicMock()
    mock_page.inner_text.return_value = "x" * 10000
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mocker.patch("sources.news.trafilatura.extract", return_value=None)

    items = news.fetch(NEWS_CONFIG, browser=mock_browser)
    assert len(items[0].content) == 8000

def test_scrape_uses_trafilatura_when_available(mocker):
    mock_page = MagicMock()
    mock_page.content.return_value = "<html><body><article>Clean article text</article></body></html>"
    mock_page.inner_text.return_value = "Nav junk | Clean article text | Footer ads"
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mocker.patch("sources.news.trafilatura.extract", return_value="Clean article text")

    items = news.fetch(NEWS_CONFIG, browser=mock_browser)
    assert items[0].content == "Clean article text"

def test_scrape_falls_back_to_inner_text_when_trafilatura_returns_none(mocker):
    mock_page = MagicMock()
    mock_page.content.return_value = "<html><body>sparse</body></html>"
    mock_page.inner_text.return_value = "fallback text"
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mocker.patch("sources.news.trafilatura.extract", return_value=None)

    items = news.fetch(NEWS_CONFIG, browser=mock_browser)
    assert items[0].content == "fallback text"
