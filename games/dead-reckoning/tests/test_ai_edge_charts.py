"""Edge-case tests for charts.py: limits of IDs, records, and pack resolution."""


import charts
import gen


def test_get_chart_handles_unknown_and_invalid_ids():
    """get_chart returns None for unknown campaign IDs, out-of-range practice IDs, and malformed daily IDs."""
    assert charts.get_chart("nonexistent-chart") is None
    # Practice ID with invalid difficulty (9)
    assert charts.get_chart("practice-9-1") is None
    # Daily ID with invalid date format
    assert charts.get_chart("daily-2025-13-45") is None


def test_par_legs_returns_fresh_copies_or_none():
    """par_legs returns a list of dicts for valid charts, or None; par_legs2 handles two-ship charts."""
    # open-01 is always present (chapter 1)
    legs = charts.par_legs("open-01")
    assert isinstance(legs, list) and len(legs) > 0
    # Modifying the returned list should not affect internal state
    legs.append({"heading": 0, "speed": 0, "hours": 0})
    assert charts.par_legs("open-01") != legs

    assert charts.par_legs("unknown-chart-id") is None
    assert charts.par_legs2("unknown-chart-id") is None


def test_next_chart_id_respects_order_boundaries():
    """next_chart_id returns the following chart in ORDER, None at the end, and None for unknown IDs."""
    assert len(charts.ORDER) > 0
    first = charts.ORDER[0]
    last = charts.ORDER[-1]

    if len(charts.ORDER) > 1:
        assert charts.next_chart_id(first) is not None
    else:
        assert charts.next_chart_id(first) is None

    assert charts.next_chart_id(last) is None
    assert charts.next_chart_id("bogus-id") is None


def test_is_unlocked_respects_records_and_chapter_gates():
    """is_unlocked returns True for practice, and respects chapter clearance gates."""
    # Practice is always unlocked
    assert charts.is_unlocked(gen.chart_id(1, 0), {}) is True

    # Chapter 1 (open) is always unlocked regardless of records
    open_chapter = charts.CHAPTER_OF.get("open-01")
    assert open_chapter in charts.unlocked_chapters({})

    # A later chapter with no stars should not be unlocked
    for cid, ch_id in charts.CHAPTER_OF.items():
        if ch_id != "open":
            # Ensure records have 0 stars for this chart
            assert charts.is_unlocked(cid, {cid: {"stars": 0}}) is False
            break


def test_packs_for_code_parses_valid_and_invalid_codes():
    """packs_for_code returns the correct lazy packs for valid practice codes, or [] for junk."""
    # Valid difficulty 3 code
    code = gen.code_of(3, 1234)
    packs = charts.packs_for_code(code)
    assert "practice" in packs

    # Invalid codes return []
    assert charts.packs_for_code("") == []
    assert charts.packs_for_code("XX1-0") == []
    assert charts.packs_for_code(None) == []
