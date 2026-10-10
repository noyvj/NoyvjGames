"""The engine's one entry point: choosing, rewinding, going to a seen scene, the what-if peek, the hint ladder, the save contract."""

import json

import achievements
import game
import lore
import story
import explore


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()
    return call(action="open")


def play(path):
    v = None
    for ch in path:
        v = call(action="choose", i=int(ch))
        assert v["ok"], (path, ch, v["message"])
    return v


def test_a_fresh_game_starts_on_day_one_with_the_three_stats():
    v = fresh()
    assert v["run"]["scene"] == "d1a" and v["run"]["day"] == 1 and v["run"]["path"] == ""
    assert [(s["id"], s["value"]) for s in v["stats"]] == [("trust", 3), ("supplies", 6), ("hope", 5)]
    assert len(v["choices"]) == 3 and v["transcript"][0]["kind"] == "day" and v["transcript"][1]["kind"] == "narrator"


def test_choosing_moves_the_stats_and_the_visible_counters():
    fresh()
    v = call(action="choose", i=0)
    assert v["ok"] and "Trust +1" in v["message"] and v["run"]["scene"] == "d1b"
    assert [s["value"] for s in v["stats"]] == [4, 6, 6]
    assert v["tally"]["sent"] == 1 and v["progress"]["tried"][0] == 1 and v["progress"]["scenes"][0] == 2
    kinds = [t["kind"] for t in v["transcript"]]
    assert "you" in kinds and "delta" in kinds


def test_every_choice_is_answered_in_the_transcript():
    fresh()
    v = play("0000")
    kinds = [t["kind"] for t in v["transcript"]]
    for n, k in enumerate(kinds):
        if k == "you":
            assert kinds[n + 1] in ("ines", "action"), "an answer follows every reply"


def test_a_locked_or_bad_reply_is_refused_with_words():
    fresh()
    assert not call(action="choose", i=9)["ok"]
    assert not call(action="choose", i="0")["ok"]
    assert not call(action="choose", i=True)["ok"]
    v = play("12222")                   # reach a trust-gated scene with low trust is checked in the walker; here just ensure no crash
    assert v["run"]["steps"] == 5


def test_rewind_is_free_and_exact_and_nothing_is_lost():
    fresh()
    play("0000")
    full = call(action="open")
    v = call(action="rewind", step=2)
    assert v["ok"] and v["run"]["path"] == "00" and v["tally"]["rewinds"] == 1
    assert v["progress"]["tried"] == full["progress"]["tried"] and v["progress"]["scenes"] == full["progress"]["scenes"]
    assert not call(action="rewind", step=7)["ok"] and not call(action="rewind", step=-1)["ok"]
    v = call(action="restart")
    assert v["run"]["path"] == "" and v["tally"]["rewinds"] == 2
    assert not call(action="restart")["ok"]


def test_goto_takes_you_to_a_seen_scene_by_a_route_already_tried():
    fresh()
    play("0000")
    call(action="restart")
    assert not call(action="goto", scene="r11a")["ok"]
    v = call(action="goto", scene="d2b")
    assert v["ok"] and v["run"]["scene"] == "d2b" and v["tally"]["jumps"] == 1
    assert not call(action="goto", scene=5)["ok"]


def test_the_peek_opens_after_two_different_replies_in_a_scene():
    fresh()
    assert not call(action="peek")["ok"]
    play("0")
    call(action="restart")
    v = call(action="open")
    assert not v["peek"]["open"] and v["peek"]["need"] == 1
    play("1")
    call(action="restart")
    v = call(action="peek")
    assert v["ok"] and v["peek"]["showing"] and len(v["peek"]["rows"]) == 3 and v["tally"]["peeks"] == 1
    assert [r["tried"] for r in v["peek"]["rows"]] == [True, True, False]
    assert v["peek"]["rows"][2]["to"].startswith("Day 1:")
    assert call(action="peek")["tally"]["peeks"] == 1, "opening it again on the same scene is not counted twice"
    v = call(action="choose", i=0)
    assert not v["peek"]["showing"]


def test_the_hint_ladder_climbs_and_the_answer_takes_you_there():
    fresh()
    play("0")
    v = call(action="hint")
    assert v["hint"]["rung"] == 1 and "not walked" in v["hint"]["nudge"]
    call(action="hint")
    v = call(action="hint")
    assert v["hint"]["rung"] == 3 and v["hint"]["answer"] and v["tally"]["hints"] == 3
    assert not call(action="hint")["ok"]
    v = call(action="hint_do")
    assert v["ok"] and v["hint"]["rung"] == 0
    assert not call(action="hint_do")["ok"], "the answer rung must be showing first"


