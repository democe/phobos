# tests/test_llm.py
import pytest
import llm
from sources.base import Item

def make_item(content: str) -> Item:
    return Item(id="1", source="test", content=content, timestamp="2026-01-01T00:00:00")

def test_summarize_returns_string(mocker):
    mock_post = mocker.patch("llm.requests.post")
    mock_post.return_value.json.return_value = {"response": "A summary."}
    mock_post.return_value.raise_for_status = lambda: None

    result = llm.summarize(
        items=[make_item("some content")],
        prompt="Summarize this.",
        config={"base_url": "http://localhost:11434", "model": "llama3.2"},
    )
    assert result == "A summary."

def test_summarize_raises_on_connection_error(mocker):
    import requests
    mocker.patch("llm.requests.post", side_effect=requests.ConnectionError)
    with pytest.raises(requests.ConnectionError):
        llm.summarize(
            items=[make_item("x")],
            prompt="Summarize.",
            config={"base_url": "http://localhost:11434", "model": "llama3.2"},
        )


def test_summarize_uses_configured_timeout(mocker):
    mock_post = mocker.patch("llm.requests.post")
    mock_post.return_value.json.return_value = {"response": "ok"}
    mock_post.return_value.raise_for_status = lambda: None

    llm.summarize(
        items=[make_item("x")],
        prompt="p",
        config={"base_url": "http://localhost:11434", "model": "llama3.2", "timeout": 60},
    )

    assert mock_post.call_args.kwargs["timeout"] == 60


def test_summarize_defaults_timeout_to_120(mocker):
    mock_post = mocker.patch("llm.requests.post")
    mock_post.return_value.json.return_value = {"response": "ok"}
    mock_post.return_value.raise_for_status = lambda: None

    llm.summarize(
        items=[make_item("x")],
        prompt="p",
        config={"base_url": "http://localhost:11434", "model": "llama3.2"},
    )

    assert mock_post.call_args.kwargs["timeout"] == 120
