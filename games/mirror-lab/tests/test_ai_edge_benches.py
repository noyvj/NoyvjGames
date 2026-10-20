"""Edge-case and boundary tests for benches.py module-level data and functions."""

import benches


def test_chapter_of_handles_first_and_last_bench():
    """chapter_of should return the correct chapter dict for the smallest and largest bench indices."""
    first = benches.ALL_BENCHES[0]
    last = benches.ALL_BENCHES[-1]

    assert benches.chapter_of(first)["number"] == 1
    assert benches.chapter_of(last)["number"] == 5


def test_open_at_constant_is_five():
    """OPEN_AT defines how many cleared benches are needed to open the next chapter."""
    assert benches.OPEN_AT == 5


def test_chapters_list_has_five_entries_with_required_keys():
    """CHAPTERS should contain exactly five chapters, each with number, name, blurb, and benches."""
    assert len(benches.CHAPTERS) == 5
    for ch in benches.CHAPTERS:
        assert all(k in ch for k in ("number", "name", "blurb", "benches"))


def test_all_benches_contains_forty_items():
    """ALL_BENCHES should contain exactly 40 benches across five chapters."""
    assert len(benches.ALL_BENCHES) == 40


def test_by_id_and_order_are_consistent_with_all_benches():
    """BY_ID keys and ORDER list must match ALL_BENCHES IDs exactly."""
    bench_ids = {b.id for b in benches.ALL_BENCHES}
    assert set(benches.BY_ID.keys()) == bench_ids
    assert set(benches.ORDER) == bench_ids
