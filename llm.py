import requests
from sources.base import Item


def summarize(items: list[Item], prompt: str, config: dict) -> str:
    content = "\n\n".join(item.content for item in items)
    full_prompt = f"{prompt}\n\n{content}"

    response = requests.post(
        f"{config['base_url']}/api/generate",
        json={"model": config["model"], "prompt": full_prompt, "stream": False},
        timeout=config.get("timeout", 120),
    )
    response.raise_for_status()
    return response.json()["response"]
