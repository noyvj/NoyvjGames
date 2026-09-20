"""Round-2 per-game Tide items (planning/TODO.md D2/D6/D10/D14/D16/D18/
D19/D20/D22/D23/D24/D26/D28/D30)."""


def _play(env, n):
    for _ in range(n):
        env.advance_season()


def test_seasons_survived_counter(game_env):
    el = game_env.elements["seasons-survived-display"]
    assert el.innerText == "Seasons survived: 0"
    _play(game_env, 3)
    assert el.innerText == "Seasons survived: 3"


def test_worst_season_names_cause(game_env):
    _play(game_env, 2)
    assert "no adaptation" in game_env.elements["worst-season-display"].innerText
    st = game_env.state
    st.funds = 1000
    for _ in range(3):
        game_env.invest("adaptation")
    st.damage_log[0] = 0.1  # make later season the worst
    game_env.advance_season()
    text = game_env.elements["worst-season-display"].innerText
    assert "Sandbag berms" in text or "no adaptation" in text


def test_worst_season_cause_none_for_old_save(game_env):
    game_env.state.damage_log = [5.0, 5.0]
    assert game_env.state.worst_season_cause() is None


def test_warning_banner_suggests_action(game_env):
    st = game_env.state
    st.acidity_history = [40.0, 40.0]
    st.fish_yield_history = [1.0]
    game_env.module.render()
    banner = game_env.elements["fish-warning-banner"]
    assert not banner.hidden
    assert "Acidity Reduction" in banner.innerText


def test_tile_tooltip_states_seasons_remaining(game_env):
    game_env.module.render()
    tiles = game_env.elements["coastline-grid"].children
    bottom = tiles[-1]
    assert "season(s) at the current pace" in bottom.title


def test_seasons_until_flood_uses_scenario_pace(game_env):
    st = game_env.state
    row = game_env.module.COASTLINE_ROWS - 1
    moderate = st.seasons_until_flood(row)
    assert moderate == 3
    st.set_sea_scenario("conservative")
    assert st.seasons_until_flood(row) == 4
    st.set_sea_scenario("severe")
    assert st.seasons_until_flood(row) == 3


def test_sea_scenario_locks_after_play(game_env):
    st = game_env.state
    assert st.set_sea_scenario("severe")
    game_env.advance_season()
    assert st.sea_level == 6.5
    assert not st.set_sea_scenario("conservative")
    assert st.sea_scenario == "severe"
    assert game_env.elements["sea-scenario-select"].disabled


def test_sea_scenario_invalid_ignored(game_env):
    assert not game_env.state.set_sea_scenario("nonsense")


def test_scenario_select_change_event(game_env):
    sel = game_env.elements["sea-scenario-select"]
    sel.value = "conservative"

    class E:
        target = sel

    sel.dispatch("change", E())
    assert game_env.state.sea_scenario == "conservative"


def test_graph_has_average_line_and_baseline_marker(game_env):
    game_env.state.capacity["output"] = 2
    _play(game_env, 3)
    svg = game_env.module.acidity_fish_history_svg()
    assert "stroke-dasharray" in svg and "Average acidity" in svg
    assert "Baseline set here" not in svg
    game_env.set_baseline()
    _play(game_env, 1)
    assert "Baseline set here" in game_env.module.acidity_fish_history_svg()


def test_then_vs_now_sparkline(game_env):
    assert game_env.module.then_vs_now_sparkline_svg() == ""
    _play(game_env, 3)
    assert "polyline" in game_env.module.then_vs_now_sparkline_svg()
    assert "polyline" in game_env.elements["then-vs-now-graph"].innerHTML


def test_hard_lag_note_fires_once(game_env):
    st = game_env.state
    game_env.toggle_hard_lag()
    assert any("takes effect" in m for m in st.ticker_log)
    n = len(st.ticker_full_history)
    game_env.toggle_hard_lag()
    game_env.toggle_hard_lag()
    assert len(st.ticker_full_history) == n


def test_hard_lag_toggle_has_tooltip_in_markup():
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text()
    assert "3 seasons to 6" in html


def test_output_mix_preview(game_env):
    st = game_env.state
    st.capacity["output"] = 2
    game_env.module.render()
    text = game_env.elements["output-mix-preview"].innerText
    assert "Fishing" in text and "Industry" in text
    income, acidity = st.output_mix_preview("industry")
    assert income == 12 and acidity == 2 * 2.0 * 1.4


def test_tier_badge_tracks_tier(game_env):
    assert game_env.elements["adaptation-tier-badge"].innerText == "⚪"
    game_env.state.funds = 1000
    for _ in range(3):
        game_env.invest("adaptation")
    assert game_env.elements["adaptation-tier-badge"].innerText != "⚪"


def test_seawall_tiles_carry_tier_class(game_env):
    game_env.state.funds = 1000
    for _ in range(6):
        game_env.invest("adaptation")
    tiles = game_env.elements["coastline-grid"].children
    assert "coastline-seawall--t2" in tiles[-1].className


def test_recovery_celebration(game_env):
    st = game_env.state
    st.fish_crash_open = True
    st.acidity_history = [0.0, 0.0, 0.0]
    st.season = 5
    st._record_recovery_message(0.95)
    assert st.recovery_celebrated_season == 5
    assert any("rebuilt" in m for m in st.ticker_log)
    assert not st.fish_crash_open
    game_env.module.render()
    assert not game_env.elements["fish-recovery-banner"].hidden
    st._record_recovery_message(0.95)  # no second celebration
    assert sum("rebuilt" in m for m in st.ticker_full_history) == 1


def test_no_recovery_without_prior_crash(game_env):
    st = game_env.state
    st._record_recovery_message(0.95)
    assert st.recovery_celebrated_season == 0


def test_crash_then_recovery_via_play(game_env):
    st = game_env.state
    st.acidity_history = [45.0] * 3
    st.acidity = 45.0
    st.fish_yield_history = [1.0]
    game_env.advance_season()  # fish yield now reflects ~45 acidity
    assert st.fish_crash_open
    st.acidity_history = [0.0] * 10
    game_env.advance_season()
    game_env.advance_season()
    assert st.recovery_celebrated_season > 0


def test_new_fields_round_trip_and_old_save_defaults(game_env):
    st = game_env.state
    st.set_sea_scenario("severe")
    game_env.advance_season()
    data = game_env.module.get_state()
    assert data["sea_scenario"] == "severe" and len(data["tier_log"]) == 1
    game_env.module.load_state({"season": 3})
    assert st.sea_scenario == "severe"  # untouched by an old payload
    game_env.module.load_state({"sea_scenario": "bogus", "tier_log": [99, "x", 1]})
    assert st.sea_scenario == "severe" and st.tier_log == [1]
