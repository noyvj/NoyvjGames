"""B29: the guided, narrated example playthrough."""


def test_five_steps_with_titles_and_text(game_env):
    steps = game_env.module.example_playthrough()
    assert len(steps) == 5
    for title, text in steps:
        assert title and text


def test_numbers_are_computed_from_the_constants(game_env):
    m = game_env.module
    text = " ".join(t for _, t in m.example_playthrough())
    assert f"{m._example_growth(m.EXAMPLE_TICKS):.0f}" in text
    assert f"{m.DEGRADE_PER_CLEAR * 100:.0f}%" in text
    assert str(m.RECOVERY_TICKS) in text


def test_growth_is_faster_than_linear(game_env):
    m = game_env.module
    assert m._example_growth(40) > 2 * m._example_growth(20)


def test_each_clear_lowers_soil_productivity(game_env):
    m = game_env.module
    assert m._example_growth(10, clear_count=1) < m._example_growth(10)
    assert m._example_growth(10, clear_count=99) > 0  # floored, never zero


def test_balanced_run_beats_clear_happy_and_nearly_matches_never_clearing(game_env):
    m = game_env.module
    patient = m._example_growth(m.EXAMPLE_TICKS)
    quick, _ = m._example_clearing_plot_total(m.MATURITY_TICKS // 6, m.EXAMPLE_TICKS)
    harvested, _ = m._example_clearing_plot_total(m.MATURITY_TICKS, m.EXAMPLE_TICKS)
    kept = m.EXAMPLE_PLOTS - m.EXAMPLE_HARVESTED_PLOTS
    balanced = kept * patient + m.EXAMPLE_HARVESTED_PLOTS * harvested
    never = m.EXAMPLE_PLOTS * patient
    assert balanced > m.EXAMPLE_PLOTS * quick
    assert balanced >= 0.7 * never
    assert never > m.EXAMPLE_PLOTS * quick


def test_clearing_plot_total_respects_recovery_downtime(game_env):
    m = game_env.module
    total, clears = m._example_clearing_plot_total(10, 25)
    # 10 accruing + 10 replanting = 20 ticks per cycle, so one clear then 5 accruing ticks.
    assert clears == 1
    expected = m._example_growth(10, 0) + m._example_growth(5, 1)
    assert abs(total - expected) < 1e-9


def test_panel_toggles_and_renders_steps(game_env):
    m = game_env.module
    panel = game_env.elements["example-panel"]
    toggle = game_env.elements["example-toggle-button"]
    m.update_example_display()
    assert panel.hidden is True
    toggle.dispatch("click", None)
    assert panel.hidden is False
    assert "Hide" in toggle.innerText
    assert len(panel.children) == 6  # intro + five steps
    toggle.dispatch("click", None)
    assert panel.hidden is True


def test_reopening_does_not_duplicate_content(game_env):
    toggle = game_env.elements["example-toggle-button"]
    panel = game_env.elements["example-panel"]
    for _ in range(3):
        toggle.dispatch("click", None)
        toggle.dispatch("click", None)
    toggle.dispatch("click", None)
    assert len(panel.children) == 6


def test_example_never_touches_live_game_state(game_env):
    m = game_env.module
    before = (m.community_relations, [p.value for p in m.plots][:3])
    m.example_playthrough()
    assert (m.community_relations, [p.value for p in m.plots][:3]) == before
