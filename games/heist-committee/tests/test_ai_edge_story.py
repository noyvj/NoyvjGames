import story


def test_minutes_with_empty_meta():
    """Empty meta defaults jobs_done to 0 and returns the first minute."""
    res = story.minutes({})
    assert len(res["entries"]) == 1
    assert res["next_at"] == 1


def test_minutes_with_missing_jobs_done_key():
    """Missing jobs_done key defaults to 0."""
    res = story.minutes({"other": "data"})
    assert res["jobs_done"] == 0
    assert len(res["entries"]) == 1


def test_minutes_with_negative_jobs_done():
    """Negative jobs_done yields no entries and next_at stays at the first unlock."""
    res = story.minutes({"jobs_done": -5})
    assert res["entries"] == []
    assert res["next_at"] == 0


def test_minutes_with_large_jobs_done():
    """Large jobs_done unlocks all minutes and sets next_at to None."""
    res = story.minutes({"jobs_done": 100})
    assert len(res["entries"]) == len(story.MINUTES)
    assert res["next_at"] is None


def test_debrief_with_unknown_class():
    """Unknown class skips the opening line but still returns crew voice."""
    content_mock = type("MockContent", (), {"crew": {"dot": {"short": "Dot", "voice": "I did it."}}})()
    result = {"events": []}
    lines = story.debrief(content_mock, ["dot"], result, "unknown_class", 0)
    assert len(lines) == 1
    assert lines[0]["who"] == "Dot"


def test_debrief_with_many_traits_clamps_to_two():
    """Debrief only shows the first two trait lines regardless of how many fired."""
    content_mock = type("MockContent", (), {"crew": {"dot": {"short": "Dot", "voice": "Done."}}})()
    events = [
        {"type": "trait", "trait": "chatty", "crew": "dot"},
        {"type": "trait", "trait": "nervous", "crew": "dot"},
        {"type": "trait", "trait": "lucky", "crew": "dot"},
    ]
    lines = story.debrief(content_mock, ["dot"], {"events": events}, "clean", 0)
    trait_lines = [line for line in lines if line["text"] in story.TRAIT_LINES.values()]
    assert len(trait_lines) == 2


def test_debrief_with_zero_seed():
    """Zero seed produces deterministic output."""
    content_mock = type("MockContent", (), {"crew": {"dot": {"short": "Dot", "voice": "Hello."}}})()
    result = {"events": []}
    lines1 = story.debrief(content_mock, ["dot"], result, "clean", 0)
    lines2 = story.debrief(content_mock, ["dot"], result, "clean", 0)
    assert lines1 == lines2
