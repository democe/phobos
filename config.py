from pathlib import Path
import yaml

REQUIRED_KEYS = ["ollama", "telegram", "sources", "compose"]


def load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open() as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config file is empty or invalid: {path}")
    for key in REQUIRED_KEYS:
        if key not in cfg:
            raise KeyError(f"Missing required config key: '{key}'")
    return cfg
