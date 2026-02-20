def compose(
    summaries: dict[str, str],
    order: list[str] | None = None,
    messages: list[list[str]] | None = None,
) -> list[str]:
    """Return one composed string per message group.

    If `messages` is provided, each inner list is one Telegram message.
    If only `order` is provided (legacy), returns a single-element list.
    Groups that produce no content (all sources missing from summaries) are omitted.
    """
    if messages is not None:
        groups = messages
    else:
        groups = [order or []]

    result = []
    for group in groups:
        sections = []
        for source in group:
            if source not in summaries:
                continue
            header = f"## {source.capitalize()}"
            sections.append(f"{header}\n\n{summaries[source]}")
        if sections:
            result.append("\n\n---\n\n".join(sections))
    return result
