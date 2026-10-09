"""The finished game as a whole: 60 shifts in 8 chapters, every crew story reachable, and a player who plays every shift well
earns every achievement and fills the whole Record."""

import json
from collections import Counter

import achievements
import cases
import cast
import codex
import game
import lexicon as lx
import progress


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def test_sixty_shifts_in_eight_chapters():
    assert [len(c["shifts"]) for c in progress.CHAPTERS] == [7, 8, 8, 8, 8, 8, 7, 6]
    assert len(progress.ORDER) == 60 and len(cast.STATION_NOTES) == 8 and len(cases.ALL) == 60


def test_every_crew_story_can_be_told_to_its_last_page():
    seen = Counter(p["crew"] for d in cases.ALL for p in d["patients"])
    for crew in cast.CREW_IDS:
        assert seen[crew] >= cast.BEAT_AT[-1], crew
    told = codex.beats_told({sid: 1 for sid in progress.ORDER})
    assert len(told) == len(cast.CREW_IDS) * len(cast.BEAT_AT)
    assert len(codex.tally_told({sid: 1 for sid in progress.ORDER})) == len(cast.TALLY_BEATS)


def test_every_scan_and_every_treatment_can_be_used_somewhere():
    for tid in lx.TEST_IDS:
        assert any(tid in d.get("tests", "").split() for d in cases.ALL), tid
    for tid in lx.TX_IDS:
        assert any(_can_cure(d["id"], tid) for d in cases.ALL), tid


def _can_cure(sid, tid):
    """True if treatment `tid` is on the shelf in this shift and cures one of its patients without a chart note against it."""
    c = game.compiled(sid)
    if tid not in c.tx or c.stock0[c.item_ix[lx.TX_BY_ID[tid]["item"]]] < 1:
        return False
    x = c.tx.index(tid)
    return any(tid in lx.COND[cond]["cures"] and not c.tx_forbidden(i, x) for i, p in enumerate(c.patients) for cond in p.truth)


def test_chapters_get_new_tools_in_order():
    first = {}
    for d in cases.ALL:
        c = game.compiled(d["id"])
        ch = progress.CHAPTER_OF[d["id"]]
        for name, used in (("tests", bool(c.tests)), ("traits", any(p.traits for p in c.patients)), ("beds", bool(c.beds)),
                           ("band", c.band and any(p.shaking for p in c.patients)), ("robots", bool(c.robots)), ("pairs", c.maxc == 2)):
            if used:
                first.setdefault(name, ch)
    assert first["tests"] == 1 and first["traits"] == 2 and first["beds"] == 4 and first["band"] == 5 and first["robots"] == 5 and first["pairs"] == 6


def _play_clean(sid):
    game.game._enter(sid)
    for _ in range(80):
        if game.game.case.done(game.game.st):
            break
        for _r in range(3):
            call(action="hint")
        assert call(action="hint_do")["ok"], sid
    assert game.game.result["grade"] == 3, sid


def test_perfect_play_earns_every_achievement_and_fills_the_record():
    game.game.__init__()
    for sid in progress.ORDER:
        _play_clean(sid)
    # a completionist also tries each remaining scan and treatment once, on a shift where it works
    for tid in lx.TX_IDS:
        if tid in game.game.rec_cures:
            continue
        for d in cases.ALL:
            c = game.compiled(d["id"])
            for i, p in enumerate(c.patients):
                if tid in c.tx and any(tid in lx.COND[t]["cures"] for t in p.truth) and not c.tx_forbidden(i, c.tx.index(tid)) and not p.shaking \
                        and not c.maybe_spreads(i, (-1,) * len(c.tests)) and len(c.candidates(i, (-1,) * len(c.tests))) == 1 and c.stock0[c.item_ix[lx.TX_BY_ID[tid]["item"]]]:
                    game.game._enter(d["id"])
                    game.game.restore()
                    game.game.do(("treat", i, c.tx.index(tid)))
                    break
            else:
                continue
            break
    for tid in lx.TEST_IDS:
        if tid not in game.game.rec_tests:
            d = next(d for d in cases.ALL if tid in d.get("tests", "").split())
            game.game._enter(d["id"])
            game.game.restore()
            c = game.game.case
            for i, p in enumerate(c.patients):
                if not p.shaking and not p.spreads and game.game.do(("scan", i, c.tests.index(tid)))[0]:
                    break
    v = call(action="open")
    assert v["totals"]["clean"] == 60 and v["totals"]["done"] == 60
    got = [a["id"] for a in v["achievements"] if a["earned"]]
    assert sorted(got) == sorted(achievements.IDS), set(achievements.IDS) - set(got)
    assert v["record"]["found"] == v["record"]["total"], [(s["id"], s["found"], s["total"]) for s in v["record"]["sections"]]
    assert game.get_state()["achievements_earned"] == list(achievements.IDS)
