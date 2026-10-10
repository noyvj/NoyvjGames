"""Every authored case is checked by the solver: sound, deducible with a unique answer, solvable with a clean finish (one trip and no
wrong guess) by the careful plan, and the choice of bag matters."""

from collections import Counter
from itertools import combinations

import casework as cw
import cases
import houses
import lexicon as lx
import progress
import solver

ALL = [(d["id"], cw.Case(d)) for d in cases.ALL]


def test_forty_cases_in_five_chapters_of_eight():
    assert len(cases.ALL) == 40 and [len(c["cases"]) for c in progress.CHAPTERS] == [8] * 5
    assert len({d["id"] for d in cases.ALL}) == 40 and len({d["title"] for d in cases.ALL}) == 40
    assert progress.ORDER[0] == "1-1" and progress.ORDER[-1] == "5-8"


def test_every_case_is_sound_and_fair():
    for cid, _case in ALL:
        assert solver.validate(progress.DATA[cid]) == [], cid


def test_the_careful_plan_finishes_every_case_clean_in_one_trip():
    for cid, case in ALL:
        st = case.new_state()
        tokens = []
        for _ in range(200):
            act = solver.next_action(case, st)
            assert act is not None, cid
            st, _info = case.apply(st, act)
            assert st is not None, (cid, act)
            tokens.append(cw.to_token(act))
            if act[0] == "accuse":
                break
        assert st[cw.SOLVED] and case.total_cost(st) == 0 and st[cw.TRIPS] == 1, cid
        assert cw.replay(case, tokens)[0] == st, cid


def test_the_answer_is_unique_once_everything_is_read():
    for cid, case in ALL:
        st = case.new_state()
        st = st[:cw.LOOKED] + (1,) + st[cw.LOOKED + 1:]
        st = st[:cw.ENTERED] + ((1 << len(case.rooms)) - 1,) + st[cw.ENTERED + 1:]
        notes = list(st[cw.NOTES])
        for r in range(len(case.rooms)):
            for e in range(6):
                notes[r * 6 + e] = case.reading(r, e)
        st = st[:cw.NOTES] + (tuple(notes),)
        for s in range(case.n):
            assert case.candidates(st, s) == [case.truth[s]], (cid, s, case.candidates(st, s))


def test_a_smallest_bag_exists_within_the_kit_and_tools_are_needed():
    for cid, case in ALL:
        info = solver.analyse(case)
        assert 1 <= info["min_kit"] <= case.kit_size, cid
        assert max(len(c) for c in info["cands"]) >= 2, "%s: the file alone already names the spirit" % cid


def test_the_choice_of_bag_matters_in_every_case():
    for cid, case in ALL:
        bad = [k for size in range(1, case.kit_size + 1) for k in combinations(range(6), size)
               if not all(solver.separates(case, set(k), s) for s in range(case.n))]
        assert bad, "%s: every bag works, so there is no choice to make" % cid


def test_the_first_cases_are_gentle():
    first = solver.analyse(cw.Case(progress.DATA["1-1"]))
    assert first["min_kit"] == 1 and len(progress.DATA["1-1"]["pool"]) == 3


def test_chapter_mechanics_arrive_in_order():
    ch = progress.CHAPTERS
    sizes = [houses.size_of(progress.DATA[c]["layout"]) for c in ch[0]["cases"]]
    assert sizes == sorted(sizes) and sizes[0] == 3 and sizes[-1] == 7
    assert all(len(progress.DATA[c]["truth"]) == 1 and not progress.DATA[c]["keepsake"] for c in ch[0]["cases"] + ch[1]["cases"])
    assert all(progress.DATA[c]["features"] for c in ch[1]["cases"])
    assert all(len(progress.DATA[c]["truth"]) == 2 for c in ch[2]["cases"])
    assert all(progress.DATA[c]["keepsake"] for c in ch[3]["cases"])
    assert all(houses.size_of(progress.DATA[c]["layout"]) >= 10 and progress.DATA[c]["kit"] == 4 for c in ch[4]["cases"])
    assert all(progress.DATA[c]["kit"] == 3 for c in ch[0]["cases"] + ch[1]["cases"] + ch[2]["cases"] + ch[3]["cases"])


def test_every_kind_feature_and_keepsake_appears_in_the_book():
    truths = Counter(k for d in cases.ALL for k in d["truth"])
    assert set(truths) == set(lx.KIND_IDS) and min(truths.values()) >= 2
    assert {f for d in cases.ALL for f in d["features"].values()} == set(lx.FT_IDS)
    assert {d["keepsake"][1] for d in cases.ALL if d["keepsake"]} == set(lx.KS_IDS)
    assert sum(1 for d in cases.ALL if len(d["truth"]) == 2) == 10
    assert {b for d in cases.ALL for b, _r in d["accounts"]} >= {"tidy", "mover", "shy", "curious"}


def test_every_case_has_its_words():
    for d in cases.ALL:
        assert d["client"] and len(d["intro"]) > 60 and len(d["ending"]) > 60, d["id"]


def test_two_presences_chapter_gives_every_account_its_room_and_no_roamers():
    for cid in progress.CHAPTERS[2]["cases"] + [c for c in progress.CHAPTERS[4]["cases"] if len(progress.DATA[c]["truth"]) == 2]:
        d = progress.DATA[cid]
        assert all(r for _b, r in d["accounts"]) and all(len(s) == 1 for s in d["restless"])
        assert not any("roamer" in lx.KIND_BEHAVIOURS[k] for k in d["truth"])


def test_chapters_open_five_at_a_time_and_next_case_walks_on():
    best = {}
    assert progress.chapter_open(best, 0) and not progress.chapter_open(best, 1)
    for cid in progress.CHAPTERS[0]["cases"][:5]:
        best[cid] = 3
    assert progress.chapter_open(best, 1) and not progress.chapter_open(best, 2)
    assert progress.next_case(best, "1-1") == "1-6"
    assert progress.totals(best)["done"] == 5 and progress.totals(best)["clean"] == 5
    assert progress.next_case({}, "1-8") == "1-1"
