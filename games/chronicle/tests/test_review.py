"""Milestone 7 (part two), spaced review: facts return after growing gaps, time is a day counter, nothing is punished."""

import copy
import json
import re
from pathlib import Path

import pytest

import review as rv
from setdata import load_set_dict

from .conftest import strip_extras

GAME_DIR = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE = "presidents-sample"
LABELS = {"confidence": {k: k for k in ("documented", "disputed", "traditional-but-doubtful")}, "strength": {"direct": "direct", "contributing": "contributing"}}


def everything(sample):
    return {"learned": list(sample.events), "sorted": sample.myth_claim_ids(), "threads": sample.web_relation_ids(),
            "decided": {d["id"]: {"picked": d["chosen"]} for d in sample.decisions}}


def learn(p, sample, **extra):
    state = {"learned": list(sample.events)}
    state.update(extra)
    p.m.load_state({"sets": {SAMPLE: state}})


def review_view(p):
    p.call("mode", mode="review")
    return p.call("boot")["view"]["review"]


def answer(p, right=True):
    """Answer the question that is up: the right option, or a wrong one."""
    q = review_view(p)["question"]
    puz = rv.make_question(p.m.SETS[SAMPLE], p.m.S["sets"][SAMPLE], q["key"], q["asked"], p.m.REVIEW_LABELS)
    choice = puz["answer"] if right else [o["id"] for o in q["options"] if o["id"] != puz["answer"]][0]
    return q["key"], p.call("review_answer", key=q["key"], choice=choice)


def srs(p):
    return p.m.S["sets"][SAMPLE]["srs"]


# ---- the scheduler -------------------------------------------------------------------------------------------------

def test_the_ladder_is_one_three_seven_fourteen_thirty():
    assert rv.LADDER == (1, 3, 7, 14, 30)


def test_a_right_answer_climbs_a_rung_and_sets_the_next_gap():
    rec, day = rv.new_record(), 0
    due = []
    for _ in range(5):
        rec = rv.after_answer(rec, day, True)
        due.append(rec["due"] - day)
        day = rec["due"]
    assert due == [1, 3, 7, 14, 30] and rec["step"] == 5 and rv.is_settled(rec) and rec["right"] == rec["asked"] == 5
    rec = rv.after_answer(rec, day, True)           # past the top: the longest gap, no further climb that matters
    assert rec["due"] - day == 30 and rv.is_settled(rec)


def test_a_wrong_answer_returns_tomorrow_from_the_first_rung_and_never_removes_the_fact():
    rec = rv.new_record()
    for day in (0, 1, 4):
        rec = rv.after_answer(rec, day, True)
    assert rec["step"] == 3
    rec = rv.after_answer(rec, 11, False)
    assert rec["step"] == 0 and rec["due"] == 12 and rec["asked"] == 4 and rec["right"] == 3 and rec["last"] == 11
    assert not rv.is_settled(rec)


def test_the_schedule_never_reads_a_clock_or_a_random_state():
    for name in ("review.py", "decision.py", "account.py", "game.py"):
        source = (GAME_DIR / name).read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(random|time|datetime|calendar)\b", source, re.M), name
        assert not re.search(r"\b(time\.time|datetime\.|setTimeout|setInterval|Date\.now|new Date)\b", source), name
    assert "Date.now" not in (GAME_DIR / "app.js").read_text(encoding="utf-8")


def test_items_exist_only_for_what_the_player_has_learned(sample):
    empty = {"learned": set(), "sorted": set(), "threads": set(), "decided": {}}
    assert rv.all_keys(sample, empty) == []
    prog = {"learned": {"e-washington-oath", "c-bastille"}, "sorted": {"c-e-gettysburg-date"}, "threads": {"r-sumter-emancipation"}, "decided": {"d-sumter": {"picked": "supply"}}}
    assert rv.all_keys(sample, prog) == ["ev:e-washington-oath", "ev:c-bastille", "my:c-e-gettysburg-date", "ln:r-sumter-emancipation", "dc:d-sumter"]
    full = {k: (set(v) if isinstance(v, list) else v) for k, v in everything(sample).items()}
    keys = rv.all_keys(sample, full)
    assert len(keys) == len(sample.events) + len(sample.myth_claim_ids()) + len(sample.web_relation_ids()) + len(sample.decisions)
    assert keys[0].startswith("ev:") and len(set(keys)) == len(keys)


