# tests/test_email.py
from sources import email as email_source
from unittest.mock import MagicMock, patch

EMAIL_CONFIG = {
    "host": "imap.example.com",
    "port": 993,
    "username": "user@example.com",
    "password": "pass",
    "mailbox": "INBOX",
    "prompt": "summarize",
}

def test_fetch_returns_items(mocker):
    mock_imap = MagicMock()
    mock_imap.search.return_value = ("OK", [b"1 2"])
    mock_imap.fetch.side_effect = [
        ("OK", [(b"1", b"From: a@b.com\r\nSubject: Hello\r\nMessage-ID: <id1@x>\r\n\r\nBody one")]),
        ("OK", [(b"2", b"From: c@d.com\r\nSubject: World\r\nMessage-ID: <id2@x>\r\n\r\nBody two")]),
    ]
    mocker.patch("sources.email.imaplib.IMAP4_SSL", return_value=mock_imap)
    items = email_source.fetch(EMAIL_CONFIG, browser=None)
    assert len(items) == 2
    assert items[0].id == "<id1@x>"
    assert "Hello" in items[0].content

def test_fetch_returns_empty_on_no_messages(mocker):
    mock_imap = MagicMock()
    mock_imap.search.return_value = ("OK", [b""])
    mocker.patch("sources.email.imaplib.IMAP4_SSL", return_value=mock_imap)
    items = email_source.fetch(EMAIL_CONFIG, browser=None)
    assert items == []
