# tests/test_main.py
from unittest.mock import MagicMock, patch

import pytest

import main
from sources.base import Item


def make_item(source: str) -> Item:
    return Item(id="1", source=source, content="stuff", timestamp="2026-01-01T00:00:00")


CONFIG = {
    "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
    "telegram": {"bot_token": "tok", "chat_id": "123"},
    "sources": {
        "weather": {"enabled": True, "prompt": "summarize weather"},
        "email": {"enabled": False, "prompt": "summarize email"},
    },
    "compose": {"order": ["weather", "email"]},
}


def _mock_ollama_ok(mocker):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    return mocker.patch("main.requests.get", return_value=mock_resp)


def test_run_skips_disabled_sources(mocker):
    mocker.patch("main.config.load", return_value=CONFIG)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mocker.patch("main.cache.filter_new", return_value=[make_item("weather")])
    mocker.patch("main.cache.mark_seen")
    mock_summarize = mocker.patch("main.llm.summarize", return_value="weather summary")
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")
    assert mock_summarize.call_count == 1  # only weather, not email


def test_run_skips_source_with_no_new_items(mocker):
    mocker.patch("main.config.load", return_value=CONFIG)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mocker.patch("main.cache.filter_new", return_value=[])  # all seen
    mock_summarize = mocker.patch("main.llm.summarize", return_value="summary")
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")
    mock_summarize.assert_not_called()


def test_run_source_error_does_not_abort(mocker):
    mocker.patch("main.config.load", return_value=CONFIG)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", side_effect=Exception("network error"))
    mocker.patch("main.cache.filter_new", return_value=[])
    mocker.patch("main.llm.summarize", return_value="summary")
    mock_send = mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")  # should not raise


def test_run_raises_if_ollama_unreachable(mocker):
    mocker.patch("main.config.load", return_value=CONFIG)
    import requests

    mocker.patch("main.requests.get", side_effect=requests.ConnectionError("refused"))
    mocker.patch("main.sync_playwright")

    with pytest.raises(RuntimeError, match="Ollama is not reachable"):
        main.run(config_path="config.yaml")


