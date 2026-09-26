"""C21: the shadow grid (a non-interactive twin that copies your moves)."""


def test_off_by_default(game_env):
    m = game_env.module
    assert m.shadow_scenario is None and m.shadow_actions == []
    assert m.shadow_rows() is None
    m.render()
    assert game_env.elements["shadow-table"].children == []
    assert "Pick a starting scenario" in game_env.elements["shadow-verdict"].innerText


def test_default_twin_scenario_contrasts_with_the_current_one(game_env):
    m = game_env.module
    m.state.scenario = "standard"
    assert m.default_shadow_scenario() == "coal_legacy"
    m.state.scenario = "greenfield"
    assert m.default_shadow_scenario() == "standard"


def test_setting_and_clearing_the_scenario(game_env):
    m = game_env.module
    assert m.set_shadow_scenario("coal_legacy") is True and m.shadow_scenario == "coal_legacy"
    assert m.set_shadow_scenario(None) is True and m.shadow_scenario is None
    for bad in ("bogus", 3, ["standard"], ""):
        assert m.set_shadow_scenario(bad) is False


def test_actions_are_only_recorded_while_the_shadow_is_on(game_env):
    m = game_env.module
    m.state.funds = 10_000
    m._make_build_handler("solar")()
    assert m.shadow_actions == []
    m.set_shadow_scenario("coal_legacy")
    m._make_build_handler("solar")()
    assert [(a["kind"], a["type"], a["round"]) for a in m.shadow_actions] == [("build", "solar", 1)]


def test_failed_actions_are_not_recorded(game_env):
    m = game_env.module
    m.set_shadow_scenario("coal_legacy")
    m.state.funds = 0
    m._make_build_handler("nuclear")()
    assert m.shadow_actions == []


def test_retires_are_recorded(game_env):
    m = game_env.module
    m.set_shadow_scenario("standard")
    m.state.plant_counts["coal"] = 2
    m._make_retire_handler("coal")()
    assert any(a["kind"] == "retire" and a["type"] == "coal" for a in m.shadow_actions)


def test_the_twin_copies_your_moves_on_its_own_start(game_env):
    m = game_env.module
    m.set_shadow_scenario("coal_legacy")
    m.state.funds = 10_000
    m._make_build_handler("solar")()
    twin, skipped = m.replay_shadow()
    assert twin.plant_counts["solar"] == 1 and skipped == 0
    assert twin.plant_counts["coal"] == m.SCENARIOS["coal_legacy"]["plants"]["coal"]  # its own starting fleet


def test_the_twin_advances_with_you(game_env):
    m = game_env.module
    m.set_shadow_scenario("standard")
    for _ in range(3):
        game_env.advance_round()
    twin, _ = m.replay_shadow()
    assert twin.round_number == m.state.round_number


def test_replay_is_deterministic(game_env):
    m = game_env.module
    m.set_shadow_scenario("coal_legacy")
    m.state.funds = 10_000
    m._make_build_handler("wind")()
    for _ in range(4):
        m.on_advance_round()
    a, _ = m.replay_shadow()
    b, _ = m.replay_shadow()
    assert (a.funds, a.score(), a.plant_counts) == (b.funds, b.score(), b.plant_counts)


def test_unaffordable_mirrored_moves_are_skipped_and_counted(game_env):
    m = game_env.module
    m.set_shadow_scenario("coal_legacy")  # starts with less money than standard
    m.state.funds = 10_000
    for _ in range(5):
        m._make_build_handler("nuclear")()
    _twin, skipped = m.replay_shadow()
    assert skipped >= 1
    rows, verdict = m.shadow_rows()
    assert "could not afford" in verdict


def test_the_shadow_never_changes_your_grid(game_env):
    m = game_env.module
    m.set_shadow_scenario("greenfield")
    m.state.funds = 10_000
    m._make_build_handler("solar")()
    before = (m.state.funds, dict(m.state.plant_counts), m.state.round_number)
    m.replay_shadow()
    m.render()
    assert (m.state.funds, dict(m.state.plant_counts), m.state.round_number) == before


def test_render_shows_a_table_and_a_verdict(game_env):
    m = game_env.module
    m.set_shadow_scenario("coal_legacy")
    m.render()
    table = game_env.elements["shadow-table"]
    assert len(table.children) == 5  # header + four metrics
    assert "Twin (Coal-heavy legacy grid)" in table.children[0].children[2].innerText
    assert game_env.elements["shadow-verdict"].innerText


def test_selector_turns_it_on_and_off(game_env):
    m = game_env.module
    game_env.elements["shadow-select"].value = "greenfield"
    game_env.elements["shadow-select"].dispatch("change", None)
    assert m.shadow_scenario == "greenfield"
    game_env.elements["shadow-select"].value = "off"
    game_env.elements["shadow-select"].dispatch("change", None)
    assert m.shadow_scenario is None


def test_action_log_is_capped(game_env):
    m = game_env.module
    m.set_shadow_scenario("standard")
    m.state.funds = 10_000_000
    for _ in range(m.SHADOW_MAX_ACTIONS + 25):
        m.record_shadow_action("build", "solar")
    assert len(m.shadow_actions) == m.SHADOW_MAX_ACTIONS


def test_save_round_trip_and_default_omits_key(game_env):
    m = game_env.module
    assert "shadow" not in m.get_state()
    m.set_shadow_scenario("coal_legacy")
    m.state.funds = 10_000
    m._make_build_handler("wind")()
    data = m.get_state()
    assert data["shadow"]["scenario"] == "coal_legacy" and len(data["shadow"]["actions"]) == 1
    m.set_shadow_scenario(None)
    m.shadow_actions.clear()
    m.load_state(data)
    assert m.shadow_scenario == "coal_legacy" and m.shadow_actions[0]["type"] == "wind"


def test_load_rejects_bad_values(game_env):
    m = game_env.module
    base = m.get_state()
    for bad in ("x", [1], None, {"scenario": "bogus"}, {"scenario": 3}, {"actions": []}):
        data = dict(base)
        data["shadow"] = bad
        m.load_state(data)
        assert m.shadow_scenario is None and m.shadow_actions == []
    data = dict(base)
    data["shadow"] = {"scenario": "standard", "actions": [
        {"round": 1, "kind": "build", "type": "solar"}, {"round": 0, "kind": "build", "type": "solar"},
        {"round": "2", "kind": "build", "type": "solar"}, {"round": 2, "kind": "sell", "type": "solar"},
        {"round": 2, "kind": "build", "type": "bogus"}, "junk", None, {"round": True, "kind": "build", "type": "solar"},
    ]}
    m.load_state(data)
    assert m.shadow_actions == [{"round": 1, "kind": "build", "type": "solar"}]
