"""C29: the player's plant mix beside a real region's published generation mix."""


def _set_plants(m, counts):
    for plant_type in m.PLANT_TYPES:
        m.state.plant_counts[plant_type] = counts.get(plant_type, 0)


def test_off_by_default_and_prompts_for_a_choice(game_env):
    m = game_env.module
    assert m.real_grid_choice is None and m.real_grid_rows() is None
    m.render()
    assert "Pick a real region" in game_env.elements["real-grid-verdict"].innerText
    assert game_env.elements["real-grid-source"].hidden is True
    assert game_env.elements["real-grid-table"].children == []


def test_every_region_is_a_full_mix_with_a_source_and_year(game_env):
    m = game_env.module
    for key, region in m.REAL_GRIDS.items():
        assert region["label"] and region["source"] and 2000 < region["year"] < 2100, key
        assert set(region["shares"]) == set(m.GENERATION_TYPES) | {"other"}, key
        assert 96.0 <= sum(region["shares"].values()) <= 101.5, (key, sum(region["shares"].values()))
        assert all(v >= 0 for v in region["shares"].values())


def test_regions_carry_their_defining_facts(game_env):
    m = game_env.module
    assert m.REAL_GRIDS["fr"]["shares"]["nuclear"] > 60
    assert m.REAL_GRIDS["de"]["shares"]["nuclear"] == 0.0
    assert m.REAL_GRIDS["de"]["shares"]["wind"] > m.REAL_GRIDS["us"]["shares"]["wind"]
    assert m.REAL_GRIDS["us"]["shares"]["gas"] > m.REAL_GRIDS["us"]["shares"]["coal"]


def test_setting_and_clearing_and_rejecting_bad_values(game_env):
    m = game_env.module
    assert m.set_real_grid("us") is True and m.real_grid_choice == "us"
    for bad in ("nowhere", 3, ["us"], "", True):
        assert m.set_real_grid(bad) is False
    assert m.real_grid_choice == "us"
    assert m.set_real_grid(None) is True and m.real_grid_choice is None


def test_no_capacity_means_no_table_only_a_hint(game_env):
    m = game_env.module
    _set_plants(m, {})
    m.set_real_grid("us")
    assert m.real_grid_rows() is None
    m.render()
    assert "Build some generation" in game_env.elements["real-grid-verdict"].innerText


def test_rows_and_verdict_for_an_all_solar_grid_against_france(game_env):
    m = game_env.module
    _set_plants(m, {"solar": 4})
    m.set_real_grid("fr")
    rows, verdict = m.real_grid_rows()
    by_label = {r[0]: r for r in rows}
    assert by_label["Solar"][1] == "100%" and by_label["Solar"][2] == "2%"
    assert by_label["Clean total"][1] == "100%"
    assert "cleaner" in verdict and "France" in verdict and "2020" in verdict


def test_a_coal_grid_is_dirtier_than_germany(game_env):
    m = game_env.module
    _set_plants(m, {"coal": 3, "gas": 1})
    m.set_real_grid("de")
    rows, verdict = m.real_grid_rows()
    assert "dirtier" in verdict
    assert {r[0]: r for r in rows}["Clean total"][1] == "0%"


def test_equal_clean_share_reads_as_a_match(game_env):
    m = game_env.module
    _set_plants(m, {"wind": 1})
    m.set_real_grid("us")
    m.REAL_GRIDS["us"]["shares"] = dict(m.REAL_GRIDS["us"]["shares"], solar=100.0, wind=0.0, hydro=0.0, nuclear=0.0)
    _set_plants(m, {"solar": 1})
    rows, verdict = m.real_grid_rows()
    assert "matches" in verdict


def test_rendering_builds_a_header_and_a_row_per_type_plus_totals(game_env):
    m = game_env.module
    _set_plants(m, {"wind": 2, "gas": 1})
    game_env.elements["real-grid-select"].value = "us"
    game_env.elements["real-grid-select"].dispatch("change", None)
    table = game_env.elements["real-grid-table"]
    assert len(table.children) == 1 + len(m.GENERATION_TYPES) + 2  # header, types, other, clean total
    source = game_env.elements["real-grid-source"]
    assert source.hidden is False and "shares of generation" in source.innerText and "capacity" in source.innerText


def test_choice_saves_only_when_on_and_loads_validated(game_env):
    m = game_env.module
    assert "real_grid" not in m.get_state()
    m.set_real_grid("de")
    state = m.get_state()
    assert state["real_grid"] == "de"
    m.set_real_grid(None)
    m.load_state(state)
    assert m.real_grid_choice == "de"
    for bad in ("nowhere", 5, None, ["de"]):
        m.load_state({**state, "real_grid": bad})
        assert m.real_grid_choice is None
    m.load_state({k: v for k, v in state.items() if k != "real_grid"})
    assert m.real_grid_choice is None
