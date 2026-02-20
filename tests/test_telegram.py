# tests/test_telegram.py
import pytest
import telegram

def test_send_calls_api(mocker):
    mock_post = mocker.patch("telegram.requests.post")
    mock_post.return_value.raise_for_status = lambda: None
    telegram.send("hello", config={"bot_token": "tok", "chat_id": "123"})
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[0][0] == "https://api.telegram.org/bottok/sendMessage"

def test_send_raises_on_failure(mocker):
    import requests
    mock_post = mocker.patch("telegram.requests.post")
    mock_post.return_value.raise_for_status.side_effect = requests.HTTPError("bad")
    with pytest.raises(requests.HTTPError):
        telegram.send("hello", config={"bot_token": "tok", "chat_id": "123"})

def test_send_splits_long_message(mocker):
    mock_post = mocker.patch("telegram.requests.post")
    mock_post.return_value.raise_for_status = lambda: None
    long_text = "x" * 5000
    telegram.send(long_text, config={"bot_token": "tok", "chat_id": "123"})
    assert mock_post.call_count == 2  # 4096 + 904

def test_send_autodiscovers_chat_id(mocker):
    mock_get = mocker.patch("telegram.requests.get")
    mock_get.return_value.raise_for_status = lambda: None
    mock_get.return_value.json.return_value = {
        "result": [{"message": {"chat": {"id": 42}}}]
    }
    mock_post = mocker.patch("telegram.requests.post")
    mock_post.return_value.raise_for_status = lambda: None
    telegram.send("hello", config={"bot_token": "tok"})
    posted_json = mock_post.call_args[1]["json"]
    assert posted_json["chat_id"] == 42

def test_send_raises_if_no_updates_and_no_chat_id(mocker):
    mock_get = mocker.patch("telegram.requests.get")
    mock_get.return_value.raise_for_status = lambda: None
    mock_get.return_value.json.return_value = {"result": []}
    with pytest.raises(RuntimeError, match="Send a message to your bot first"):
        telegram.send("hello", config={"bot_token": "tok"})
