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

    items = news.fetch(NEWS_CONFIG, browser=mock_browser)
    assert items == []

def test_fetch_caps_content_at_8000_chars(mocker):
    mock_page = MagicMock()
    mock_page.inner_text.return_value = "x" * 10000
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    items = news.fetch(NEWS_CONFIG, browser=mock_browser)
    assert len(items[0].content) == 8000
