"""Edge-case tests for log.py: limits of public APIs, missing fields, and boundary values."""

import log


def test_log_entry_from_dict_with_missing_keys_returns_defaults():
    """Missing season, era, kind, or text should fall back to 0, '', 'beat', or None."""
    entry = log.LogEntry.from_dict({})
    assert entry is None

    entry = log.LogEntry.from_dict({"text": "A line."})
    assert (entry.season, entry.era, entry.kind) == (0, "", "beat")


def test_log_entry_from_dict_with_wrong_types_rejects_or_clamps():
    """Season must be int, era and kind must be str; text must be str."""
    # season as string -> clamped to 0
    entry = log.LogEntry.from_dict({"season": "4", "era": "tribal", "kind": "beat", "text": "Fine."})
    assert entry.season == 0

    # era as int -> clamped to ''
    entry = log.LogEntry.from_dict({"season": 4, "era": 123, "kind": "beat", "text": "Fine."})
    assert entry.era == ""

    # kind as list -> clamped to 'beat'
    entry = log.LogEntry.from_dict({"season": 4, "era": "tribal", "kind": ["beat"], "text": "Fine."})
    assert entry.kind == "beat"

    # text as non-str -> returns None
    assert log.LogEntry.from_dict({"season": 4, "era": "tribal", "kind": "beat", "text": 123}) is None


def test_chronicle_check_population_with_zero_and_negative_input():
    """Population at or below zero should not trigger any milestones."""
    chronicle = log.Chronicle()

    class FakeState:
        pass

    s_zero = FakeState()
    s_zero.population = 0
    s_zero.season = 1
    s_zero.era = "tribal"
    chronicle.check_population(s_zero)
    assert chronicle._population_milestones_hit == set()

    s_neg = FakeState()
    s_neg.population = -5
    s_neg.season = 2
    s_neg.era = "tribal"
    chronicle.check_population(s_neg)
    assert chronicle._population_milestones_hit == set()


def test_chronicle_check_population_at_and_beyond_max_milestone():
    """Crossing the largest milestone (250) should log it; exceeding it does nothing extra."""
    chronicle = log.Chronicle()

    class FakeState:
        pass

    s1 = FakeState()
    s1.population = 249
    s1.season = 10
    s1.era = "tribal"
    chronicle.check_population(s1)
    assert 250 not in chronicle._population_milestones_hit

    s2 = FakeState()
    s2.population = 250
    s2.season = 11
    s2.era = "tribal"
    chronicle.check_population(s2)
    assert 250 in chronicle._population_milestones_hit
    assert len(chronicle._population_milestones_hit) == 8  # All milestones up to 250 are now hit

    s3 = FakeState()
    s3.population = 300
    s3.season = 12
    s3.era = "tribal"
    chronicle.check_population(s3)
    assert len(chronicle._population_milestones_hit) == 8  # No new milestones added


def test_chronicle_restore_with_empty_or_malformed_data():
    """Restoring empty or deeply malformed data should leave the chronicle in a safe default state."""
    chronicle = log.Chronicle()

    # Empty dict
    chronicle.restore({})
    assert chronicle.entries == []
    assert chronicle._population_milestones_hit == set()
    assert chronicle._last_score_label is None
    assert chronicle._researched_seen == set()

    # Entries with bad types
    chronicle.restore({"entries": [{"text": 123}, {"season": "x", "era": [], "kind": {}, "text": "ok"}]})
    assert len(chronicle.entries) == 1
    assert chronicle.entries[0].text == "ok"


def test_chronicle_snapshot_and_restore_round_trip():
    """Snapshotting a populated chronicle and restoring it should preserve entries and milestones."""
    chronicle = log.Chronicle()

    class FakeState:
        pass

    for pop in [10, 15]:
        s = FakeState()
        s.population = pop
        s.season = 5
        s.era = "tribal"
        chronicle.check_population(s)

    snap = chronicle.snapshot()
    assert "entries" in snap
    assert "population_milestones_hit" in snap

    new_chronicle = log.Chronicle()
    new_chronicle.restore(snap)
    assert new_chronicle._population_milestones_hit == chronicle._population_milestones_hit
    assert len(new_chronicle.entries) == len(chronicle.entries)
