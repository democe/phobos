import requests
from sources.base import Item


def summarize(items: list[Item], prompt: str, config: dict, source_cfg: dict | None = None) -> str:
    content = "\n\n".join(item.content for item in items)
    full_prompt = f"{prompt}\n\n{content}"

    payload = {"model": config["model"], "prompt": full_prompt, "stream": False}
    options = {}
    if "num_ctx" in config:
        options["num_ctx"] = config["num_ctx"]
    if source_cfg and "temperature" in source_cfg:
        options["temperature"] = source_cfg["temperature"]
    if options:
        payload["options"] = options

    response = requests.post(
        f"{config['base_url']}/api/generate",
        json=payload,
        timeout=config.get("timeout", 120),
    )
    response.raise_for_status()
    return response.json()["response"]
