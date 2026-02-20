# Phobos

Phobos is a personal digest script that aggregates Twitter, news, email, weather, and calendar data, summarizes it with a local LLM, and delivers it to Telegram on a schedule.

## Requirements

- [uv](https://docs.astral.sh/uv/) — must be on a PATH accessible to all users (e.g. `/usr/local/bin/uv`), not only to the installing user
- `rsync` — used by the install script to copy project files
- [Ollama](https://ollama.com/) with a model pulled (e.g. `ollama pull llama3.2`)
- A Telegram bot token ([create one via BotFather](https://core.telegram.org/bots#botfather))
