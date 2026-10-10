import json

import achievements
import boards
import game
import hints
import logbook
import render
import rules


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def solve_board(bid):
    b = boards.BY_ID[bid]
    game.game._enter(bid)
    game.game.draw.load_answer(b.solution)
    game.game._record()


def test_the_first_three_decks_are_built_with_their_twists():
    sizes = [len(c["rooms"]) for c in boards.CHAPTER_LIST]
    assert sizes[:3] == [8, 8, 8]
    dock, crew, eng = ([boards.BY_ID[i] for i in boards.CHAPTER_LIST[k]["rooms"]] for k in range(3))
    assert all(b.twists == () for b in dock)
    assert all("holes" in b.twists and "bridges" not in b.twists for b in crew)
    assert all("bridges" in b.twists for b in eng)
    for b in eng:
        assert rules.flags_of(b, b.solution) == ["bridge"], b.id          # every bridge board really crosses on a bridge


def test_picking_a_board_in_a_far_deck_works_on_a_fresh_game():
    fresh()
    far = boards.CHAPTER_LIST[2]["rooms"][0]
    v = call(action="pick", board=far)
    assert v["ok"] and v["board"]["id"] == far and "Bridges" in boards.CHAPTER_LIST[2]["new"]
    v = call(action="pick", board=boards.CHAPTER_LIST[1]["rooms"][0])
    assert v["ok"] and "Holes" in v["board"]["new"]


def test_the_hint_ladder_climbs_three_rungs_for_free_and_counts_each_ask():
    fresh()
    base = call(action="open")
    assert base["hint"]["rung"] == 0 and base["hint"]["nudge"] == ""
    v1 = call(action="hint")
    assert v1["hint"]["rung"] == 1 and v1["hint"]["nudge"] and not v1["hint"]["hint"] and "hr-ghost" not in v1["layer"]
    v2 = call(action="hint")
    assert v2["hint"]["rung"] == 2 and v2["hint"]["hint"] and v2["layer"].count("hr-ghost") == 1
    v3 = call(action="hint")
    assert v3["hint"]["rung"] == 3 and v3["hint"]["answer"] and v3["layer"].count("hr-ghost") == len(game.game.board.lines)
    assert v3["tally"]["hints"] == 3
    assert call(action="hint")["ok"] is False and game.game.tally["hints"] == 3
    assert v3["board"]["status_name"] == "open" and v3["totals"]["patched"] == 0              # a hint never changes a state


def test_the_answer_can_be_laid_with_one_button_and_undone():
    fresh()
    assert call(action="load_answer")["ok"] is False
    for _ in range(3):
        call(action="hint")
    v = call(action="load_answer")
    assert v["board"]["status_name"] == "restored" and v["result"]["status"] == 2 and v["totals"]["restored"] == 1
    v = call(action="undo")
    assert v["board"]["status_name"] == "open" and v["totals"]["restored"] == 1


def test_hints_are_the_same_every_time_and_name_a_real_line():
    for b in boards.ALL_BOARDS:
        c = hints.starter(b)
        assert c in b.lines and hints.nudge_text(b) == hints.nudge_text(b)
        assert rules.LINE_NAMES[c] in hints.nudge_text(b) and rules.LINE_NAMES[c] in hints.hint_text(b)
        assert hints.ghosts(b, 0) == {} and set(hints.ghosts(b, 3)) == set(b.lines) and list(hints.ghosts(b, 2)) == [c]
        assert len(hints.ghosts(b, 2)[c]) == min(len(b.solution[c]), hints.OPENING + 1)


def test_hint_rungs_are_saved_and_validated():
    fresh()
    call(action="hint")
    call(action="hint")
    state = json.loads(json.dumps(game.get_state()))
    assert state["rungs"] == {boards.ORDER[0]: 2} and state["tally"]["hints"] == 2
    game.load_state(state)
    assert call(action="open")["hint"]["rung"] == 2
    game.load_state({"rungs": {boards.ORDER[0]: 9, "nope": 1, boards.ORDER[1]: True, boards.ORDER[2]: 3}})
    assert game.game.rungs == {boards.ORDER[2]: 3}


def test_every_board_has_a_quiet_log_line_and_it_is_found_when_the_room_is_patched():
    for bid in boards.ORDER:
        assert logbook.LOGS[bid].strip() and len(logbook.LOGS[bid]) < 220
    fresh()
    entries = call(action="open")["log"]
    assert len(entries) == len(boards.ORDER) and not any(e["found"] for e in entries) and not any(e["line"] for e in entries)
    solve_board(boards.ORDER[0])
    entries = call(action="open")["log"]
    assert entries[0]["found"] and entries[0]["line"] == logbook.LOGS[boards.ORDER[0]] and not entries[1]["found"]
    assert game.game.result["log"] == logbook.LOGS[boards.ORDER[0]] and game.game.result["first"] is True


def test_the_log_has_no_all_good_hero_and_nothing_timed():
    text = " ".join(logbook.LOGS.values()).lower()
    for word in ("timer", "countdown", "energy", "streak", "hurry", "daily", "limited time", "expires"):
        assert word not in text, word


def test_the_station_map_shows_every_room_in_its_state():
    fresh()
    svg = call(action="open")["map"]
    assert svg.count("hr-room s0") >= 8 and "hr-room s1" not in svg and "hr-hull-0" in svg
    solve_board(boards.ORDER[0])
    game.game.draw.clear()
    solve_board(boards.ORDER[1])
    game.game.draw.paths = {c: p for c, p in list(boards.BY_ID[boards.ORDER[1]].solution.items())[:0]}
    svg = render.station_svg(game.game._rooms_view())
    assert "hr-room s2" in svg and "hr-room-check" in svg and "hr-room-crack" in svg
    assert svg.count("data-id=") == len(boards.ORDER)
    assert "locked" not in svg and "data-open" not in svg       # every deck is open from the start


def test_the_map_marks_patched_with_a_dashed_ring_and_restored_with_a_check_not_only_light():
    decks = [{"name": "Test", "open": True, "rooms": [
        {"id": "a", "name": "A", "number": 1, "status": s, "status_name": rules.STATUS_NAMES[s], "open": True, "current": False} for s in (0, 1, 2)]}]
    svg = render.station_svg(decks)
    assert "hr-room-dash" in svg and "hr-room-check" in svg and "hr-room-crack" in svg
    assert svg.count("hr-room-empty") == 5


def test_three_goals_are_always_offered_and_every_achievement_can_be_one():
    fresh()
    v = call(action="open")
    assert len(v["goals"]) == 3 and all(not g["earned"] for g in v["goals"])
    assert len(achievements.goals({})) == 3 and len(achievements.goals({}, count=20)) == len(achievements.IDS)
    only = achievements.goals({f: 999 for f in ("patched", "restored", "decks_patched", "rung3", "laid", "flag_retry")})
    assert {a["id"] for a in only} == {"over_and_under", "mind_the_valve", "colour_theory"}


def test_achievement_facts_follow_play():
    fresh()
    solve_board(boards.ORDER[0])
    f = game.game.facts()
    assert f["patched"] == 1 and f["restored"] == 1 and "first_spark" in achievements.earned(f)
    state = game.get_state()
    assert "first_spark" in state["achievements_earned"]
    fresh()
    game.load_state({"achievements_earned": list(achievements.IDS)})
    assert not achievements.earned(game.game.facts())
