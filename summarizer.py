import requests

SUMMARIZE_PROMPT = (
    "You are a digest summarizer. Concisely summarize the following content, "
    "preserving all key facts and topics. Keep your response under 4096 characters."
)


def summarize(text: str, config: dict) -> str:
    """Run text through a second Ollama pass to compress it."""
    full_prompt = f"{SUMMARIZE_PROMPT}\n\n{text}"
    response = requests.post(
        f"{config['base_url']}/api/generate",
        json={"model": config["model"], "prompt": full_prompt, "stream": False},
        timeout=config.get("timeout", 120),
    )
    response.raise_for_status()
    return response.json()["response"]
