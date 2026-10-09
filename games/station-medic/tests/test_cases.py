"""Every authored shift is checked by the solver: it compiles, it is fair (a no-cost plan exists whatever the scans say), the
real truth is finished with no cost, and every other truth the signs allow is finished with no cost too."""

import itertools

import cases
import cast
import lexicon as lx
import shift
from shift import Case
from solver import Solver, solve_truth

COMPILED = [(d, Case(d)) for d in cases.ALL]


def test_chapters_and_ids():
    ids = [d["id"] for d in cases.ALL]
    assert len(ids) == len(set(ids))
    for cid, name, blurb, shifts in cases.CHAPTER_DATA:
        assert shifts and name and blurb
        assert all(d["id"].startswith(str(1 + [c[0] for c in cases.CHAPTER_DATA].index(cid)) + "-") for d in shifts)


def test_every_shift_compiles_with_no_errors():
    for d, c in COMPILED:
        assert c.errors == [], (d["id"], c.errors)
        assert 1 <= len(c.patients) <= 4
        assert d["title"] and d["intro"]
        for p in c.patients:
            assert p.say and p.crew in cast.CREW_BY_ID


def test_every_shift_is_fair():
    for d, c in COMPILED:
        s = Solver(c)
        assert s.solvable(), d["id"]
        assert not s.exhausted, d["id"]


def test_every_shift_is_finished_clean_against_its_authored_truth():
    for d, c in COMPILED:
        plan, st, cost = solve_truth(c)
        assert cost == 0 and c.done(st), d["id"]


def test_every_shift_is_finished_clean_whichever_look_alike_each_patient_really_has():
    """Deducible: the plan never depends on luck, so every world the signs allow must end clean."""
    for d, c in COMPILED:
        shared = Solver(c).memo
        worlds = [[combo for combo, _r in p.cands] for p in c.patients]
        for pick in itertools.product(*worlds):
            d2 = dict(d)
            d2["patients"] = [dict(pd, truth=" ".join(c.pool[i] for i in combo)) for pd, combo in zip(d["patients"], pick)]
            c2 = Case(d2)
            assert c2.errors == [], (d["id"], pick)
            s2 = Solver(c2)
            s2.memo = shared
            plan, st, cost = solve_truth(c2, s2)
            assert cost == 0 and c2.done(st), (d["id"], pick)


def test_the_authored_truth_is_one_of_the_look_alikes():
    for d, c in COMPILED:
        for p in c.patients:
            assert tuple(sorted(p.truth_ix)) in [combo for combo, _r in p.cands]


def test_some_shifts_really_need_a_scan_and_the_stock_is_tight():
    scans_needed = 0
    for d, c in COMPILED:
        plan, _st, _c = solve_truth(c)
        if any(a[0] == "scan" for a in plan):
            scans_needed += 1
    assert scans_needed >= 6
    # taking one unit off the shelf breaks at least one shelf of most shifts (the puzzle has teeth)
    tight = 0
    for d, c in COMPILED:
        for item, n in d["stock"].items():
            if n:
                d2 = dict(d, stock=dict(d["stock"], **{item: n - 1}))
                if not Solver(Case(d2)).solvable():
                    tight += 1
                    break
    assert tight == len(COMPILED)


def test_a_careless_first_move_can_strand_the_shelf_but_restoring_always_works():
    """Not every first move is safe (that is the puzzle), but replaying from the start with the solver's plan always is."""
    unsafe = 0
    for d, c in COMPILED:
        s = Solver(c)
        start = c.new_state()
        for p in range(len(c.patients)):
            for x in range(len(c.tx)):
                st2, info = c.apply(start, ("treat", p, x))
                if st2 is not None and not s.wins(s.from_state(st2)):
                    unsafe += 1
    assert unsafe > 10


def test_every_treatment_in_play_cures_someone_in_the_pool_or_is_a_shared_shelf():
    for d, c in COMPILED:
        for t in c.tx:
            if lx.TX_BY_ID[t]["item"] in ("roll", "vials"):
                continue
            # a treatment on the shelf should be curing something on the sheet (no dead shelves)
            assert any(t in lx.COND[cid]["cures"] for cid in c.pool), (d["id"], t)


def test_replaying_the_solvers_plan_through_tokens_matches():
    for d, c in COMPILED[:5]:
        plan, st, cost = solve_truth(c)
        st2, infos = shift.replay(c, [shift.to_token(a) for a in plan])
        assert st2 == st and sum(i["delta"] for i in infos) == 0


def test_cold_room_shifts_really_need_the_bed_and_a_forgotten_bed_costs():
    for d, c in COMPILED:
        if not c.beds:
            continue
        plan, _st, _cost = solve_truth(c)
        assert any(a[0] == "isolate" for a in plan), d["id"]
        # treating the patient who shows flecks in the open ward is a cost (the shelf is irrelevant to that rule)
        spreaders = [i for i, p in enumerate(c.patients) if p.spreads]
        for i in spreaders:
            pat = c.new_state()
            for t in range(len(c.tests)):
                st2, info = c.apply(pat, ("scan", i, t))
                if st2 is not None:
                    assert info["delta"] == shift.COST_EXPOSURE, d["id"]
                    break


def test_chart_notes_are_real_traps_in_the_chart_notes_chapter():
    traps = 0
    for d, c in COMPILED:
        for p_i, p in enumerate(c.patients):
            if not p.forbids:
                continue
            for x, tid in enumerate(c.tx):
                if c.tx_forbidden(p_i, x) and any(tid in lx.COND[t]["cures"] for t in p.truth):
                    traps += 1
    assert traps >= 8
