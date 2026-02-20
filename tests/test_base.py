# tests/test_base.py
from sources.base import Item

def test_item_fields():
    item = Item(id="123", source="twitter", content="hello", timestamp="2026-01-01T00:00:00")
    assert item.id == "123"
    assert item.source == "twitter"
    assert item.content == "hello"
    assert item.timestamp == "2026-01-01T00:00:00"
