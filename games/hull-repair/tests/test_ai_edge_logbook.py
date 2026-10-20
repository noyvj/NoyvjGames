import logbook
import boards


def test_line_for_returns_log_when_bid_exists():
    """line_for should return the exact log string for a known board id."""
    bid = "airlock-two"
    result = logbook.line_for(bid)
    assert result == logbook.LOGS[bid]


def test_line_for_returns_empty_string_for_missing_bid():
    """line_for should fall back to an empty string when the board id is not in LOGS."""
    result = logbook.line_for("nonexistent-room")
    assert result == ""


def test_entries_with_empty_state_marks_all_rooms_unfound():
    """entries with zero input (empty state dict) should mark every room as not found with an empty line."""
    st = {}
    entries = logbook.entries(st)
    assert len(entries) == len(boards.ORDER)
    for entry in entries:
        assert entry["found"] is False
        assert entry["line"] == ""


def test_entries_with_single_patched_room():
    """entries with the smallest non-zero input (one room patched) should mark only that room found."""
    st = {"airlock-two": 1}
    entries = logbook.entries(st)
    by_id = {e["id"]: e for e in entries}
    assert by_id["airlock-two"]["found"] is True
    for bid in boards.ORDER:
        if bid != "airlock-two":
            assert by_id[bid]["found"] is False


def test_entries_with_all_rooms_patched():
    """entries with the largest input (all rooms patched) should mark every room found with its line."""
    st = {bid: 1 for bid in boards.ORDER}
    entries = logbook.entries(st)
    by_id = {e["id"]: e for e in entries}
    for bid in boards.ORDER:
        assert by_id[bid]["found"] is True
        assert by_id[bid]["line"] == logbook.LOGS[bid]


def test_entries_preserves_board_order_and_deck_names():
    """entries should iterate in boards.ORDER and use the correct deck name from CHAPTER_LIST."""
    st = {}
    entries = logbook.entries(st)
    for i, bid in enumerate(boards.ORDER):
        assert entries[i]["id"] == bid
        b = boards.BY_ID[bid]
        assert entries[i]["deck"] == boards.CHAPTER_LIST[b.chapter]["name"]
