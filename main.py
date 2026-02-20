import logging
import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright
from requests.exceptions import Timeout

import cache
import composer
import config
import llm
import sources.calendar as calendar_source
import sources.email as email_source
import sources.news
import sources.twitter
import sources.weather
import summarizer
import telegram

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = Path("cache")

SOURCE_MODULES = {
    "weather": sources.weather,
    "email": email_source,
    "calendar": calendar_source,
    "news": sources.news,
    "twitter": sources.twitter,
}


def run(config_path: str = "config.yaml") -> None:
    cfg = config.load(Path(config_path))

    try:
        requests.get(cfg["ollama"]["base_url"], timeout=5).raise_for_status()
    except Exception as e:
        raise RuntimeError(
            f"Ollama is not reachable at {cfg['ollama']['base_url']}: {e}"
        )

    summaries = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for source_name, source_cfg in cfg["sources"].items():
            if not source_cfg.get("enabled", False):
                continue
            if source_name not in SOURCE_MODULES:
                logger.warning("Unknown source '%s', skipping", source_name)
                continue
            try:
                items = SOURCE_MODULES[source_name].fetch(source_cfg, browser)
            except Exception as e:
                logger.error("Source '%s' failed: %s", source_name, e)
                continue

            if source_cfg.get("cache", True):
                cache_file = CACHE_DIR / f"{source_name}.json"
                new_items = cache.filter_new(items, cache_file)
                if not new_items:
                    logger.info("No new items from '%s', skipping", source_name)
                    continue
            else:
                new_items = items

            try:
                if source_name == "news":
                    per_item_summaries = []
                    for item in new_items:
                        try:
                            per_item_summaries.append(
                                llm.summarize([item], source_cfg["prompt"], cfg["ollama"])
                            )
                        except Timeout:
                            logger.warning("LLM timed out for news item %s, skipping", item.id)
                        except Exception as e:
                            logger.error("LLM summarize failed for news item %s: %s", item.id, e)
                    if not per_item_summaries:
                        continue
                    summary = "\n\n".join(per_item_summaries)
                else:
                    summary = llm.summarize(new_items, source_cfg["prompt"], cfg["ollama"])
            except Timeout:
                logger.warning("LLM timed out for source '%s', skipping", source_name)
                continue
            except Exception as e:
                logger.error("LLM summarize failed for source '%s': %s", source_name, e)
                continue

            if source_cfg.get("cache", True):
                cache.mark_seen(new_items, cache_file)
            summaries[source_name] = summary

        browser.close()

    if not summaries:
        logger.info("Nothing new across all sources, not sending Telegram message")
        return

    compose_cfg = cfg["compose"]
    use_messages = compose_cfg.get("messages") is not None
    groups = composer.compose(
        summaries,
        order=compose_cfg.get("order"),
        messages=compose_cfg.get("messages"),
    )
    if not groups:
        logger.info(
            "No configured sources produced content, not sending Telegram message"
        )
        return
    if compose_cfg.get("summarize") and not use_messages:
        try:
            groups = [summarizer.summarize(groups[0], cfg["ollama"])]
        except Exception as e:
            logger.error(
                "Final digest summarization failed, sending uncompressed digest: %s", e
            )
    for group in groups:
        telegram.send(group, cfg["telegram"])
    logger.info("Digest sent successfully")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    run(config_path)
