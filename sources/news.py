import hashlib
import logging
from datetime import datetime, timezone

import trafilatura

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
        html = page.content()
        extracted = trafilatura.extract(html)
        if extracted:
            content = extracted[:CONTENT_CAP]
        else:
            content = page.inner_text("body")[:CONTENT_CAP]
    finally:
        page.close()
    return Item(
        id=hashlib.md5(url.encode()).hexdigest(),
        source="news",
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