def test_ready_items_come_earliest_due_first_then_in_the_fixed_order(sample):
    prog = {k: (set(v) if isinstance(v, list) else v) for k, v in everything(sample).items()}
    keys = rv.all_keys(sample, prog)
    records = {keys[0]: dict(rv.new_record(), due=3), keys[1]: dict(rv.new_record(), due=1)}
    day0 = rv.due_keys(sample, prog, records, 0)
    assert day0[:2] == [keys[2], keys[3]] and keys[0] not in day0 and keys[1] not in day0       # new items are due at once; these two wait
    day1 = rv.due_keys(sample, prog, records, 1)
    assert day1[:2] == [keys[2], keys[3]] and day1[-1] == keys[1] and keys[0] not in day1       # earlier due leads among the waiting ones
    day3 = rv.due_keys(sample, prog, records, 3)
    assert day3[-2:] == [keys[1], keys[0]] and len(day3) == len(keys)


# ---- questions ------------------------------------------------------------------------------------------------------

def test_review_questions_are_pinned_by_a_fixture(sample):
    fixture = json.loads((FIXTURES / "review_questions_v1.json").read_text(encoding="utf-8"))
    assert fixture["seed_version"] == rv.SEED_VERSION and len(fixture["puzzles"]) == 3 * 34
    prog = {k: (set(v) if isinstance(v, list) else v) for k, v in everything(sample).items()}
    for code, want in fixture["puzzles"].items():
        key, _, asked = code.rpartition("#")
        q = rv.make_question(sample, prog, key, int(asked), LABELS)
        assert [o["id"] for o in q["options"]] == want["options"] and q["answer"] == want["answer"], code


def test_every_question_has_its_answer_among_fixed_options_built_from_the_set(sample):
    prog = {k: (set(v) if isinstance(v, list) else v) for k, v in everything(sample).items()}
    for key in rv.all_keys(sample, prog):
        for asked in range(4):
            q = rv.make_question(sample, prog, key, asked, LABELS)
            ids = [o["id"] for o in q["options"]]
            assert q["answer"] in ids and len(set(ids)) == len(ids) and 2 <= len(ids) <= 4
            assert all(o["label"].strip() for o in q["options"]) and q["prompt"].strip() and q["context"].strip()
            claim = rv.claim_for(sample, key)
            assert claim is not None and len(claim["sources"]) >= 3


def test_date_questions_use_only_dates_of_moments_the_player_has_learned(sample):
    prog = {"learned": {"e-washington-oath", "e-gettysburg", "e-kennedy", "e-fort-sumter", "c-apollo"}, "sorted": set(), "threads": set(), "decided": {}}
    q = rv.make_question(sample, prog, "ev:e-gettysburg", 0, LABELS)
    assert set(o["id"] for o in q["options"]) <= prog["learned"] and q["answer"] == "e-gettysburg"
    labels = [o["label"] for o in q["options"]]
    assert "19 November 1863" in labels and len(set(labels)) == 4
    few = {"learned": {"e-gettysburg", "e-kennedy"}, "sorted": set(), "threads": set(), "decided": {}}
    assert rv.make_question(sample, few, "ev:e-gettysburg", 0, LABELS) is None        # not enough other moments to ask fairly


def test_the_same_inputs_give_the_same_question_and_asking_again_varies_it(sample):
    prog = {k: (set(v) if isinstance(v, list) else v) for k, v in everything(sample).items()}
    a = rv.make_question(sample, prog, "ev:e-kennedy", 0, LABELS)
    assert a == rv.make_question(sample, prog, "ev:e-kennedy", 0, LABELS)
    assert len({tuple(o["id"] for o in rv.make_question(sample, prog, "ev:e-kennedy", n, LABELS)["options"]) for n in range(6)}) > 1


def test_unlearned_or_unknown_items_have_no_question(sample):
    empty = {"learned": set(), "sorted": set(), "threads": set(), "decided": {}}
    for key in ("ev:e-kennedy", "my:c-e-gettysburg-tradition", "ln:r-sumter-emancipation", "dc:d-sumter", "ev:zz", "zz:1", "nope"):
        assert rv.make_question(sample, empty, key, 0, LABELS) is None
    assert rv.claim_for(sample, "zz:1") is None


def test_a_decision_question_asks_what_they_chose_and_never_which_is_best(sample):
    prog = {"learned": set(sample.events), "sorted": set(), "threads": set(), "decided": {"d-sumter": {"picked": "withdraw"}}}
    q = rv.make_question(sample, prog, "dc:d-sumter", 0, LABELS)
    assert q["prompt"] == "What did Abraham Lincoln choose?" and q["answer"] == "supply" and len(q["options"]) == 3
    assert not re.search(r"\b(best|better|should|right choice)\b", q["prompt"].lower())


