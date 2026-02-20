import requests
from datetime import datetime, timezone, timedelta
from icalendar import Calendar
from sources.base import Item


def fetch(config: dict, browser) -> list[Item]:
    resp = requests.get(config["ics_url"])
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.content)
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=config["lookahead_days"])
    events = []
    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue
        dtstart = comp.get("dtstart")
        if dtstart is None:
            continue
        begin = dtstart.dt
        if not hasattr(begin, "hour"):
            # date-only event: convert to datetime at midnight UTC
            begin = datetime(begin.year, begin.month, begin.day, tzinfo=timezone.utc)
        if begin.tzinfo is None:
            begin = begin.replace(tzinfo=timezone.utc)
        if now <= begin <= cutoff:
            name = str(comp.get("summary", ""))
            uid = str(comp.get("uid", ""))
            description = comp.get("description")
            content = f"{name}\n{begin.strftime('%Y-%m-%d %H:%M UTC')}"
            if description:
                content += f"\n{str(description)}"
            events.append((begin, Item(
                id=uid,
                source="calendar",
                content=content,
                timestamp=now.isoformat(),
            )))
    events.sort(key=lambda t: t[0])
    return [item for _, item in events]
