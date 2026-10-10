"""FS-17 to FS-22: the six exam formats (formats.py) and their panel, plus FS-23's default exam date."""

import random

import pytest


def _formats(game_env):
    return game_env.module.formats


def _norm(game_env):
    m = game_env.module
    return lambda text: m.normalize_answer(text, fold_accents=True)


# ---- engine ----

def test_every_format_has_a_ledger_mode_and_a_maker(game_env):
    f = _formats(game_env)
    assert set(f.FORMAT_ORDER) == set(f.FORMATS)
    for fid in f.FORMAT_ORDER:
        assert f.FORMATS[fid]["mode"] in game_env.module.PRACTICE_MODES
        q = f.make_question(fid, random.Random(1))
        assert q["format"] == fid and q["prompt"] and q["accepted"] and q["answer"]


def test_sessions_have_no_repeated_prompt_and_the_right_length(game_env):
    f = _formats(game_env)
    for fid in f.FORMAT_ORDER:
        session = f.make_session(fid, random.Random(3))
        assert 1 <= len(session) <= f.SESSION_LENGTH
        keys = [(q["prompt"], q.get("context", "")) for q in session]
        assert len(keys) == len(set(keys))


def test_the_bank_answers_pass_their_own_check_and_a_wrong_one_fails(game_env):
    f, norm = _formats(game_env), _norm(game_env)
    for fid in f.FORMAT_ORDER:
        for seed in range(40):
            q = f.make_question(fid, random.Random(seed))
            assert f.check(q, q["answer"], norm), (fid, q["prompt"], q["answer"])
            assert not f.check(q, "zzz qqq", norm)
            if not q["typed"]:
                assert q["answer"] in q["choices"] and len(set(q["choices"])) == len(q["choices"])


# ---- clock reading ----

@pytest.mark.parametrize("hour,minute,expected", [
    (3, 20, "il est trois heures vingt"),
    (3, 15, "il est trois heures et quart"),
    (3, 30, "il est trois heures et demie"),
    (3, 45, "il est quatre heures moins le quart"),
    (3, 40, "il est quatre heures moins vingt"),
    (3, 5, "il est trois heures cinq"),
    (1, 0, "il est une heure"),
    (13, 0, "il est une heure"),
    (12, 0, "il est midi"),
    (0, 0, "il est minuit"),
    (12, 30, "il est midi et demi"),
    (0, 30, "il est minuit et demi"),
    (11, 45, "il est midi moins le quart"),
    (23, 50, "il est minuit moins dix"),
])
def test_clock_forms(game_env, hour, minute, expected):
    f, norm = _formats(game_env), _norm(game_env)
    forms = [norm(x) for x in f.accepted_clock_forms(hour, minute)]
    assert norm(expected) in forms


def test_both_ways_of_saying_a_quarter_to_are_accepted(game_env):
    f, norm = _formats(game_env), _norm(game_env)
    forms = [norm(x) for x in f.accepted_clock_forms(3, 45)]
    assert norm("trois heures quarante-cinq") in forms and norm("quatre heures moins le quart") in forms


def test_the_clock_svg_is_valid_and_hands_follow_the_time(game_env):
    import xml.etree.ElementTree as ET
    f = _formats(game_env)
    a, b = f.clock_svg(3, 0), f.clock_svg(9, 30)
    ET.fromstring(a)
    ET.fromstring(b)
    assert a != b and a.count("<line") == 14  # 12 ticks and two hands


# ---- the panel ----

def test_opening_shows_the_picker_and_picking_starts_a_session(game_env):
    m = game_env.module
    game_env.elements["formats-button"].dispatch("click", None)
    assert game_env.elements["formats-panel"].hidden is False
    assert len(game_env.elements["formats-picker"].children) == 6
    assert "Pick a format" in game_env.elements["formats-progress"].innerText
    game_env.elements["formats-pick-reciprocal"].dispatch("click", None)
    assert m.formats_format == "reciprocal" and len(m.formats_queue) > 0
    assert game_env.elements["formats-card"].hidden is False
    assert game_env.elements["formats-typed-row"].hidden is True
    assert len(game_env.elements["formats-choices"].children) == 4


def test_a_right_answer_counts_to_that_formats_own_ledger_entry(game_env):
    m = game_env.module
    m.start_formats("pairq")
    q = m.formats_queue[0]
    before = m.practice_ledger["pairq"]["total"]
    assert m.submit_formats_answer(q["answer"]) is True
    assert m.practice_ledger["pairq"]["total"] == before + 1 and m.practice_ledger["pairq"]["correct"] >= 1
    assert m.practice_ledger["clock"]["total"] == 0  # only its own mode
    assert "Yes." in game_env.elements["formats-feedback"].innerText
    assert game_env.elements["formats-next-button"].hidden is False
    assert m.submit_formats_answer("again") is None  # already answered


def test_a_wrong_answer_shows_the_right_one_and_still_counts_to_accuracy(game_env):
    m = game_env.module
    m.start_formats("truefalse")
    q = m.formats_queue[0]
    wrong = "Faux" if q["answer"] == "Vrai" else "Vrai"
    assert m.submit_formats_answer(wrong) is False
    assert "Not quite" in game_env.elements["formats-feedback"].innerText
    assert m.practice_ledger["truefalse"]["total"] == 1 and m.practice_ledger["truefalse"]["correct"] == 0


def test_typed_formats_need_text_and_enter_submits(game_env):
    m = game_env.module
    m.start_formats("pronoun")
    assert game_env.elements["formats-typed-row"].hidden is False
    assert m.submit_formats_answer("   ") is None
    q = m.formats_queue[0]
    game_env.elements["formats-input"].value = q["answer"]
    m.on_formats_keydown(type("E", (), {"key": "Enter"})())
    assert m.formats_result is True


def test_a_session_walks_to_a_summary_and_never_touches_srs(game_env):
    m = game_env.module
    snapshot = [(p.plot_id, p.stage, p.interval_days, p.next_due, p.last_reviewed) for p in m.state.plots]
    m.start_formats("rewrite")
    total = len(m.formats_queue)
    for _ in range(total):
        m.submit_formats_answer(m.formats_queue[m.formats_index]["answer"])
        m.next_formats_question()
    assert game_env.elements["formats-summary"].hidden is False
    assert f"{total}/{total} right" in game_env.elements["formats-summary"].innerText
    assert snapshot == [(p.plot_id, p.stage, p.interval_days, p.next_due, p.last_reviewed) for p in m.state.plots]
    m.close_formats()
    assert game_env.elements["formats-panel"].hidden is True


def test_the_marker_says_it_does_not_grow_plots(game_env):
    m = game_env.module
    assert m.growth_marker("formats")[0] == "none"
    m.render()
    assert game_env.elements["growth-marker-formats"].innerText == "Does not grow plots"


# ---- FS-23 ----

def test_the_default_exam_date_is_a_one_click_offer_and_never_set_silently(game_env):
    m = game_env.module
    m._today_override = "2026-10-10"
    assert m.exam_date is None
    m.planner_open = True
    m.render()
    button = game_env.elements["planner-default-button"]
    assert button.hidden is False and "13 Nov 2026" in button.innerText
    assert m.exam_date is None
    button.dispatch("click", None)
    assert m.exam_date == "2026-11-13" == m.EXAM_DEFAULT_DATE
    m.render()
    assert game_env.elements["planner-default-button"].hidden is True
    assert m.exam_days_left() == 34
