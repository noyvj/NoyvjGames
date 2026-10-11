import json

import benches
import game


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def solve_current():
    for r, c, piece, state in game.game.bench.solution:
        v = call(action="place", r=r, c=c, piece=piece)
        for _ in range(state):
            v = call(action="flip", r=r, c=c)
    return v


def test_open_returns_the_whole_view():
    fresh()
    v = call(action="open")
    b = v["bench"]
    assert v["ok"] and b["id"] == "c1-1" and b["status"] == "open" and b["svg"].startswith("<svg") and b["rows"][3] == ">ooom".replace("m", "o")
    assert b["tray"][0]["piece"] == "mirror" and b["tray"][0]["left"] == 1 and b["need"] == 1 and b["lit"] == 0
    assert v["totals"] == {"benches": 40, "cleared": 0, "sensors": 0, "fewest": 0, "chapters": 5, "chapters_cleared": 0}
    assert v["tally"] == {"placed": 0, "picked": 0, "flips": 0, "hints": 0} and v["verdict"] is None
    assert len(v["chapters"]) == 5 and [c["open"] for c in v["chapters"]] == [True, False, False, False, False]
    assert v["map"].startswith("<svg") and len(v["log"]["shelf"]) == 5 and len(v["log"]["cards"]) == 40


def test_placing_the_stored_solution_clears_the_bench_and_names_the_result():
    fresh()
    v = solve_current()
    assert v["bench"]["status"] == "cleared" and v["bench"]["best"] == 1 and v["bench"]["fewest"] is True and v["bench"]["solved_now"]
    assert v["verdict"]["kind"] == "cleared" and v["verdict"]["pieces"] == 1 and v["verdict"]["fewest"] and v["verdict"]["next"] == "c1-2"
    assert "Bench cleared" in v["message"] and v["totals"]["cleared"] == 1 and v["totals"]["sensors"] == 1 and v["totals"]["fewest"] == 1
    assert v["bench"]["line"] == benches.BY_ID["c1-1"].line


def test_every_bench_can_be_cleared_by_playing_its_stored_solution():
    fresh()
    for bid in benches.ORDER:
        game.game._enter(bid)
        game.game.cleared.setdefault("c1-1", benches.BY_ID["c1-1"].solution_layout())
        for ch in (1, 2):                                                    # open every chapter for this walk through
            for b in benches.CHAPTERS[ch - 1]["benches"][:5]:
                game.game.cleared.setdefault(b.id, b.solution_layout())
        v = call(action="clear_bench")
        v = solve_current()
        assert v["bench"]["solved_now"] and bid in game.game.cleared and len(game.game.cleared[bid]) == benches.BY_ID[bid].par, bid


def test_flip_pickup_and_the_tray_count():
    fresh()
    v = call(action="place", r=3, c=1, piece="mirror")
    assert v["bench"]["tray"][0]["left"] == 0 and v["bench"]["pieces"] == 1 and v["tally"]["placed"] == 1
    v = call(action="place", r=3, c=2, piece="mirror")
    assert v["ok"] is False and "no mirror left" in v["message"]
    v = call(action="flip", r=3, c=1)
    assert v["ok"] and v["tally"]["flips"] == 1 and "backslash" in v["message"]
    v = call(action="pickup", r=3, c=1)
    assert v["bench"]["tray"][0]["left"] == 1 and v["tally"]["picked"] == 1 and v["bench"]["pieces"] == 0
    assert call(action="pickup", r=3, c=1)["ok"] is False and call(action="flip", r=3, c=1)["ok"] is False


def test_placing_on_an_occupied_slot_swaps_the_piece_back_to_the_tray():
    fresh()
    game.game._enter("c2-2")
    call(action="place", r=1, c=2, piece="mirror")
    v = call(action="place", r=1, c=2, piece="splitter")
    assert v["ok"] and v["bench"]["tray"][0]["left"] == 1 and v["tally"]["picked"] == 1 and "went back to the tray" in v["message"]
    assert call(action="place", r=1, c=2, piece="splitter")["ok"] is False                   # already there


