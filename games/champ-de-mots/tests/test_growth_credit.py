"""Which activities grow plots (user request, 2026-10-08): the text marker on
every question panel, and the credit each crediting mode gives a plot through
the existing watering and nudge paths."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent

ACTIVITIES = (
    "practice", "review", "proficiency", "bonus", "builder", "conversation", "listening",
    "liaison", "placement", "blitz", "racer", "sprint", "boutique", "cafe",
    "pairs", "gaps", "listenpick", "wordorder",
)
GROWS = {
    "practice", "review", "proficiency", "placement", "blitz", "racer", "sprint", "boutique", "cafe",
    "pairs", "gaps", "listenpick", "wordorder",
}
NO_GROW = {"bonus", "builder", "conversation", "listening", "liaison"}


def _plot_snapshot(plot):
    return (plot.ease_factor, plot.interval_days, plot.last_reviewed, plot.next_due, plot.correct_streak, plot.stage)


def _watered(module, plot):
    module.state.review(plot.plot_id, True)
    module.state.advance_day(40)  # long overdue, so any credit will move it
    return plot


# --- markers ---------------------------------------------------------------------------


def test_every_question_activity_has_a_marker_in_both_pages_and_the_table():
    assert set(ACTIVITIES) == GROWS | NO_GROW
    for name in ("index.html", "pc.html"):
        html = (GAME_DIR / name).read_text(encoding="utf-8")
        for key in ACTIVITIES:
            assert f'id="growth-marker-{key}"' in html, (name, key)


def test_marker_text_says_grows_or_does_not_grow_and_says_how(game_env):
    module = game_env.module
    for key in ACTIVITIES:
        element = game_env.elements[f"growth-marker-{key}"]
        text = element.innerText
        assert text.startswith("Grows plots") or text == "Does not grow plots", (key, text)
        assert element.title and element.title in element.attributes["aria-label"]
        assert element.attributes["aria-label"].startswith(text)
        if key in NO_GROW:
            assert text == "Does not grow plots"
            assert "not plots" in element.title or "not tied to any plot" in element.title  # says why
            assert element.attributes["data-growth"] == "none"
        else:
            assert text.startswith("Grows plots")
    # 2026-10-08 watering rule: every plot-linked activity says the same thing.
    for key in ("practice", "review", "proficiency", "blitz", "racer", "sprint", "boutique", "cafe",
                "pairs", "gaps", "listenpick", "wordorder"):
        assert game_env.elements[f"growth-marker-{key}"].innerText == "Grows plots: waters, then nudges", key
        assert "first correct answer" in game_env.elements[f"growth-marker-{key}"].title
    assert "apply" in game_env.elements["growth-marker-placement"].innerText


def test_marker_is_a_text_and_shape_cue_not_colour_only():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    block = css[css.index(".growth-marker {"):]
    assert "border: 1px solid currentColor" in block  # a ring that follows the text
    assert '.growth-marker[data-growth="none"] { border-style: dashed; }' in block  # a different shape too


# --- Review and proficiency -------------------------------------------------------------


def test_review_credit_is_full_first_then_nudge_and_is_reported(game_env):
    module = game_env.module
    plot = module.state.plots[2]
    module.start_review("word")
    module.review_queue = [plot.plot_id, plot.plot_id]
    module.review_index = 0
    module._advance_review_question()
    answer = module.review_question["answer"] if module.review_question["mode"] == "choice" else None
    if answer is None:
        return
    module.submit_review_answer(answer)
    assert module.growth_credit["review"] == {"full": 1, "nudge": 0}
    assert plot.stage != module.STAGE_SEED
    module.next_review_question()
    answer = module.review_question["answer"] if module.review_question["mode"] == "choice" else None
    if answer is None:
        return
    module.submit_review_answer(answer)
    # The same plot answered again the same day is a nudge, but a plot counts once per session.
    assert module.growth_credit["review"] == {"full": 1, "nudge": 0}
    assert plot.interval_days == 2
    module.next_review_question()
    assert "Plot growth credited: watered 1 plot." in game_env.elements["review-summary"].innerText


def test_a_wrong_review_answer_credits_nothing(game_env):
    module = game_env.module
    module.start_review("word")
    question = module.review_question
    wrong = next((c for c in question["choices"] if c != question["answer"]), "zzzz") if question["mode"] == "choice" else "zzzz"
    plot = module.state.plots_by_id[question["plot_id"]]
    before = _plot_snapshot(plot)
    module.submit_review_answer(wrong)
    assert module.growth_credit["review"] == {"full": 0, "nudge": 0}
    assert _plot_snapshot(plot) == before


def test_proficiency_correct_answers_now_water_the_plot_and_say_so(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    entry = module.proficiency_questions[0]
    question = entry["question"]
    plot = module.state.plots_by_id[question["plot_id"]]
    assert plot.stage == module.STAGE_SEED and plot.last_reviewed is None
    answer = question["answer"]
    if question["mode"] == "typed":
        assert module.submit_proficiency_answer(answer) in (True, False)
    else:
        assert module.submit_proficiency_answer(answer) is True
    assert module.growth_credit["proficiency"]["full"] == 1
    assert plot.last_reviewed == module.state.current_day and plot.stage != module.STAGE_SEED
    # finish the test and read the credit line
    while module.proficiency_index < len(module.proficiency_questions):
        if module.proficiency_result is None:
            q = module.proficiency_questions[module.proficiency_index]["question"]
            module.submit_proficiency_answer(q["answer"])
        module.next_proficiency_question()
    text = game_env.elements["proficiency-summary"].innerText
    assert "Plot growth credited:" in text and "watered" in text


def test_proficiency_wrong_answer_leaves_the_plot_alone(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    question = module.proficiency_questions[0]["question"]
    plot = module.state.plots_by_id[question["plot_id"]]
    before = _plot_snapshot(plot)
    wrong = next((c for c in question["choices"] if c != question["answer"]), "zzzz") if question["mode"] == "choice" else "qqqqq"
    module.submit_proficiency_answer(wrong)
    assert _plot_snapshot(plot) == before
    assert module.growth_credit["proficiency"] == {"full": 0, "nudge": 0}


# --- arcade games: they water too (2026-10-08) --------------------------------------------------


def test_credit_game_plot_waters_first_then_nudges_once_per_day_and_never_lowers_a_stage(game_env):
    module = game_env.module
    plot = module.state.plots[4]
    assert plot.last_reviewed is None  # never watered: a game can now water it
    assert module.credit_game_plot(plot, "blitz") == "full"
    assert plot.stage == module.STAGE_SPROUT and plot.last_watered == module.state.current_day
    stage, streak, ease, interval = plot.stage, plot.correct_streak, plot.ease_factor, plot.interval_days
    assert module.credit_game_plot(plot, "blitz") == "nudge"  # same day: a nudge
    assert plot.interval_days == interval + module.REVIEW_NUDGE_DAYS
    assert (plot.stage, plot.correct_streak, plot.ease_factor) == (stage, streak, ease)
    assert module.credit_game_plot(plot, "blitz") is None  # at most one nudge per plot per day
    assert module.growth_credit["blitz"] == {"full": 1, "nudge": 0}  # a plot counts once per session
    module.state.advance_day(40)
    assert module.credit_game_plot(plot, "blitz") == "full"  # a new day waters again
    assert module.STAGE_RANK[plot.stage] >= module.STAGE_RANK[stage]


def _prep_plot_for_question(module, question):
    plot = module.state.plots_by_id[question["plot_id"]]
    _watered(module, plot)
    return plot


def test_blitz_correct_answer_waters_a_plot_that_was_never_watered_and_the_summary_says_so(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    question = mg.blitz_question
    plot = module.state.plots_by_id[question["plot_id"]]
    assert plot.stage == module.STAGE_SEED
    assert mg.submit_blitz_choice(question["answer"]) is True
    assert plot.stage == module.STAGE_SPROUT and plot.correct_streak == 1
    assert module.growth_credit["blitz"] == {"full": 1, "nudge": 0}
    mg._end_blitz(mg.BLITZ_END_TIME)
    mg.render()
    assert "Plot growth credited: watered 1 plot." in game_env.elements["blitz-summary"].innerText


def test_blitz_on_a_plot_already_watered_today_only_nudges(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    question = mg.blitz_question
    plot = module.state.plots_by_id[question["plot_id"]]
    module.water_plot(plot)  # the day's watering already happened
    interval, stage = plot.interval_days, plot.stage
    mg.submit_blitz_choice(question["answer"])
    assert plot.interval_days == interval + 1 and plot.stage == stage
    assert module.growth_credit["blitz"] == {"full": 0, "nudge": 1}
    mg._end_blitz(mg.BLITZ_END_TIME)
    mg.render()
    assert "Plot growth credited: nudged 1 plot." in game_env.elements["blitz-summary"].innerText


def test_blitz_wrong_answer_credits_nothing(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    question = mg.blitz_question
    plot = module.state.plots_by_id[question["plot_id"]]
    before = _plot_snapshot(plot)
    wrong = next(c for c in question["choices"] if c != question["answer"])
    mg.submit_blitz_choice(wrong)
    assert _plot_snapshot(plot) == before
    assert module.growth_credit["blitz"] == {"full": 0, "nudge": 0}
    mg._end_blitz(mg.BLITZ_END_TIME)
    mg.render()
    assert "Plot growth credited: none this session." in game_env.elements["blitz-summary"].innerText


def test_starting_a_new_run_resets_that_games_credit(game_env):
    module = game_env.module
    mg = module.minigames
    module.growth_credit["blitz"]["nudge"] = 3
    mg.start_blitz()
    assert module.growth_credit["blitz"] == {"full": 0, "nudge": 0}


def test_racer_correct_answer_waters(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_racer()
    question = mg.racer_question
    plot = module.state.plots_by_id[question["plot_id"]]
    mg.submit_racer_choice(question["answer"])
    assert plot.stage == module.STAGE_SPROUT
    assert module.growth_credit["racer"]["full"] == 1
    mg._end_racer(mg.RACER_END_PLAYER)
    mg.render()
    assert "Plot growth credited: watered 1 plot." in game_env.elements["racer-summary"].innerText


def test_sprint_correct_answer_waters(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_sprint()
    question = mg.sprint_question
    plot = module.state.plots_by_id[question["plot_id"]]
    mg.submit_sprint_choice(question["answer"])
    assert plot.stage == module.STAGE_SPROUT
    assert module.growth_credit["sprint"]["full"] == 1
    mg._end_sprint(mg.SPRINT_END_TIME)
    mg.render()
    assert "Plot growth credited: watered 1 plot." in game_env.elements["sprint-summary"].innerText


def test_boutique_correct_sale_waters_the_garment_and_colour_plots(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_boutique()
    order = mg.boutique_order
    garment_fr, colour_fr = order["credit_fr"]
    garment_plot = module._plot_by_fr()[" ".join(garment_fr.split()).lower()]
    colour_plot = module._plot_by_fr()[" ".join(colour_fr.split()).lower()]
    assert garment_plot is not colour_plot
    assert garment_plot.stage == colour_plot.stage == module.STAGE_SEED
    mg.submit_boutique_choice(order["answer"])
    assert garment_plot.stage == colour_plot.stage == module.STAGE_SPROUT
    assert module.growth_credit["boutique"]["full"] == 2
    # finish the shift for the summary
    while mg.boutique_active:
        mg.submit_boutique_choice(mg.boutique_order["answer"])
    mg.render()
    assert "Plot growth credited:" in game_env.elements["boutique-summary"].innerText


def test_boutique_missed_sale_credits_nothing(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_boutique()
    garment_fr, colour_fr = mg.boutique_order["credit_fr"]
    plot = module._plot_by_fr()[" ".join(garment_fr.split()).lower()]
    _watered(module, plot)
    before = _plot_snapshot(plot)
    wrong = next(c for c in mg.boutique_order["choices"] if c != mg.boutique_order["answer"])
    mg.submit_boutique_choice(wrong)
    assert _plot_snapshot(plot) == before
    assert module.growth_credit["boutique"] == {"full": 0, "nudge": 0}


def test_cafe_correct_order_waters_the_dish_plot_and_a_twist_waters_the_grammar_plot(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_cafe()
    order = mg.cafe_order
    dish_plot = module._plot_by_fr()[" ".join(order["credit_fr"][0].split()).lower()]
    assert dish_plot.stage == module.STAGE_SEED
    mg.submit_cafe_item_choice(order["answer"])
    assert dish_plot.stage == module.STAGE_SPROUT
    assert module.growth_credit["cafe"]["full"] == 1
    # run to the first twist round (every third customer)
    guard = 0
    while mg.cafe_active and not (mg.cafe_stage == mg.CAFE_STAGE_TWIST) and guard < 10:
        mg.submit_cafe_item_choice(mg.cafe_order["answer"])
        guard += 1
    assert mg.cafe_stage == mg.CAFE_STAGE_TWIST
    twist = mg.cafe_twist_question
    twist_plot = module.state.plots_by_id[twist["plot_id"]]
    before = module.growth_credit["cafe"]["full"]
    mg.submit_cafe_twist_choice(twist["answer"])
    assert twist_plot.stage == module.STAGE_SPROUT
    assert module.growth_credit["cafe"]["full"] == before + 1


def test_cafe_wrong_twist_gives_no_twist_credit(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_cafe()
    guard = 0
    while mg.cafe_active and mg.cafe_stage != mg.CAFE_STAGE_TWIST and guard < 10:
        mg.submit_cafe_item_choice(mg.cafe_order["answer"])
        guard += 1
    twist = mg.cafe_twist_question
    twist_plot = module.state.plots_by_id[twist["plot_id"]]
    _watered(module, twist_plot)
    before = _plot_snapshot(twist_plot)
    wrong = next(c for c in twist["choices"] if c != twist["answer"])
    mg.submit_cafe_twist_choice(wrong)
    assert _plot_snapshot(twist_plot) == before


def test_modes_that_do_not_grow_plots_never_touch_a_plot(game_env):
    module = game_env.module
    plot = module.state.plots[6]
    _watered(module, plot)
    before = [_plot_snapshot(p) for p in module.state.plots]
    module.start_liaison_drill()
    for _ in range(3):
        if module.liaison_questions and module.liaison_index < len(module.liaison_questions):
            module.submit_liaison_answer(module.liaison_questions[module.liaison_index]["answer"])
            module.next_liaison_question()
    module.start_sentence_builder()
    module.start_conversation()
    assert [_plot_snapshot(p) for p in module.state.plots] == before


def test_growth_credit_is_session_only_and_never_saved(game_env):
    module = game_env.module
    module.growth_credit["blitz"]["nudge"] = 5
    assert not any("growth" in key for key in module.get_state())


def test_growth_stage_never_goes_down_through_any_credit(game_env):
    module = game_env.module
    plot = _watered(module, module.state.plots[9])
    for _ in range(6):
        module.state.review(plot.plot_id, True)
    stage_rank = module.STAGE_RANK[plot.stage]
    module.state.advance_day(60)
    module.credit_game_plot(plot, "racer")
    module.credit_review_plot(plot, "review")
    assert module.STAGE_RANK[plot.stage] >= stage_rank


def test_changelog_mentions_the_markers():
    import json
    entries = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    entries = entries["changelog"] if isinstance(entries, dict) else entries
    assert any(re.search(r"grow plots", e.get("entry", ""), re.I) for e in entries)
