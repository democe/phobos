from unittest.mock import patch, MagicMock
from summarizer import summarize

OLLAMA_CFG = {"base_url": "http://localhost:11434", "model": "llama3.2"}


def test_summarize_posts_to_ollama_and_returns_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "Short summary."}
    mock_resp.raise_for_status = MagicMock()

    with patch("summarizer.requests.post", return_value=mock_resp) as mock_post:
        result = summarize("Long text here.", OLLAMA_CFG)

    assert result == "Short summary."
    mock_post.assert_called_once_with(
        "http://localhost:11434/api/generate",
        json=mock_post.call_args.kwargs["json"],
        timeout=120,  # default when not configured
    )
    call_json = mock_post.call_args.kwargs["json"]
    assert call_json["model"] == "llama3.2"
    assert "Long text here." in call_json["prompt"]


def test_summarize_includes_length_instruction_in_prompt():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "OK"}
    mock_resp.raise_for_status = MagicMock()

    with patch("summarizer.requests.post", return_value=mock_resp) as mock_post:
        summarize("some text", OLLAMA_CFG)

    prompt = mock_post.call_args.kwargs["json"]["prompt"]
    assert "4096" in prompt


def test_summarize_uses_configured_timeout():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "ok"}
    mock_resp.raise_for_status = MagicMock()

    with patch("summarizer.requests.post", return_value=mock_resp) as mock_post:
        summarize("text", {**OLLAMA_CFG, "timeout": 60})

    assert mock_post.call_args.kwargs["timeout"] == 60


def test_summarize_raises_on_ollama_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("Ollama error")

    with patch("summarizer.requests.post", return_value=mock_resp):
        try:
            summarize("text", OLLAMA_CFG)
            assert False, "Should have raised"
        except Exception as e:
            assert "Ollama error" in str(e)
