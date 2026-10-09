import json

import boards
import game
import progress
import rules


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def lay(bid, upto=None, lines=None):
    """Lay the stored layout of a board by dragging, a line at a time."""
    b = boards.BY_ID[bid]
    if game.game.current != bid:
        call(action="pick", board=bid)
    last = None
    for c in lines or b.lines:
        path = b.solution[c][:upto]
        r = call(action="begin", x=path[0][0], y=path[0][1])
        assert r["ok"], r["message"]
        r = call(action="move", cells=[list(p) for p in path[1:]])
        assert r["ok"], r["message"]
        last = call(action="end")
    return last


def test_open_returns_the_whole_view():
    fresh()
    v = call(action="open")
    assert v["board"]["id"] == boards.ORDER[0] and v["board"]["svg"].startswith("<svg") and v["layer"] is not None
    assert v["totals"]["rooms"] == len(boards.ORDER) and v["tally"] == {"laid": 0, "erased": 0, "undos": 0}
    assert [line["c"] for line in v["board"]["lines"]] == list(boards.ALL_BOARDS[0].lines)
    assert call(action="open")["rooms"][0]["open"] is True


def test_the_svg_is_sent_only_when_the_board_changes():
    fresh()
    call(action="open")
    v = call(action="begin", x=3, y=0)
    assert "svg" not in v["board"]
    v = call(action="pick", board=boards.ORDER[1])
    assert "svg" in v["board"]


def test_laying_every_line_restores_the_room_and_counts_everything():
    fresh()
    b = boards.ALL_BOARDS[0]
    r = lay(b.id)
    assert r["result"]["status"] == 2 and r["result"]["first"] and r["result"]["next"] == boards.ORDER[1]
    assert r["totals"]["patched"] == 1 and r["totals"]["restored"] == 1
    assert r["tally"]["laid"] == sum(len(p) - 1 for p in b.solution.values())
    assert r["board"]["empty"] == 0 and r["board"]["status_name"] == "restored"


def test_joining_the_lines_without_covering_every_cell_only_patches():
    fresh()
    spec = {"id": "p", "rows": ["A...a", ".....", ".....", ".....", "....."]}
    loose = rules.Board(spec)
    loose.chapter, loose.number = 0, 1
    boards.BY_ID["p"] = loose
    boards.ORDER.append("p")
    try:
        game.game._enter("p")
        call(action="begin", x=0, y=0)
        call(action="move", cells=[[1, 0], [2, 0], [3, 0], [4, 0]])
        v = call(action="end")
        assert v["result"]["status"] == 1 and v["result"]["empty"] == 20 and v["board"]["status_name"] == "patched"
        assert v["totals"]["patched"] == 1
    finally:
        del boards.BY_ID["p"]
        boards.ORDER.remove("p")
        fresh()


def test_a_refused_move_changes_nothing_and_says_why():
    fresh()
    call(action="begin", x=3, y=0)
    v = call(action="move", cells=[[2, 0], [0, 0]])
    assert v["ok"] is False and v["message"]
    assert [list(p) for p in game.game.draw.paths["A"]] == [[3, 0], [2, 0]]


def test_bad_requests_are_refused_without_breaking_the_game():
    fresh()
    assert call(action="begin", x="a", y=0)["ok"] is False
    assert call(action="begin", x=True, y=0)["ok"] is False
    assert call(action="move", cells="no")["ok"] is False
    assert call(action="move", cells=[[1]])["ok"] is False
    assert call(action="pick", board="nope")["ok"] is False
    assert call(action="pick", board=5)["ok"] is False
    assert "error" in call(action="dance")
    assert json.loads(game.handle("not json")) == {"error": "bad request"}
    assert json.loads(game.handle("[1]")) == {"error": "bad request"}
    assert call(action="begin", x=99, y=99)["ok"] is False
    assert call(action="cell", x=99, y=99)["cell_text"] == ""
    assert call(action="cell", x=3, y=0)["cell_text"].startswith("column 4, row 1")


