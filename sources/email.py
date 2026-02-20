import imaplib
import email as stdlib_email
from datetime import datetime, timezone
from sources.base import Item


def fetch(config: dict, browser) -> list[Item]:
    imap = imaplib.IMAP4_SSL(config["host"], config["port"])
    try:
        imap.login(config["username"], config["password"])
        imap.select(config["mailbox"])
        status, data = imap.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            return []
        ids = data[0].split()
        return [_fetch_message(imap, msg_id) for msg_id in ids]
    finally:
        imap.logout()


def _fetch_message(imap, msg_id: bytes) -> Item:
    _, data = imap.fetch(msg_id, "(RFC822)")
    raw = data[0][1]
    msg = stdlib_email.message_from_bytes(raw)
    message_id = msg.get("Message-ID", msg_id.decode())
    subject = msg.get("Subject", "(no subject)")
    sender = msg.get("From", "unknown")
    body = _extract_body(msg)
    content = f"From: {sender}\nSubject: {subject}\n\n{body}"
    return Item(
        id=message_id,
        source="email",
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="replace")
    return msg.get_payload(decode=True).decode(errors="replace") if msg.get_payload() else ""
