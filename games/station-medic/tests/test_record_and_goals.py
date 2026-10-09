"""The Record (codex), crew beats, the achievements' facts and the always-visible three goals."""

import json

import achievements
import cast
import codex
import game
import lexicon as lx
import progress


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()
    return call(action="open")


def test_a_fresh_record_is_locked_and_reveals_nothing_unearned():
    v = fresh()
    rec = v["record"]
    assert rec["found"] == 0 and rec["total"] == achievements.RECORD_TOTAL and "fiction game" in rec["notice"]
    for sec in rec["sections"]:
        for e in sec["entries"]:
            if sec["id"] == "crew":
                assert e["lines"] == []
            else:
                assert not e["unlocked"] and e["title"] in ("Not filed yet", "Not written yet") and e["lines"] == []


def test_curing_files_the_condition_and_the_treatment_and_a_scan_files_the_scan():
    fresh()
    v = call(action="treat", p=0, x=0)
    secs = {s["id"]: s for s in v["record"]["sections"]}
    assert secs["conditions"]["found"] == 1 and secs["treatments"]["found"] == 1 and secs["crew"]["found"] == 1
    cond = [e for e in secs["conditions"]["entries"] if e["unlocked"]][0]
    assert cond["title"] == "Hollow Ache" and any("Cured by" in line for line in cond["lines"])
    game.game.best.update({sid: 3 for sid in progress.CHAPTERS[0]["shifts"][:5]})
    call(action="pick", shift="2-1")
    v = call(action="scan", p=0, t=0)
    assert [s for s in v["record"]["sections"] if s["id"] == "scans"][0]["found"] == 1


def test_crew_beats_follow_the_authored_order_not_the_play_order():
    told_in_order = codex.beats_told({sid: 3 for sid in progress.ORDER})
    for sid in progress.ORDER:
        for crew, k in codex.BEATS_BY_SHIFT[sid]:
            assert 0 <= k < len(cast.BEATS[crew])
    # the first appearance of every crew member tells their first beat
    firsts = {}
    for sid in progress.ORDER:
        for crew, k in codex.BEATS_BY_SHIFT[sid]:
            firsts.setdefault(crew, k)
    assert all(k == 0 for k in firsts.values()) and set(firsts) == set(cast.CREW_IDS)
    assert len(told_in_order) == len(set(told_in_order))


def test_finishing_a_shift_tells_its_beats_and_the_result_card_carries_them():
    fresh()
    v = call(action="treat", p=0, x=0)
    assert v["result"]["beats"] and v["result"]["beats"][0]["who"] == "Imre Solace"
    game.game.best.update({sid: 1 for sid in progress.CHAPTERS[0]["shifts"]})
    rec = call(action="open")["record"]
    notes = [s for s in rec["sections"] if s["id"] == "notes"][0]
    assert notes["found"] == 1 and notes["entries"][0]["unlocked"] and not notes["entries"][1]["unlocked"]


def test_every_beat_and_note_is_short_and_safe():
    for crew, beats in cast.BEATS.items():
        assert len(beats) == len(cast.BEAT_AT) and all(20 < len(b) < 260 for b in beats), crew
    assert len(cast.STATION_NOTES) == len(progress.CHAPTERS) or len(cast.STATION_NOTES) >= len(progress.CHAPTERS)


def test_the_codex_counts_agree_with_the_view():
    fresh()
    game.game.best.update({sid: 3 for sid in progress.ORDER})
    game.game.rec_cured = list(lx.COND_IDS)
    game.game.rec_cures = list(lx.TX_IDS)
    game.game.rec_tests = list(lx.TEST_IDS)
    rec = call(action="open")["record"]
    found, total = codex.counts(game.game.rec_cured, game.game.rec_cures, game.game.rec_tests, game.game.best)
    assert (rec["found"], rec["total"]) == (found, total)
    assert sum(s["found"] for s in rec["sections"]) == rec["found"]


def test_there_are_always_three_goals_in_any_order_and_they_only_name_open_chapters():
    v = fresh()
    assert len(v["goals"]) == 3 and all(g["chapter"] < 1 for g in v["goals"])
    assert 'id="goals"' in open(game.__file__.replace("game.py", "index.html"), encoding="utf-8").read()
    for g in v["goals"]:
        assert 0 <= g["have"] < g["need"]


def test_achievement_facts_are_computed_from_progress_alone():
    fresh()
    game.game.best.update({"1-1": 3, "1-2": 2})
    f = game.game.facts()
    assert f["done"] == 2 and f["clean"] == 1 and f["cold_clean"] == 0
    assert len(achievements.IDS) == 14 and len(set(achievements.IDS)) == 14
