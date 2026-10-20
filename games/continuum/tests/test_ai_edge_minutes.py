"""Edge-case tests for minutes.py."""

import minutes


def test_clean_empty_input_returns_empty_list():
    assert minutes.clean([]) == []


def test_clean_trims_at_max_buffer_size():
    raw = [{"kind": "build", "era": "tribal", "season": 1, "text": f"item {i}"} for i in range(minutes.MAX_ENTRIES * 3)]
    result = minutes.clean(raw)
    assert len(result) == minutes.MAX_ENTRIES


def test_entries_missing_key_returns_empty_list():
    assert minutes.entries({}) == []


def test_record_accepts_smallest_allowed_season():
    ui = {}
    assert minutes.record(ui, "build", "Shelter", "tribal", 1)
    assert minutes.entries(ui)[0]["season"] == 1


def test_record_rejects_zero_and_negative_seasons():
    ui = {}
    assert not minutes.record(ui, "build", "Shelter", "tribal", 0)
    assert not minutes.record(ui, "build", "Shelter", "tribal", -5)
    assert ui == {}


def test_record_clamps_to_max_entries_on_overflow():
    ui = {}
    for i in range(minutes.MAX_ENTRIES + 1):
        minutes.record(ui, "build", f"Building {i}", "tribal", 1)
    assert len(minutes.entries(ui)) == minutes.MAX_ENTRIES
