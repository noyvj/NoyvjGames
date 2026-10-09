import dsl
from editor import Editor, fmt_addr, get_list, parse_addr


def ed(allow="F L R G P S rep until if A B"):
    return Editor(None, allow)


def test_insert_actions_moves_the_cursor():
    e = ed()
    for a in "FFL":
        assert e.insert(a)
    assert e.prog["main"] == ["F", "F", "L"] and e.cursor == (("main",), 3)


def test_insert_at_a_gap_in_the_middle():
    e = ed()
    for a in "FF":
        e.insert(a)
    e.set_cursor(("main",), 1)
    e.insert("L")
    assert e.prog["main"] == ["F", "L", "F"] and e.cursor == (("main",), 2)


def test_blocks_put_the_cursor_inside_and_fill_in_order():
    e = ed()
    e.insert(["rep", 3, []])
    assert e.cursor == (("main", 0, 2), 0)
    e.insert("F")
    e.insert("L")
    assert e.prog["main"] == [["rep", 3, ["F", "L"]]]
    e.set_cursor(("main",), 1)
    e.insert("G")
    assert e.prog["main"][1] == "G"


def test_if_has_two_lists():
    e = ed()
    e.insert(["if", "part", [], []])
    e.insert("G")
    e.set_cursor(("main", 0, 3), 0)
    e.insert("F")
    assert e.prog["main"] == [["if", "part", ["G"], ["F"]]]


def test_refuses_what_the_room_does_not_allow_and_keeps_the_list():
    e = ed("F")
    assert not e.insert("L") and "not available" in e.last_error
    assert not e.insert(["rep", 2, []])
    assert e.prog["main"] == []


def test_refuses_over_the_cap_and_over_deep():
    e = ed()
    for _ in range(dsl.MAX_SIZE):
        assert e.insert("F")
    assert not e.insert("F") and "at most" in e.last_error
    e = ed()
    for _ in range(dsl.MAX_DEPTH):
        assert e.insert(["rep", 2, []])
    assert not e.insert(["rep", 2, []])
    assert e.insert("F")


def test_calls_follow_the_routine_rules():
    e = ed()
    assert e.insert(["call", "A"])
    assert e.go_routine("A")
    assert not e.insert(["call", "B"]) and e.can_insert(["call", "A"])
    assert e.go_routine("B")
    assert e.insert(["call", "A"])
    assert e.can_insert(["call", "B"])


def test_remove_adjusts_the_cursor():
    e = ed()
    for a in "FLR":
        e.insert(a)
    assert e.remove(("main", 0))
    assert e.prog["main"] == ["L", "R"] and e.cursor == (("main",), 2)
    e = ed()
    e.insert(["rep", 2, []])
    e.insert("F")
    assert e.remove(("main", 0))
    assert e.prog["main"] == [] and e.cursor == (("main",), 0)


def test_remove_earlier_sibling_keeps_the_cursor_in_the_same_block():
    e = ed()
    e.insert("F")
    e.insert(["rep", 2, []])
    e.insert("L")
    assert e.cursor == (("main", 1, 2), 1)
    e.remove(("main", 0))
    assert e.cursor == (("main", 0, 2), 1) and get_list(e.prog, e.cursor[0]) == ["L"]


def test_move_swaps_neighbours():
    e = ed()
    for a in "FLR":
        e.insert(a)
    assert e.move(("main", 0), 1)
    assert e.prog["main"] == ["L", "F", "R"]
    assert not e.move(("main", 2), 1) and not e.move(("main", 0), -1)


def test_set_count_and_cond_are_validated():
    e = ed()
    e.insert(["rep", 3, []])
    assert e.set_count(("main", 0), 5) and e.prog["main"][0][1] == 5
    assert not e.set_count(("main", 0), 12) and not e.set_count(("main", 0), 1)
    e.set_cursor(("main",), 1)
    e.insert(["until", "blocked", []])
    assert e.set_cond(("main", 1), "!carrying") and e.prog["main"][1][1] == "!carrying"
    assert not e.set_cond(("main", 1), "nonsense")
    assert not e.set_cond(("main", 0), "part")


def test_undo_and_clear():
    e = ed()
    e.insert("F")
    e.insert("L")
    assert e.undo() and e.prog["main"] == ["F"]
    assert e.clear() and e.prog["main"] == [] and e.undo() and e.prog["main"] == ["F"]
    assert not Editor().undo()


def test_load_replaces_and_is_undoable():
    e = ed()
    e.insert("F")
    assert e.load(dsl.from_text("main: L L"))
    assert e.prog["main"] == ["L", "L"] and e.undo() and e.prog["main"] == ["F"]
    assert not ed("F").load(dsl.from_text("main: L"))


def test_addresses_round_trip_and_bad_ones_are_none():
    assert parse_addr("main/2/2") == ("main", 2, 2) and fmt_addr(("main", 2, 2)) == "main/2/2"
    for bad in ("", "x/1", "main/a", None, 5, "main/-1"):
        assert parse_addr(bad) is None


def test_set_cursor_rejects_bad_places():
    e = ed()
    e.insert("F")
    assert not e.set_cursor(("main",), 5) and not e.set_cursor(("A",), 0) and not e.set_cursor(("main", 3, 2), 0)
    assert e.set_cursor(("main",), 0)
