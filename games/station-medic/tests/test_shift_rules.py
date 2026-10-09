"""The rules in shift.py, one at a time, on small hand-made cases."""

import shift
from casekit import P, S
from shift import Case


def make(**kw):
    base = dict(sid="t", title="t", intro="t", pool="coil ember", stock={"gel": 2, "tonic": 2, "cells": 2},
                patients=[P("teo", "ember", "x")], tests="lamp")
    base.update(kw)
    return Case(S(**base))


def run(case, *acts):
    st = case.new_state()
    infos = []
    for act in acts:
        st2, info = case.apply(st, act)
        if st2 is not None:
            st = st2
        infos.append(info)
    return st, infos


def test_a_scan_uses_a_supply_and_reads_the_truth():
    c = make()
    st, (info,) = run(c, ("scan", 0, 0))
    assert info["ok"] and info["positive"] and st[0][c.item_ix["cells"]] == 1
    assert st[1][0][shift.READ] == (1,)
    assert c.candidates(0, st[1][0][shift.READ]) == [(1,)]


def test_a_cure_settles_the_patient_with_no_cost():
    c = make()
    st, infos = run(c, ("scan", 0, 0), ("treat", 0, c.tx.index("tonic")))
    assert infos[1]["kind"] == "cure" and c.done(st) and c.total_cost(st) == 0


def test_a_repeat_scan_and_a_missing_supply_are_refused_without_cost():
    c = make(stock={"gel": 1, "tonic": 1, "cells": 1})
    st, infos = run(c, ("scan", 0, 0), ("scan", 0, 0))
    assert not infos[1]["ok"] and c.total_cost(st) == 0
    c2 = make(stock={"gel": 1, "tonic": 1, "cells": 0})
    _st, (info,) = run(c2, ("scan", 0, 0))
    assert not info["ok"] and "No lamp cells" in info["msg"]


def test_a_treatment_that_does_nothing_costs_one_and_the_patient_stays():
    c = make()
    st, (info,) = run(c, ("treat", 0, c.tx.index("gel")))
    assert info["kind"] == "ease" or info["kind"] == "waste"
    # gel is the ease for Ember Fever: it settles with a cost
    assert info["kind"] == "ease" and c.total_cost(st) == 1 and c.done(st)
    c2 = make(pool="coil ember", patients=[P("teo", "coil", "x")], stock={"gel": 1, "tonic": 1, "cells": 1})
    st2, (info2,) = run(c2, ("treat", 0, c2.tx.index("tonic")))
    assert info2["kind"] == "waste" and not c2.done(st2) and c2.total_cost(st2) == 1


def test_a_chart_note_makes_a_forbidden_treatment_a_reaction():
    c = make(patients=[P("teo", "ember", "x", traits="cold")], stock={"salve": 1, "tonic": 1, "cells": 1})
    st, (info,) = run(c, ("treat", 0, c.tx.index("salve")))
    assert info["kind"] == "reaction" and c.total_cost(st) == 2 and c.done(st)


def test_two_heavy_treatments_clash():
    c = make(pool="vent brass", patients=[P("teo", "vent brass", "x")], maxc=2, stock={"tonic": 2, "gel": 1, "loz": 1, "drip": 1})
    # vent cures: loz, gel; brass cures: drip, gel -- tonic cures neither, so it wastes; then a second heavy clashes
    st, infos = run(c, ("treat", 0, c.tx.index("tonic")), ("treat", 0, c.tx.index("tonic")))
    assert infos[0]["kind"] == "waste" and infos[1]["kind"] == "clash" and c.total_cost(st) == 3


def test_a_shaking_patient_must_be_steadied_first():
    c = make(pool="saltt loose", patients=[P("teo", "saltt", "x")], stock={"band": 1, "tonic": 1, "gel": 1, "cells": 1}, robots=0)
    st, infos = run(c, ("scan", 0, 0), ("band", 0), ("scan", 0, 0))
    assert not infos[0]["ok"] and "shaking" in infos[0]["msg"] and infos[1]["ok"] and infos[2]["ok"]
    assert st[1][0][shift.STEADY] == 1 and st[0][c.item_ix["band"]] == 0
    st, infos = run(c, ("band", 0), ("band", 0))
    assert not infos[1]["ok"]


