"""Edge-case tests for logbook.py."""


import benches
import game
import logbook


def setup_function(_fn):
    game.game.__init__()


def test_families_used_with_empty_input_returns_empty_set():
    assert logbook.families_used([]) == set()


def test_families_used_with_unknown_pieces_ignores_them():
    result = logbook.families_used(["mirror", "unknown_piece", "splitter"])
    assert result == {"mirror", "splitter"}


def test_shelf_with_no_used_families_marks_all_pages_empty():
    pages = logbook.shelf(set())
    assert len(pages) == len(logbook.SHELF)
    assert all(not p["filled"] for p in pages)


def test_shelf_with_one_family_marks_only_that_page_filled():
    pages = logbook.shelf({"prism"})
    prism_page = next(p for p in pages if p["id"] == "prism")
    assert prism_page["filled"] is True
    assert all(not p["filled"] for p in pages if p["id"] != "prism")


def test_cards_with_empty_cleared_dict_returns_all_unlocked_and_unfilled():
    game.game.cleared = {}
    cards = logbook.cards(game.game.cleared)
    assert len(cards) == len(benches.ALL_BENCHES)
    for card in cards:
        assert card["filled"] is False
        assert "locked" in card


def test_summary_with_empty_inputs_returns_zero_counts():
    s = logbook.summary(set(), {})
    assert s["pages"] == 0
    assert s["pages_total"] == len(logbook.SHELF)
    assert s["cards"] == 0
    assert s["cards_total"] == len(benches.ALL_BENCHES)


def test_cards_with_partial_cleared_benches():
    game.game.cleared = {"c1-1": benches.BY_ID["c1-1"].solution_layout()}
    cards = logbook.cards(game.game.cleared)
    c1_1_card = next(c for c in cards if c["id"] == "c1-1")
    assert c1_1_card["filled"] is True
    assert c1_1_card["pieces"] > 0
    assert "line" in c1_1_card
