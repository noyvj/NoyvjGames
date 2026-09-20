"""R2-L1b: every practice mode feeds one shared, capped practice-progress
ledger surfaced as the header's "Practice score" tile and a dashboard
section -- never SRS state."""

import json


def _srs_snapshot(state):
    return [
        (p.plot_id, p.stage, p.interval_days, p.next_due, p.last_reviewed, p.correct_streak, p.ease_factor)
        for p in state.plots
    ]


def test_fresh_ledger_is_empty_and_tile_shows_zero(game_env):
    module = game_env.module
    assert module.practice_score() == 0
    assert set(module.practice_ledger) == set(module.PRACTICE_MODES)
    module.render()
    assert game_env.elements["practice-score-display"].innerText == "Practice score: 0"


def test_correct_answer_earns_a_point_and_updates_tile(game_env):
    module = game_env.module
    assert module.record_practice("blitz", True) is True
    assert module.practice_ledger["blitz"]["correct"] == 1
    assert module.practice_score() == 1
    assert game_env.elements["practice-score-display"].innerText == "Practice score: 1"


def test_wrong_answer_counts_toward_accuracy_only(game_env):
    module = game_env.module
    assert module.record_practice("racer", False) is False
    entry = module.practice_ledger["racer"]
    assert (entry["correct"], entry["total"], entry["points"]) == (0, 1, 0)


def test_unknown_mode_is_ignored(game_env):
    assert game_env.module.record_practice("nope", True) is False
    assert game_env.module.practice_score() == 0


def test_daily_cap_then_resets_next_day(game_env):
    module, state = game_env.module, game_env.state
    for _ in range(module.PRACTICE_DAILY_CAP + 15):
        module.record_practice("cafe", True)
    assert module.practice_ledger["cafe"]["points"] == module.PRACTICE_DAILY_CAP
    assert module.practice_ledger["cafe"]["correct"] == module.PRACTICE_DAILY_CAP + 15
    state.advance_day(1)
    module.record_practice("cafe", True)
    assert module.practice_ledger["cafe"]["points"] == module.PRACTICE_DAILY_CAP + 1


def test_lifetime_cap_per_mode(game_env):
    module, state = game_env.module, game_env.state
    for _ in range(module.PRACTICE_MODE_CAP // module.PRACTICE_DAILY_CAP + 3):
        for _ in range(module.PRACTICE_DAILY_CAP + 2):
            module.record_practice("bonus", True)
        state.advance_day(1)
    assert module.practice_ledger["bonus"]["points"] == module.PRACTICE_MODE_CAP


def test_liaison_answers_feed_the_ledger(game_env):
    module = game_env.module
    module.start_liaison_drill()
    entry = module.liaison_questions[0]
    module.submit_liaison_answer(entry["answer"])
    assert module.practice_ledger["liaison"]["points"] == 1


def test_proficiency_answers_feed_the_ledger(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    entry = module.proficiency_questions[0]
    module.submit_proficiency_answer(entry["question"]["answer"])
    assert module.practice_ledger["proficiency"]["total"] == 1


def test_bonus_answers_feed_the_ledger(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    module.place_bonus_tile(0)
    while module.bonus_tile_pool:
        module.place_bonus_tile(0)
    assert module.practice_ledger["bonus"]["total"] == 1


def test_gender_drill_feeds_the_ledger_via_watering(game_env):
    module, state = game_env.module, game_env.state
    plot = next(
        p for p in state.plots
        if state.is_row_unlocked(p.sequence) and module.V_GENDER_TAG in module.variants_for(p)
    )
    module.open_practice(plot.plot_id, variant=module.V_GENDER_TAG)
    module.submit_answer(module.current_question["answer"])
    assert module.practice_ledger["gender"]["correct"] == 1


def test_blitz_and_racer_feed_the_ledger(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    mg.submit_blitz_choice(mg.blitz_question["answer"])
    assert module.practice_ledger["blitz"]["points"] == 1
    if mg.racer_available():
        mg.start_racer()
        mg.submit_racer_choice(mg.racer_question["answer"])
        assert module.practice_ledger["racer"]["points"] == 1


def test_shop_minigames_record_each_customer(game_env):
    module = game_env.module
    mg = module.minigames
    for name, resolve in (("boutique", mg._resolve_boutique_customer),):
        resolve(True)
        assert module.practice_ledger[name]["points"] == 1
        resolve(False)
        assert module.practice_ledger[name]["total"] == 2
    mg._resolve_cafe_customer(True, True)
    assert module.practice_ledger["cafe"]["points"] == 1


def test_practice_never_mutates_srs_state(game_env):
    module, state = game_env.module, game_env.state
    before = _srs_snapshot(state)
    module.start_liaison_drill()
    module.submit_liaison_answer(module.liaison_questions[0]["answer"])
    module.start_bonus_section(1)
    mg = module.minigames
    mg.start_blitz()
    mg.submit_blitz_choice(mg.blitz_question["answer"])
    assert _srs_snapshot(state) == before


def test_ledger_round_trips_through_save(game_env):
    module = game_env.module
    for _ in range(3):
        module.record_practice("blitz", True)
    module.record_practice("blitz", False)
    saved = json.loads(json.dumps(module.get_state()))
    assert list(saved["practice_ledger"]) == ["blitz"]
    module.practice_ledger = module._validated_practice_ledger({})
    module.load_state(saved)
    assert module.practice_ledger["blitz"]["correct"] == 3
    assert module.practice_ledger["blitz"]["total"] == 4
    assert module.practice_score() == 3


def test_load_state_defaults_missing_or_garbage_ledger(game_env):
    module = game_env.module
    module.record_practice("blitz", True)
    module.load_state({"version": 1, "current_day": 0, "plots": {}})
    assert module.practice_score() == 0
    for junk in ("x", 5, [1], {"blitz": "bad", "racer": {"correct": "9", "total": None}}):
        module.load_state({"version": 1, "current_day": 0, "plots": {}, "practice_ledger": junk})
        assert module.practice_score() == 0


def test_load_state_clamps_tampered_values(game_env):
    module = game_env.module
    bad = {"blitz": {"correct": 5, "total": 2, "points": 9999, "day": -50, "day_points": 999},
           "cafe": {"correct": True, "total": 10**12, "points": -3}}
    module.load_state({"version": 1, "current_day": 0, "plots": {}, "practice_ledger": bad})
    b = module.practice_ledger["blitz"]
    assert b["correct"] <= b["total"] == 2
    assert b["points"] <= b["correct"]
    assert b["day_points"] <= module.PRACTICE_DAILY_CAP
    c = module.practice_ledger["cafe"]
    assert c["correct"] == 0 and c["points"] == 0 and c["total"] <= module.PRACTICE_COUNT_LIMIT


def test_dashboard_lists_every_mode(game_env):
    module = game_env.module
    module.record_practice("liaison", True)
    module.dashboard_open = True
    module.render_dashboard()
    panel = game_env.elements["dashboard-panel"]

    def texts(el):
        out = [el.innerText]
        for c in el.children:
            out.extend(texts(c))
        return out

    joined = "\n".join(texts(panel))
    assert "Practice progress — 1 point" in joined
    assert "Liaison practice — 1 of 1 correct (100%)" in joined
    assert "Verb Racer — not played yet" in joined


def test_index_has_the_score_tile():
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    assert 'id="practice-score-display"' in html