def test_tally_steadies_one_patient_for_free():
    c = make(pool="saltt loose", patients=[P("teo", "saltt", "x"), P("kit", "loose", "y")], stock={"band": 0, "tonic": 1, "gel": 1, "cells": 1}, robots=1)
    st, infos = run(c, ("robot", 0), ("robot", 1), ("band", 1))
    assert infos[0]["ok"] and not infos[1]["ok"] and not infos[2]["ok"]


def test_handling_a_contagious_patient_in_the_ward_costs_once_and_the_cold_room_prevents_it():
    c = make(pool="spore soot", patients=[P("teo", "spore", "x")], stock={"vials": 1, "dye": 0, "loz": 1, "gel": 1, "roll": 1}, tests="breath dye", beds=1)
    st, infos = run(c, ("scan", 0, 0), ("scan", 0, 1))
    assert c.total_cost(st) == 2 and "needs airing" in infos[0]["msg"] and "needs airing" not in infos[1]["msg"]
    st, infos = run(c, ("isolate", 0), ("scan", 0, 0), ("scan", 0, 1))
    assert c.total_cost(st) == 0 and infos[0]["ok"]


def test_the_cold_room_has_a_limited_number_of_beds_and_frees_when_the_patient_is_settled():
    c = make(pool="spore soot", patients=[P("teo", "soot", "x"), P("kit", "spore", "y")], stock={"loz": 2, "gel": 1, "tonic": 1, "patch": 0, "roll": 1}, beds=1)
    st, infos = run(c, ("isolate", 0), ("isolate", 1))
    assert infos[0]["ok"] and not infos[1]["ok"] and "taken" in infos[1]["msg"]
    st, infos = run(c, ("isolate", 0), ("release", 0), ("isolate", 1))
    assert all(i["ok"] for i in infos)
    c0 = make()
    _st, (info,) = run(c0, ("isolate", 0))
    assert not info["ok"] and "no cold room" in info["msg"]


def test_comfort_and_borrow_are_always_available_and_cost_one_each():
    c = make(stock={"gel": 0, "tonic": 0, "cells": 0})
    st, infos = run(c, ("borrow", c.item_ix["tonic"]), ("treat", 0, c.tx.index("tonic")))
    assert infos[0]["kind"] == "borrow" and infos[1]["kind"] == "cure" and c.total_cost(st) == 1
    st, infos = run(c, ("comfort", 0))
    assert c.done(st) and c.total_cost(st) == 1
    assert not run(c, ("comfort", 0), ("comfort", 0))[1][1]["ok"]


def test_a_two_condition_patient_needs_both_cured():
    c = make(pool="vent brass", patients=[P("teo", "vent brass", "x")], maxc=2, stock={"loz": 1, "gel": 1, "drip": 1})
    st, infos = run(c, ("treat", 0, c.tx.index("loz")))
    assert infos[0]["kind"] == "partial" and not c.done(st)
    st, infos = run(c, ("treat", 0, c.tx.index("gel")))     # gel cures both vent and brass
    assert infos[0]["kind"] == "cure" and c.done(st)


def test_grades():
    assert [shift.grade_of(n) for n in (0, 1, 2, 3, 9)] == [3, 2, 2, 1, 1]


def test_tokens_round_trip_and_bad_tokens_are_rejected():
    for act in (("scan", 0, 1), ("treat", 2, 3), ("band", 1), ("robot", 0), ("isolate", 3), ("release", 0), ("comfort", 1), ("borrow", 4)):
        assert shift.from_token(shift.to_token(act)) == act
    for bad in (None, 3, "scan", "scan:1", "nope:1", "treat:a:1", "treat:-1:1", "treat:1:2:3", "scan:100:1"):
        assert shift.from_token(bad) is None
    c = make()
    assert shift.replay(c, ["scan:0:0", "treat:0:0"])[0] is not None
    assert shift.replay(c, ["scan:0:0", "scan:0:0"]) == (None, None)
    assert shift.replay(c, ["scan:9:0"]) == (None, None)
