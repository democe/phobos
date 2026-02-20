# tests/test_config.py
import pytest
from pathlib import Path
import yaml
import config

VALID_CONFIG = {
    "ollama": {"base_url": "http://localhost:11434", "model": "llama3.2"},
    "telegram": {"bot_token": "tok", "chat_id": "123"},
    "sources": {
        "weather": {"enabled": True, "prompt": "summarize weather"},
    },
    "compose": {"order": ["weather"]},
}

def test_load_valid_config(tmp_path):
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(VALID_CONFIG))
    cfg = config.load(f)
    assert cfg["ollama"]["model"] == "llama3.2"

def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        config.load(Path("/nonexistent/config.yaml"))

def test_load_missing_required_key_raises(tmp_path):
    bad = {"sources": {}}  # missing ollama and telegram
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(bad))
    with pytest.raises(KeyError):
        config.load(f)