# ---- the engine -------------------------------------------------------------------------------------------------------

def test_review_is_always_available_and_says_so_when_nothing_is_learned(p):
    v = p.call("mode", mode="review")["view"]
    assert v["mode"] == "review" and v["modes"][5]["available"] is True
    r = v["review"]
    assert r["question"] is None and r["feedback"] is None and r["counts"]["total"] == 0 and r["day"] == 0
    assert "Nothing to review yet" in r["idle"] and len(r["explainer"]) == 4


def test_a_learned_fact_is_new_and_ready_straight_away(p, sample):
    learn(p, sample)
    r = review_view(p)
    assert r["counts"]["total"] == 21 and r["counts"]["ready"] == 21 and r["counts"]["later"] == 0 and r["counts"]["new"] == 21
    q = r["question"]
    assert q["new"] is True and q["asked"] == 0 and q["key"].startswith("ev:") and "answer" not in q
    assert "answer" not in json.dumps(r)


def test_a_right_answer_schedules_the_fact_for_tomorrow_then_it_returns_on_the_next_day(p, sample):
    learn(p, sample)
    key, r = answer(p, True)
    fb = r["view"]["review"]["feedback"]
    assert fb["right"] is True and "comes back tomorrow" in fb["message"] and fb["claim"] and len(fb["claim"]["sources"]) >= 3
    assert srs(p)[key] == {"step": 1, "due": 1, "last": 0, "asked": 1, "right": 1}
    assert r["new"] == ["first_recall"]
    p.call("review_next")
    assert review_view(p)["question"]["key"] != key
    p.call("review_day")
    ready = p.call("boot")["view"]["review"]
    assert ready["day"] == 1 and ready["counts"]["ready"] == 21
    assert review_view(p)["question"]["key"] != key               # the twenty new facts are ready too, and lead


def test_a_wrong_answer_is_gentle_and_the_fact_comes_back_tomorrow(p, sample):
    learn(p, sample)
    key, r = answer(p, False)
    fb = r["view"]["review"]["feedback"]
    assert fb["right"] is False and fb["answer_label"] and fb["choice_label"] != fb["answer_label"]
    assert "comes back tomorrow" in fb["message"] and "nothing is taken away" in fb["message"]
    assert srs(p)[key] == {"step": 0, "due": 1, "last": 0, "asked": 1, "right": 0}
    banned = r"\b(streak|overdue|missed|behind|expire[sd]?|penalt\w*|failed|lost|hurry|urgent|punish\w*|countdown|deadline)\b"
    assert not re.search(banned, json.dumps(r["view"]["review"]).lower().replace("no deadline", ""))


def test_answering_requires_the_current_question_and_a_listed_option(p, sample):
    learn(p, sample)
    q = review_view(p)["question"]
    assert p.call("review_answer", key="ev:nope", choice=q["options"][0]["id"])["ok"] is False
    assert p.call("review_answer", key=q["key"], choice="nope")["ok"] is False
    assert p.call("review_answer", key=q["key"], choice=None)["ok"] is False
    assert srs(p) == {}
    p.call("review_answer", key=q["key"], choice=q["options"][0]["id"])
    assert p.call("review_answer", key=q["key"], choice=q["options"][0]["id"])["ok"] is False        # press Next first
    assert len(srs(p)) == 1


def test_nothing_is_ready_after_the_last_one_and_the_page_says_why_without_pressure(p, sample):
    learn(p, sample, sorted=[], threads=[])
    n = review_view(p)["counts"]["total"]
    for _ in range(n):
        answer(p, True)
        p.call("review_next")
    r = review_view(p)
    assert r["question"] is None and r["counts"]["ready"] == 0 and r["counts"]["later"] == n
    assert "Nothing is ready on day 0" in r["idle"] and "nothing is lost while you are away" in r["idle"]
    p.call("review_day")
    assert review_view(p)["counts"]["ready"] == n


