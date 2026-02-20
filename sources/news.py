import hashlib
import logging
from datetime import datetime, timezone
from sources.base import Item

logger = logging.getLogger(__name__)

CONTENT_CAP = 8000


def fetch(config: dict, browser) -> list[Item]:
    items = []
    context = browser.new_context()
    try:
        for url in config["urls"]:
            try:
                items.append(_scrape(url, context))
            except Exception as e:
                logger.warning("Failed to scrape %s: %s", url, e)
    finally:
        context.close()
    return items


def _scrape(url: str, context) -> Item:
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        text = page.inner_text("body")
    finally:
        page.close()
    return Item(
        id=hashlib.md5(url.encode()).hexdigest(),
        source="news",
        content=text[:CONTENT_CAP],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