def test_run_bypasses_cache_when_disabled(mocker):
    cfg = {
        **CONFIG,
        "sources": {
            "weather": {"enabled": True, "cache": False, "prompt": "summarize weather"}
        },
        "compose": {"order": ["weather"]},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mock_filter = mocker.patch("main.cache.filter_new")
    mock_mark = mocker.patch("main.cache.mark_seen")
    mocker.patch("main.llm.summarize", return_value="summary")
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    mock_filter.assert_not_called()
    mock_mark.assert_not_called()


def test_run_does_not_send_telegram_if_no_new_items(mocker):
    mocker.patch("main.config.load", return_value=CONFIG)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mocker.patch("main.cache.filter_new", return_value=[])  # nothing new
    mock_send = mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")
    mock_send.assert_not_called()


def test_run_summarizes_when_flag_set(mocker):
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {"weather": {"enabled": True, "cache": False, "prompt": "p"}},
        "compose": {"order": ["weather"], "summarize": True},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mocker.patch("main.llm.summarize", return_value="weather summary")
    mock_sum = mocker.patch(
        "main.summarizer.summarize", return_value="compressed summary"
    )
    mock_send = mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    mock_sum.assert_called_once()
    first_arg = mock_sum.call_args.args[0]
    assert "weather summary" in first_arg
    mock_send.assert_called_once_with("compressed summary", cfg["telegram"])


def test_run_skips_summarize_when_messages_mode(mocker):
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {"weather": {"enabled": True, "cache": False, "prompt": "p"}},
        "compose": {"messages": [["weather"]], "summarize": True},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mocker.patch("main.llm.summarize", return_value="weather summary")
    mock_sum = mocker.patch("main.summarizer.summarize")
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    mock_sum.assert_not_called()


def test_run_skips_summarize_when_flag_false(mocker):
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {"weather": {"enabled": True, "cache": False, "prompt": "p"}},
        "compose": {"order": ["weather"], "summarize": False},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mocker.patch("main.llm.summarize", return_value="weather summary")
    mock_sum = mocker.patch("main.summarizer.summarize")
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    mock_sum.assert_not_called()


def test_run_llm_source_timeout_does_not_abort(mocker):
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {"weather": {"enabled": True, "cache": False, "prompt": "p"}},
        "compose": {"order": ["weather"]},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    import requests

    mocker.patch("main.llm.summarize", side_effect=requests.Timeout("timed out"))
    mock_send = mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    mock_send.assert_not_called()


def test_run_llm_timeout_logs_warning_not_error(mocker, caplog):
    import logging
    import requests

    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {"weather": {"enabled": True, "cache": False, "prompt": "p"}},
        "compose": {"order": ["weather"]},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mocker.patch("main.llm.summarize", side_effect=requests.Timeout("timed out"))
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    with caplog.at_level(logging.WARNING, logger="__main__"):
        main.run(config_path="config.yaml")

    assert any(r.levelno == logging.WARNING for r in caplog.records)
    assert not any(r.levelno == logging.ERROR for r in caplog.records)


def test_run_news_summarizes_each_item_individually(mocker):
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {
            "news": {"enabled": True, "cache": False, "prompt": "summarize news"},
        },
        "compose": {"order": ["news"]},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    items = [
        Item(id="a", source="news", content="article 1", timestamp="2026-01-01T00:00:00"),
        Item(id="b", source="news", content="article 2", timestamp="2026-01-01T00:00:00"),
    ]
    mocker.patch("main.sources.news.fetch", return_value=items)
    mock_summarize = mocker.patch("main.llm.summarize", side_effect=["summary 1", "summary 2"])
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    assert mock_summarize.call_count == 2
    # Each call should receive exactly one item
    assert mock_summarize.call_args_list[0].args[0] == [items[0]]
    assert mock_summarize.call_args_list[1].args[0] == [items[1]]


def test_run_news_joined_summaries_reach_composer(mocker):
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {
            "news": {"enabled": True, "cache": False, "prompt": "summarize news"},
        },
        "compose": {"order": ["news"]},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    items = [
        Item(id="a", source="news", content="article 1", timestamp="2026-01-01T00:00:00"),
        Item(id="b", source="news", content="article 2", timestamp="2026-01-01T00:00:00"),
    ]
    mocker.patch("main.sources.news.fetch", return_value=items)
    mocker.patch("main.llm.summarize", side_effect=["summary 1", "summary 2"])
    mock_compose = mocker.patch("main.composer.compose", return_value=["composed text"])
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    compose_call_summaries = mock_compose.call_args.args[0]
    assert compose_call_summaries["news"] == "summary 1\n\nsummary 2"


def test_run_falls_back_when_final_summarizer_fails(mocker):
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {"weather": {"enabled": True, "cache": False, "prompt": "p"}},
        "compose": {"order": ["weather"], "summarize": True},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mocker.patch("main.llm.summarize", return_value="weather summary")
    mocker.patch("main.summarizer.summarize", side_effect=Exception("ollama timeout"))
    mock_send = mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    mock_send.assert_called_once()
    assert "weather summary" in mock_send.call_args.args[0]


def test_run_non_browser_sources_in_parallel(mocker):
    """Non-browser sources should all be fetched (fetch called for each enabled one)."""
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {
            "weather": {"enabled": True, "cache": False, "prompt": "p"},
            "calendar": {"enabled": True, "cache": False, "prompt": "p"},
            "email": {"enabled": True, "cache": False, "prompt": "p"},
        },
        "compose": {"order": ["weather", "calendar", "email"]},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mock_weather = mocker.patch("main.sources.weather.fetch", return_value=[make_item("weather")])
    mock_calendar = mocker.patch("main.sources.calendar.fetch", return_value=[make_item("calendar")])
    mock_email = mocker.patch("main.sources.email.fetch", return_value=[make_item("email")])
    mocker.patch("main.llm.summarize", return_value="summary")
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    mock_weather.assert_called_once()
    mock_calendar.assert_called_once()
    mock_email.assert_called_once()


def test_run_browser_sources_not_run_via_thread_pool(mocker):
    """news and twitter must not be called via _run_source (they need Playwright)."""
    cfg = {
        "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
        "telegram": {"bot_token": "tok", "chat_id": "123"},
        "sources": {
            "news": {"enabled": True, "cache": False, "prompt": "p"},
            "weather": {"enabled": True, "cache": False, "prompt": "p"},
        },
        "compose": {"order": ["weather", "news"]},
    }
    mocker.patch("main.config.load", return_value=cfg)
    _mock_ollama_ok(mocker)
    mock_run_source = mocker.patch("main._run_source", return_value=("weather", "w summary"))
    mocker.patch("main.sources.news.fetch", return_value=[make_item("news")])
    mocker.patch("main.llm.summarize", return_value="news summary")
    mocker.patch("main.telegram.send")
    mocker.patch("main.sync_playwright")

    main.run(config_path="config.yaml")

    # _run_source should only be called for weather, not news
    assert mock_run_source.call_count == 1
    assert mock_run_source.call_args.args[0] == "weather"