def test_five_right_answers_on_five_days_settle_every_fact_and_earn_long_memory(p, sample):
    learn(p, sample, sorted=[], threads=[])
    days = []
    for _ in range(5):
        while review_view(p)["question"] is not None:
            answer(p, True)
            p.call("review_next")
        days.append(p.m.S["day"])
        assert "long_memory" not in p.m.get_state()["achievements_earned"] or len(days) == 5
        while review_view(p)["question"] is None and len(days) < 5:
            p.call("review_day")
    assert days == [0, 1, 4, 11, 25]                        # gaps of 1, 3, 7 and 14 days between the five sittings
    assert all(rec["step"] == 5 and rv.is_settled(rec) for rec in srs(p).values()) and len(srs(p)) == 21
    assert "long_memory" in p.m.get_state()["achievements_earned"]
    assert review_view(p)["counts"]["settled"] == 21
    p.call("review_day")
    assert review_view(p)["question"] is None                 # the longest gap is 30 days


def test_time_moves_only_when_the_player_says_so(p, sample):
    learn(p, sample)
    assert p.m.S["day"] == 0
    for _ in range(3):
        p.call("boot"), p.call("info"), p.call("archive")
    answer(p, True)
    assert p.m.S["day"] == 0 and p.m.get_state()["day"] == 0
    assert p.call("review_day")["view"]["day"] == 1 and p.m.get_state()["day"] == 1
    p.m.S["day"] = rv.MAX_DAY
    assert p.call("review_day")["ok"] is False and p.m.S["day"] == rv.MAX_DAY


def test_a_day_passing_clears_pending_feedback_and_changes_nothing_else(p, sample):
    learn(p, sample)
    answer(p, True)
    before = copy.deepcopy(p.m.get_state()["sets"])
    r = p.call("review_day")
    assert r["view"]["review"]["feedback"] is None and p.m.get_state()["sets"] == before


def test_review_never_touches_the_archive_or_the_other_modes_progress(p, sample):
    learn(p, sample, sorted=sample.myth_claim_ids(), threads=sample.web_relation_ids())
    before = {k: copy.deepcopy(v) for k, v in p.m.S["sets"][SAMPLE].items() if k != "srs"}
    found = p.call("boot")["view"]["set"]["found"]
    for _ in range(6):
        answer(p, True)
        p.call("review_next")
    p.call("review_day")
    answer(p, False)
    after = {k: v for k, v in p.m.S["sets"][SAMPLE].items() if k != "srs"}
    assert after == before and p.call("boot")["view"]["set"]["found"] == found


def test_review_brings_back_myth_claims_links_and_choices_too(p, sample):
    learn(p, sample, sorted=["c-e-gettysburg-tradition"], threads=["r-sumter-emancipation"], decided={"d-sumter": {"picked": "supply"}})
    seen = {}
    for _ in range(40):
        q = review_view(p)["question"]
        if q is None:
            break
        seen[q["key"].split(":")[0]] = q
        answer(p, True)
        p.call("review_next")
    assert set(seen) == {"ev", "my", "ln", "dc"}
    assert seen["my"]["prompt"] == "How sure are the sources about this statement?" and len(seen["my"]["options"]) == 3
    assert seen["ln"]["context"] == "Confederate guns open fire on Fort Sumter led to Lincoln signs the Emancipation Proclamation." and len(seen["ln"]["options"]) == 2


def test_the_review_board_is_only_built_in_review_mode(p, sample):
    learn(p, sample)
    v = p.call("boot")["view"]
    assert v["review"] is None and v["mode"] == "timeline" and v["day"] == 0
    assert p.call("mode", mode="review")["view"]["review"] is not None


def test_review_works_for_a_set_without_the_other_mechanics(p, g, raw):
    raw.pop("chapters")
    strip_extras(raw)
    raw["meta"]["id"] = "plain"
    g.register_set(load_set_dict(raw))
    g.S["settings"]["set"] = "plain"
    g.S["session"] = None
    g._prog("plain")["learned"] |= set(g.SETS["plain"].events)
    assert p.call("mode", mode="review")["ok"] is True
    v = p.call("boot")["view"]["review"]
    assert v["counts"]["total"] == 21 and v["question"]["key"].startswith("ev:")


# ---- save and load ----------------------------------------------------------------------------------------------------

def test_the_schedule_and_the_day_round_trip(p, sample):
    learn(p, sample)
    answer(p, True)
    p.call("review_next")
    p.call("review_day")
    answer(p, False)
    state = copy.deepcopy(p.m.get_state())
    assert state["day"] == 1 and len(state["sets"][SAMPLE]["srs"]) == 2
    p.m.reset_engine()
    p.m.load_state(state)
    assert p.m.get_state()["sets"] == state["sets"] and p.m.S["day"] == 1
    assert p.m.get_state()["achievements_earned"] == state["achievements_earned"]


