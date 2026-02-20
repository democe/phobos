# tests/test_cache.py
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sources.base import Item
import cache

def make_item(id: str) -> Item:
    return Item(id=id, source="test", content="x", timestamp=datetime.now(timezone.utc).isoformat())

def test_filter_new_all_new(tmp_path):
    cache_file = tmp_path / "test.json"
    items = [make_item("a"), make_item("b")]
    result = cache.filter_new(items, cache_file)
    assert [i.id for i in result] == ["a", "b"]

def test_filter_new_removes_seen(tmp_path):
    cache_file = tmp_path / "test.json"
    cache_file.write_text(json.dumps({"a": datetime.now(timezone.utc).isoformat()}))
    items = [make_item("a"), make_item("b")]
    result = cache.filter_new(items, cache_file)
    assert [i.id for i in result] == ["b"]

def test_mark_seen_writes_file(tmp_path):
    cache_file = tmp_path / "test.json"
    items = [make_item("a"), make_item("b")]
    cache.mark_seen(items, cache_file)
    data = json.loads(cache_file.read_text())
    assert "a" in data
    assert "b" in data

def test_mark_seen_prunes_old_entries(tmp_path):
    cache_file = tmp_path / "test.json"
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    cache_file.write_text(json.dumps({"old": old_ts}))
    cache.mark_seen([make_item("new")], cache_file)
    data = json.loads(cache_file.read_text())
    assert "old" not in data
    assert "new" in data

def test_filter_new_treats_corrupt_cache_as_empty(tmp_path):
    cache_file = tmp_path / "test.json"
    cache_file.write_text("not json")
    items = [make_item("a")]
    result = cache.filter_new(items, cache_file)
    assert [i.id for i in result] == ["a"]
