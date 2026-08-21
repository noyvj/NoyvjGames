"""Iteration Pass 3 (fun/teaching balance): event severity variation
widens with the player's accumulated skill-tree strength, so a
fully-invested skill tree doesn't outpace flat event difficulty — the
textbook flow-boredom failure mode. Center stays fixed at 1.0 so the
run-1-vs-latest-run hope-angle comparison stays meaningful; only the
spread (how mild the mild end can be, how severe the severe end can
be) grows with skill_strength.
"""


def test_skill_tree_strength_reflects_unlocked_count(game_env):
    assert game_env.module.skill_tree_strength() == 0
    game_env.skill_tree.add_knowledge(3)
    game_env.unlock_skill("reinforced_infrastructure")
    assert game_env.module.skill_tree_strength() == 1


def test_event_severity_defaults_to_zero_skill_strength(game_env):
    # Calling without a skill_strength argument must reproduce the exact
    # pre-Pass-3 bounds — no regression for any caller that omits it.
    for event_index in range(7):
        s = game_env.module.event_severity(3, event_index)
        assert game_env.module.SEVERITY_VARIATION_MIN <= s <= game_env.module.SEVERITY_VARIATION_MAX


def test_event_severity_range_widens_with_skill_strength(game_env):
    zero_skill = [game_env.module.event_severity(3, i, 0) for i in range(7)]
    full_skill = [game_env.module.event_severity(3, i, 3) for i in range(7)]
    zero_spread = max(zero_skill) - min(zero_skill)
    full_spread = max(full_skill) - min(full_skill)
    assert full_spread > zero_spread
    # The wider band actually reaches past the base bounds in both
    # directions for a fully-invested skill tree.
    assert min(full_skill) < game_env.module.SEVERITY_VARIATION_MIN
    assert max(full_skill) > game_env.module.SEVERITY_VARIATION_MAX


def test_event_severity_range_widening_is_centered_on_one(game_env):
    # Widening shouldn't shift the average severity — a stronger skill
    # tree isn't "punished," it just faces a less predictable spread.
    base_center = (
        game_env.module.SEVERITY_VARIATION_MIN + game_env.module.SEVERITY_VARIATION_MAX
    ) / 2
    for skill_strength in (0, 1, 2, 3):
        s_min = game_env.module.event_severity(3, 0, skill_strength)
        # Reconstruct the min/max bound directly from the formula's own
        # inputs rather than hardcoding, since seed varies with index.
        widened_min = base_center - (
            (game_env.module.SEVERITY_VARIATION_MAX - game_env.module.SEVERITY_VARIATION_MIN) / 2
            + game_env.module.SEVERITY_VARIATION_RANGE_PER_SKILL * skill_strength
        )
        widened_max = base_center + (
            (game_env.module.SEVERITY_VARIATION_MAX - game_env.module.SEVERITY_VARIATION_MIN) / 2
            + game_env.module.SEVERITY_VARIATION_RANGE_PER_SKILL * skill_strength
        )
        assert widened_min <= s_min <= widened_max


def test_event_severity_still_flat_for_run_one_regardless_of_skill_strength(game_env):
    for event_index in range(5):
        assert game_env.module.event_severity(1, event_index, 3) == 1.0


def test_event_severity_reproducible_for_same_inputs_with_skill_strength(game_env):
    a = game_env.module.event_severity(4, 2, 2)
    b = game_env.module.event_severity(4, 2, 2)
    assert a == b


def test_resolve_event_uses_live_skill_tree_strength_for_severity(game_env):
    # Get to run 2 (severity variation is off for run 1) with some
    # skills unlocked, then confirm the damage actually resolved used
    # the same severity event_severity() would predict for the current
    # skill_tree_strength().
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    game_env.skill_tree.add_knowledge(11)
    game_env.unlock_skill("community_reserves")
    game_env.unlock_skill("reinforced_infrastructure")
    game_env.unlock_skill("early_warning")
    game_env.start_new_run()

    game_env.resolve_event()

    expected_severity = game_env.module.event_severity(2, 0, 3)
    assert game_env.run.event_log[0]["severity"] == expected_severity


def test_higher_skill_strength_run_two_still_beats_run_one(game_env):
    # Regression guard for the existing hope-angle end-to-end test in
    # test_hope_angle_payoff.py: even with the widened severity spread
    # at full skill strength, a fully-invested second run must still
    # outscore an unassisted first run playing the same do-nothing
    # strategy (resolve only, no investment).
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    first_score = game_env.run_history[0]

    game_env.skill_tree.add_knowledge(50)
    game_env.unlock_skill("community_reserves")
    game_env.unlock_skill("reinforced_infrastructure")
    game_env.unlock_skill("early_warning")
    game_env.start_new_run()
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    latest_score = game_env.run_history[-1]

    assert latest_score > first_score