def test_loading_merges_the_schedule_and_time_never_runs_backwards(p, sample):
    learn(p, sample)
    p.m.S["day"] = 7
    p.m.load_state({"day": 3})
    assert p.m.S["day"] == 7
    p.m.load_state({"day": 12})
    assert p.m.S["day"] == 12
    good = {"step": 2, "due": 9, "last": 5, "asked": 3, "right": 2}
    p.m.load_state({"sets": {SAMPLE: {"srs": {"ev:e-kennedy": good}}}})
    p.m.load_state({"sets": {SAMPLE: {"srs": {"ev:e-kennedy": {"step": 0, "due": 1, "last": 1, "asked": 1, "right": 0}}}}})
    assert srs(p)["ev:e-kennedy"] == good                                   # the record with more history wins
    p.m.load_state({"sets": {SAMPLE: {"srs": {"ev:e-kennedy": {"step": 3, "due": 20, "last": 12, "asked": 4, "right": 3}}}}})
    assert srs(p)["ev:e-kennedy"]["asked"] == 4


@pytest.mark.parametrize("key,rec", [
    ("ev:zz", {"step": 1, "due": 1, "last": 0, "asked": 1, "right": 1}),                 # unknown item
    ("zz:e-kennedy", {"step": 1, "due": 1, "last": 0, "asked": 1, "right": 1}),          # unknown kind
    ("ev:e-kennedy", {"step": -1, "due": 1, "last": 0, "asked": 1, "right": 1}),
    ("ev:e-kennedy", {"step": True, "due": 1, "last": 0, "asked": 1, "right": 1}),
    ("ev:e-kennedy", {"step": 1, "due": "1", "last": 0, "asked": 1, "right": 1}),
    ("ev:e-kennedy", {"step": 1, "due": 10 ** 9, "last": 0, "asked": 1, "right": 1}),
    ("ev:e-kennedy", {"step": 1, "due": 1, "last": -3, "asked": 1, "right": 1}),
    ("ev:e-kennedy", {"step": 1, "due": 1, "last": 0, "asked": 1, "right": 2}),          # more right than asked
    ("ev:e-kennedy", {"step": 1, "due": 1, "last": 0, "asked": 1}),
    ("ev:e-kennedy", "x"),
])
def test_a_bad_saved_record_is_dropped(p, key, rec):
    p.m.load_state({"sets": {SAMPLE: {"srs": {key: rec}}}, "day": -5})
    assert srs(p) == {} and p.m.S["day"] == 0


def test_garbage_never_raises_in_the_review_fields(p, sample):
    learn(p, sample)
    for junk in ({"sets": {SAMPLE: {"srs": [1, 2]}}}, {"sets": {SAMPLE: {"srs": None}}}, {"day": 1.5}, {"day": "3"}, {"day": True}, {"day": None}):
        p.m.load_state(junk)
    assert p.m.S["day"] == 0 and srs(p) == {}


def test_an_older_save_without_review_fields_loads_with_everything_new(p, sample):
    p.m.load_state({"schema": 2, "sets": {SAMPLE: {"learned": list(sample.events), "solved": {}, "revealed": []}}, "viewed": []})
    r = review_view(p)
    assert p.m.S["day"] == 0 and r["counts"]["new"] == 21 and r["counts"]["ready"] == 21


# ---- wording: no guilt, no streak, no clock ----------------------------------------------------------------------------

def _string_literals(path):
    """Every string literal in a Python file that is not a docstring (so, what the code can show a player)."""
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            docs.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


def test_no_player_visible_review_text_uses_pressure_words():
    banned = re.compile(r"\b(streak|overdue|missed|falling behind|expired?|penalt\w*|punish\w*|hurry|urgent|countdown|don't lose|keep it alive)\b", re.I)
    for name in ("review.py", "game.py"):
        for s in _string_literals(GAME_DIR / name):
            assert not banned.search(s), (name, s)
    for name in ("index.html", "app.js"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert not banned.search(text), (name, banned.search(text).group(0))
    explainer = " ".join(__import__("game")._review_explainer())
    assert "no clock" in explainer and "moves only when you press Let a day pass" in explainer and "Answering never changes your archive" in explainer


def test_there_is_no_timer_or_animation_added_for_review():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"\b(setInterval|requestAnimationFrame)\b", app)
    review_css = css.split("/* Review: one question at a time")[1].split("@keyframes")[0]
    assert "animation" not in review_css and "transition" not in review_css
