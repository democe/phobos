from dataclasses import dataclass

@dataclass
class Item:
    id: str
    source: str
    content: str
    timestamp: str