def test_undo_clear_and_clear_line_are_counted_and_never_lose_a_repair():
    fresh()
    b = boards.ALL_BOARDS[0]
    lay(b.id)
    v = call(action="clear")
    assert v["board"]["status_name"] == "open" and v["totals"]["restored"] == 1 and v["tally"]["erased"] > 0
    v = call(action="undo")
    assert v["board"]["status_name"] == "restored" and v["tally"]["undos"] == 1
    v = call(action="clear_line", line="A")
    assert "A" not in game.game.draw.paths
    assert call(action="clear_line", line="Z")["ok"] is False
    fresh()
    assert call(action="undo")["ok"] is False and call(action="clear")["ok"] is False


def test_the_next_deck_is_locked_until_five_rooms_are_patched():
    fresh()
    assert progress.chapter_open(game.game.st, 0) and not progress.chapter_open(game.game.st, 1)
    v = call(action="pick", board=boards.CHAPTER_LIST[0]["rooms"][3])
    assert v["ok"] and v["board"]["id"] == boards.CHAPTER_LIST[0]["rooms"][3]


def test_next_goes_to_an_unpatched_open_room():
    fresh()
    first = boards.ORDER[0]
    lay(first)
    assert call(action="next")["board"]["id"] == boards.ORDER[1]


def test_save_round_trip_keeps_best_drafts_tally_and_flags():
    fresh()
    lay(boards.ORDER[0])
    lay(boards.ORDER[1], upto=3, lines=[boards.ALL_BOARDS[1].lines[0]])
    state = json.loads(json.dumps(game.get_state()))
    assert set(state) == {"cur", "best", "draft", "tally"}
    fresh()
    game.load_state(state)
    v = call(action="open")
    assert v["totals"]["restored"] == 1 and v["board"]["id"] == boards.ORDER[1] and v["tally"]["laid"] == state["tally"]["laid"]
    assert game.game.draw.paths                          # the unfinished line came back
    assert game.get_state() == state


def test_a_save_holds_only_what_differs_from_a_fresh_game():
    fresh()
    assert game.get_state() == {}
    call(action="begin", x=3, y=0)
    call(action="end")
    assert game.get_state() == {}


def test_only_fully_validated_state_loads():
    fresh()
    b = boards.ALL_BOARDS[0]
    good = rules.encode(b.solution)
    cases = [
        None, 5, "x", [], {"best": 5}, {"best": {b.id: 7}}, {"best": {b.id: "A00"}}, {"best": {b.id: good.replace("A", "Q")}},
        {"best": {"nope": good}}, {"tally": {"laid": -4, "erased": "x", "undos": True}}, {"flags": "bridge"}, {"cur": "ghost"},
        {"cur": boards.ORDER[0], "draft": {b.id: "A99"}}, {"best": {b.id: good + ";" + good}},
    ]
    for data in cases:
        game.load_state(data)
        v = call(action="open")
        assert v["totals"]["patched"] == 0 and all(x >= 0 for x in v["tally"].values()), data
    game.load_state({"best": {b.id: good}, "tally": {"laid": 12, "erased": -1}, "flags": ["bridge", "bogus"], "cur": "nowhere"})
    v = call(action="open")
    assert v["totals"]["restored"] == 1 and v["tally"] == {"laid": 12, "erased": 0, "undos": 0} and game.game.flags == ["bridge"]
    assert v["board"]["id"] == boards.ORDER[0]


def test_a_saved_best_must_really_patch_its_board():
    fresh()
    b = boards.ALL_BOARDS[0]
    partial = dict(b.solution)
    partial.pop(b.lines[0])
    game.load_state({"best": {b.id: rules.encode(partial)}})
    assert call(action="open")["totals"]["patched"] == 0


def test_a_patch_is_upgraded_to_a_restore_and_a_restore_is_never_downgraded():
    fresh()
    b = boards.ALL_BOARDS[0]
    lay(b.id)
    game.game.st[b.id] = 2
    call(action="clear")
    assert game.game.st[b.id] == 2 and rules.status(b, game.game.best[b.id]) == 2


def test_reset_starts_over():
    fresh()
    lay(boards.ORDER[0])
    v = call(action="reset")
    assert v["totals"]["patched"] == 0 and v["tally"]["laid"] == 0 and game.get_state() == {}


def test_flags_note_the_twists_and_the_take_backs():
    fresh()
    b = boards.ALL_BOARDS[0]
    call(action="begin", x=3, y=0)
    call(action="move", cells=[[2, 0]])
    call(action="move", cells=[[3, 0]])
    call(action="end")
    lay(b.id)
    assert "retry" in game.game.flags