def test_walking_every_loose_end_reaches_one_hundred_percent():
    fresh()
    for _round in range(400):
        le = explore.loose_end(game.game.taken, game.game.path)
        if le is None:
            break
        if le["kind"] == "rewind":
            game.game.path = game.game.path[:le["step"]]
        else:
            game.game.path = le["path"]
        game.game._sync()
        assert game.game.choose(le["choice"])[0], le
    else:
        raise AssertionError("loose ends never ran out")
    v = call(action="open")
    assert v["progress"]["tried"][0] == v["progress"]["tried"][1] == len(story.EDGES)
    assert v["progress"]["scenes"][0] == len(story.SCENES) and v["progress"]["endings"] == [9, 9]
    assert v["progress"]["archive"] == [29, 29] and v["progress"]["percent"] == 100
    earned = {a["id"] for a in v["achievements"] if a["earned"]}
    assert earned == set(achievements.IDS) - {"a_look_ahead", "second_thoughts"}, "walking the loose ends never needs a rewind or a peek button"


def test_save_round_trip_keeps_the_run_and_the_record():
    fresh()
    play("0102")
    call(action="rewind", step=2)
    state = json.loads(json.dumps(game.get_state()))
    assert state["path"] == "01" and "taken" in state and state["tally"]["rewinds"] == 1
    game.game.__init__()
    game.load_state(state)
    assert json.loads(json.dumps(game.get_state())) == state


def test_a_fresh_game_saves_nothing_and_only_non_default_keys_are_written():
    fresh()
    assert game.get_state() == {}
    play("0")
    assert set(game.get_state()) <= {"path", "taken", "seen", "endings", "found", "tally", "achievements_earned"}


def test_bad_saves_never_crash_and_fall_back_field_by_field():
    for bad in (None, 5, "x", [], {"path": "9999"}, {"path": 12}, {"taken": "no"}, {"taken": ["nope:9>d1b", 4, "d1a:7>d1b", "d1a:0>zzz"]}, {"found": ["zz", 3]},
                {"endings": "all"}, {"tally": {"rewinds": -1, "peeks": "x"}}, {"seen": ["ghost"]}, {"path": "0" * 500}):
        game.game.__init__()
        game.load_state(bad)
        v = call(action="open")
        assert v["run"]["scene"] in story.SCENES
        assert v["progress"]["tried"][0] <= len(story.EDGES)
    game.load_state({"path": "9999", "found": ["log_01", "bogus"], "taken": ["d1a:0>d1b", "d1a:55>d1b"], "tally": {"rewinds": 3}})
    s = game.get_state()
    assert "path" not in s and s["found"] == ["log_01"] and s["taken"] == ["d1a:0>d1b"] and s["tally"] == {"rewinds": 3}


def test_achievements_are_written_but_never_read_back():
    fresh()
    play("0")
    state = game.get_state()
    assert "first_words" in state["achievements_earned"]
    state["achievements_earned"] = list(achievements.IDS)
    game.game.__init__()
    game.load_state(state)
    assert game.get_state()["achievements_earned"] == ["first_words"]


def test_reset_erases_everything():
    fresh()
    play("0000")
    v = call(action="reset")
    assert v["run"]["path"] == "" and v["progress"]["tried"][0] == 0 and game.get_state() == {}


def test_the_archive_shows_a_hint_until_a_thing_is_found():
    v = fresh()
    entries = {e["id"]: e for s in v["archive"] for e in s["entries"]}
    assert not entries["log_01"]["found"] and entries["log_01"]["title"] == "Not found yet" and "Day 1" in entries["log_01"]["text"]
    v = play("0002")                    # d1d reply 0 finds log_01 only via reply 0
    v = fresh() and play("00" + "0")
    entries = {e["id"]: e for s in v["archive"] for e in s["entries"]}
    assert entries["log_01"]["found"] and entries["log_01"]["text"] == lore.COLLECT_BY_ID["log_01"][3]


def test_unknown_requests_get_an_error_not_a_crash():
    assert "error" in json.loads(game.handle("not json"))
    assert "error" in json.loads(game.handle("[]"))
    assert "error" in json.loads(game.handle('{"action": "dance"}'))
