import logging
import re

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_UPDATES_API = "https://api.telegram.org/bot{token}/getUpdates"
MAX_MESSAGE_LEN = 4096


def _strip_markdown(text: str) -> str:
    # Remove horizontal rules
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    # Remove ATX headings (# Foo -> Foo)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers (* ** _ __)
    text = re.sub(r"(\*{1,2}|_{1,2})(.*?)\1", r"\2", text)
    # Remove any remaining unpaired asterisks or underscores
    text = re.sub(r"\*{1,2}|_{1,2}", "", text)
    # Remove inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Collapse excess blank lines left by removed elements
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def send(text: str, config: dict) -> None:
    token = config["bot_token"]
    chat_id = config.get("chat_id") or _get_chat_id(token)
    logger.info("Sending to chat_id %s", chat_id)
    url = TELEGRAM_API.format(token=token)
    for chunk in _split(_strip_markdown(text)):
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
            },
        )
        if not response.ok:
            logger.error(
                "Telegram API error %s: %s", response.status_code, response.text
            )
        response.raise_for_status()


def _get_chat_id(token: str) -> int:
    response = requests.get(TELEGRAM_UPDATES_API.format(token=token))
    response.raise_for_status()
    updates = response.json().get("result", [])
    if not updates:
        raise RuntimeError(
            "No Telegram updates found. Send a message to your bot first, then run again."
        )
    return updates[-1]["message"]["chat"]["id"]


def _split(text: str) -> list[str]:
    if len(text) <= MAX_MESSAGE_LEN:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:MAX_MESSAGE_LEN])
        text = text[MAX_MESSAGE_LEN:]
    return chunks
