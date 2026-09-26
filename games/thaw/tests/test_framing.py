"""G29: the global-vs-regional framing toggle."""


def _toggle(env):
    env.elements["framing-toggle-button"].dispatch("click", None)


def test_default_is_regional(game_env):
    game_env.module.render()
    assert game_env.module.framing == "regional"
    assert "Your region's choices" in game_env.elements["framing-summary"].innerText
    assert "my region's choices" in game_env.elements["framing-toggle-button"].innerText


def test_toggle_switches_to_global_and_back(game_env):
    _toggle(game_env)
    assert game_env.module.framing == "global"
    assert "Global picture" in game_env.elements["framing-summary"].innerText
    assert "global aggregate" in game_env.elements["framing-toggle-button"].innerText
    _toggle(game_env)
    assert game_env.module.framing == "regional"


def test_regional_summary_reads_region_a_only(game_env):
    m = game_env.module
    m.region.temperature = 4.0
    m.region.counterfactual_temperature = 6.0
    m.region_b.temperature = 9.0
    text = m.framing_summary_text()
    assert "+4.0" in text and "2.0" in text and "+9.0" not in text


def test_global_summary_averages_regions_a_to_c(game_env):
    m = game_env.module
    m.region.temperature, m.region_b.temperature, m.region_c.temperature = 3.0, 6.0, 12.0
    m.region.counterfactual_temperature = 3.0
    m.region_b.counterfactual_temperature = 6.0
    m.region_c.counterfactual_temperature = 12.0
    m.framing = "global"
    text = m.framing_summary_text()
    assert "+7.0" in text
    assert "1 of 3 regions melting" in text


def test_global_summary_excludes_region_d(game_env):
    m = game_env.module
    m.region_d.temperature = 500.0
    m.framing = "global"
    assert "+500" not in m.framing_summary_text()


def test_framing_changes_no_mechanics(game_env):
    m = game_env.module
    before = (m.region.temperature, m.region.funds)
    _toggle(game_env)
    assert (m.region.temperature, m.region.funds) == before


def test_summary_tracks_a_round_in_both_framings(game_env):
    m = game_env.module
    game_env.advance_round()
    regional = game_env.elements["framing-summary"].innerText
    _toggle(game_env)
    assert game_env.elements["framing-summary"].innerText != regional
    game_env.advance_round()
    assert "average warming" in game_env.elements["framing-summary"].innerText
    assert m.framing == "global"


def test_save_round_trip(game_env):
    m = game_env.module
    _toggle(game_env)
    data = m.get_state()
    assert data["framing"] == "global"
    m.framing = "regional"
    m.load_state(data)
    assert m.framing == "global"
    assert "Global picture" in game_env.elements["framing-summary"].innerText


def test_default_framing_not_saved(game_env):
    assert "framing" not in game_env.module.get_state()


def test_load_rejects_bad_framing(game_env):
    m = game_env.module
    for bad in ("galactic", 3, None, ["global"], {"a": 1}):
        data = m.get_state()
        data["framing"] = bad
        m.framing = "global"
        m.load_state(data)
        assert m.framing == "regional"
