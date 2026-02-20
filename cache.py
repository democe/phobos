import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sources.base import Item

logger = logging.getLogger(__name__)

CACHE_TTL_HOURS = 24


def _load(cache_file: Path) -> dict:
    if not cache_file.exists():
        return {}
    try:
        return json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("Cache file %s is corrupt or unreadable, starting fresh", cache_file)
        return {}


def _prune(data: dict) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)
    result = {}
    for id, ts in data.items():
        try:
            if datetime.fromisoformat(ts) > cutoff:
                result[id] = ts
        except (ValueError, TypeError):
            pass  # drop malformed entries
    return result


def filter_new(items: list[Item], cache_file: Path) -> list[Item]:
    seen = _load(cache_file)
    return [item for item in items if item.id not in seen]


def mark_seen(items: list[Item], cache_file: Path) -> None:
    data = _prune(_load(cache_file))
    now = datetime.now(timezone.utc).isoformat()
    for item in items:
        data[item.id] = now
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, indent=2))