def test_bad_places_and_bad_requests_are_refused_without_breaking_the_game():
    fresh()
    for req in ({"r": 0, "c": 0, "piece": "mirror"}, {"r": 99, "c": 0, "piece": "mirror"}, {"r": -1, "c": 0, "piece": "mirror"},
                {"r": "a", "c": 1, "piece": "mirror"}, {"r": True, "c": 1, "piece": "mirror"}, {"r": 3, "c": 1, "piece": "lens"},
                {"r": 3, "c": 1, "piece": "prism"}, {"r": 3, "c": 1, "piece": 5}, {"r": 3, "c": 1.5, "piece": "mirror"}, {"r": None, "c": None, "piece": None}):
        v = call(action="place", **req)
        assert v["ok"] is False and v["message"], req
    assert call(action="place")["ok"] is False
    assert call(action="pick", bench="nope")["ok"] is False and call(action="pick", bench=5)["ok"] is False
    assert "error" in call(action="dance")
    assert json.loads(game.handle("not json")) == {"error": "bad request"}
    assert json.loads(game.handle("[1]")) == {"error": "bad request"}
    assert call(action="open")["tally"]["placed"] == 0


def test_move_and_clear_bench():
    fresh()
    game.game._enter("c1-2")
    call(action="place", r=0, c=3, piece="mirror")
    v = call(action="move", r=0, c=3, to_r=0, to_c=2)
    assert v["ok"] and v["bench"]["placed"][0]["c"] == 2 and v["tally"]["placed"] == 2 and v["tally"]["picked"] == 1
    assert call(action="move", r=0, c=2, to_r=0, to_c=0)["ok"] is False                      # (0,0) is the emitter
    call(action="place", r=1, c=2, piece="mirror")
    assert call(action="move", r=0, c=2, to_r=1, to_c=2)["ok"] is False                     # occupied
    v = call(action="clear_bench")
    assert v["bench"]["pieces"] == 0 and v["tally"]["picked"] == 3
    assert call(action="clear_bench")["ok"] is False


def test_improving_a_clear_with_fewer_pieces_and_clearing_again():
    fresh()
    game.game._enter("c1-2")
    for cell in ((0, 3), (4, 3)):
        v = call(action="place", r=cell[0], c=cell[1], piece="mirror")
        call(action="flip", r=cell[0], c=cell[1])
    assert game.game.cleared["c1-2"] and len(game.game.cleared["c1-2"]) == 2
    call(action="flip", r=0, c=3)
    v = call(action="flip", r=0, c=3)
    assert v["verdict"]["kind"] == "again" and v["verdict"]["best"] == 2 and v["bench"]["status"] == "cleared"
    call(action="pickup", r=0, c=3)
    assert call(action="open")["bench"]["status"] == "cleared" and call(action="open")["verdict"] is None      # states only go up
    assert len(game.game.cleared["c1-2"]) == 2


def test_a_locked_chapter_cannot_be_entered_until_five_benches_are_cleared():
    fresh()
    v = call(action="pick", bench="c2-1")
    assert v["ok"] is False and v["bench"]["id"] == "c1-1" and "5 benches" in v["message"]
    for b in benches.CHAPTERS[0]["benches"][:5]:
        game.game.cleared[b.id] = b.solution_layout()
    assert call(action="pick", bench="c2-1")["bench"]["id"] == "c2-1"
    assert call(action="pick", bench="c3-1")["ok"] is False


def test_next_goes_to_the_next_open_bench_not_yet_cleared():
    fresh()
    assert call(action="next")["bench"]["id"] == "c1-2"
    for b in benches.CHAPTERS[0]["benches"]:
        game.game.cleared[b.id] = b.solution_layout()
    game.game._enter("c1-8")
    assert call(action="next")["bench"]["id"] == "c2-1"
    for b in benches.ALL_BENCHES:
        game.game.cleared[b.id] = b.solution_layout()
    assert call(action="next")["ok"] is False


def test_the_view_describes_the_bench_in_words():
    fresh()
    game.game._enter("c3-3")
    v = call(action="open")
    b = v["bench"]
    assert "Light all 2 sensors" in b["brief"] and "1 prism" in b["brief"] and b["emitters"] == ["Emitter at row 1, column 3 sends a white beam south."]
    assert [s["need"] for s in b["sensors"]] == ["L", "S"] and all("Sensor at row" in s["text"] for s in b["sensors"])
    v = call(action="place", r=2, c=2, piece="prism")
    assert v["bench"]["lit"] == 2 and all(s["lit"] for s in v["bench"]["sensors"]) and "2 of 2 sensors lit" in v["message"]


def test_reset_starts_over():
    fresh()
    solve_current()
    v = call(action="reset")
    assert v["totals"]["cleared"] == 0 and v["tally"]["placed"] == 0 and game.get_state() == {}
