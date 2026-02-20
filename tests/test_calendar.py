# tests/test_calendar.py
from datetime import datetime, timezone, timedelta
from sources import calendar as cal_source

CALENDAR_CONFIG = {
    "ics_url": "https://example.com/calendar.ics",
    "lookahead_days": 7,
    "prompt": "summarize",
}

ICS_CONTENT = b"""BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event-001@example.com
SUMMARY:Team Meeting
DTSTART:20260220T100000Z
DTEND:20260220T110000Z
END:VEVENT
BEGIN:VEVENT
UID:event-002@example.com
SUMMARY:Old Event
DTSTART:20200101T100000Z
DTEND:20200101T110000Z
END:VEVENT
END:VCALENDAR"""

def test_fetch_returns_upcoming_events(mocker):
    mock_get = mocker.patch("sources.calendar.requests.get")
    mock_get.return_value.raise_for_status = lambda: None
    mock_get.return_value.content = ICS_CONTENT
    # Freeze time to 2026-02-19
    mocker.patch("sources.calendar.datetime", wraps=datetime)
    import sources.calendar
    sources.calendar.datetime.now = lambda tz=None: datetime(2026, 2, 19, tzinfo=timezone.utc)
    items = cal_source.fetch(CALENDAR_CONFIG, browser=None)
    assert len(items) == 1
    assert items[0].id == "event-001@example.com"
    assert "Team Meeting" in items[0].content

def test_fetch_item_content_includes_datetime(mocker):
    mock_get = mocker.patch("sources.calendar.requests.get")
    mock_get.return_value.raise_for_status = lambda: None
    mock_get.return_value.content = ICS_CONTENT
    # Freeze time to 2026-02-19
    mocker.patch("sources.calendar.datetime", wraps=datetime)
    import sources.calendar
    sources.calendar.datetime.now = lambda tz=None: datetime(2026, 2, 19, tzinfo=timezone.utc)
    items = cal_source.fetch(CALENDAR_CONFIG, browser=None)
    assert "2026-02-20" in items[0].content
