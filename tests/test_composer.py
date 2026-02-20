from composer import compose


def test_compose_flat_order_returns_single_element_list():
    summaries = {"weather": "Sunny.", "news": "All good."}
    result = compose(summaries, order=["weather", "news"], messages=None)
    assert isinstance(result, list)
    assert len(result) == 1
    assert "## Weather" in result[0]
    assert "## News" in result[0]


def test_compose_messages_groups_returns_multiple_elements():
    summaries = {"weather": "Sunny.", "twitter": "Tweets.", "email": "Mail."}
    result = compose(
        summaries,
        order=None,
        messages=[["weather"], ["twitter"], ["email"]],
    )
    assert len(result) == 3
    assert "## Weather" in result[0]
    assert "## Twitter" in result[1]
    assert "## Email" in result[2]


def test_compose_skips_sources_not_in_summaries():
    summaries = {"weather": "Sunny."}
    result = compose(summaries, order=None, messages=[["weather", "twitter"]])
    assert len(result) == 1
    assert "## Weather" in result[0]
    assert "twitter" not in result[0].lower()


def test_compose_omits_empty_groups():
    """A group whose sources all have no summaries should not produce an element."""
    summaries = {"weather": "Sunny."}
    result = compose(
        summaries,
        order=None,
        messages=[["twitter"], ["weather"]],
    )
    assert len(result) == 1
    assert "## Weather" in result[0]


def test_compose_flat_order_missing_source_skipped():
    summaries = {"weather": "Sunny."}
    result = compose(summaries, order=["weather", "news"], messages=None)
    assert len(result) == 1
    assert "news" not in result[0].lower()
