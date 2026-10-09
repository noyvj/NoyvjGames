"""K-12: a generated map with biomes."""

import json

import consulting
import geography
import save
import sim

from .test_consulting import _fresh


# --- the generator --------------------------------------------------------------
def test_the_same_seed_always_gives_the_same_map():
    assert geography.generate(1234) == geography.generate(1234)
    assert geography.generate(1234) != geography.generate(1235)
    grid = geography.generate(77)
    assert len(grid) == geography.HEIGHT and all(len(row) == geography.WIDTH for row in grid)
    assert all(cell in (geography.PLAINS, *geography.BIOMES) for row in grid for cell in row)


def test_bad_seeds_give_no_map():
    for bad in (None, 0, -5, True, "7", 7.5, geography.SEED_MAX + 1, [1], float("nan")):
        assert geography.generate(bad) == []
        assert geography.clean_seed(bad) is None
    assert geography.generate(geography.SEED_MAX) != []
    assert geography.clean_seed(1) == 1


def test_all_four_biomes_turn_up_across_seeds():
    seen = set()
    for seed in range(1, 200):
        for biome, n in geography.counts(geography.generate(seed)).items():
            if n:
                seen.add(biome)
    assert seen == set(geography.BIOMES)


def test_levels_follow_cell_counts():
    assert [geography.level_of(n) for n in (0, 1, 3, 4, 7, 8, 35)] == [0, 1, 1, 2, 2, 3, 3]


def test_the_consulting_maps_are_the_ones_the_cases_are_named_for():
    smoke = geography.counts(geography.generate(geography.CASE_SEEDS["smokestack"]))
    suburbs = geography.counts(geography.generate(geography.CASE_SEEDS["sprawl"]))
    assert smoke["river"] > 0 and smoke["coast"] == 0
    assert suburbs["coast"] > 0 and suburbs["river"] == 0
    assert set(geography.CASE_SEEDS) == set(consulting.CASES)


# --- effects ------------------------------------------------------------------------
def test_no_map_leaves_effects_untouched_and_maps_do_not_mutate_the_input():
    effects = dict(sim.NEUTRAL_EFFECTS)
    assert geography.apply_effects(effects, None) is effects
    out = geography.apply_effects(effects, geography.CASE_SEEDS["smokestack"])
    assert out is not effects and effects == sim.NEUTRAL_EFFECTS
    assert out["canal_yield_bonus"] > 0 and out["regen_mult"] < 1.0 and out["materials_yield_mult"] > 1.0


def test_every_effect_key_is_a_real_one_and_every_biome_has_a_boon_and_a_price():
    for biome, deltas in geography.EFFECTS.items():
        assert all(key in sim.NEUTRAL_EFFECTS for key in deltas)
        assert any(v > 0 for v in deltas.values()) and any(v < 0 for v in deltas.values())
        assert geography.BLURB[biome]
    assert set(geography.EFFECT_TEXT) >= {k for d in geography.EFFECTS.values() for k in d}


def test_effects_are_small_and_bounded_even_for_the_most_extreme_map():
    worst = 0.0
    for seed in range(1, 400):
        deltas = geography.effect_deltas(geography.generate(seed))
        for key, value in deltas.items():
            if key.endswith("_mult"):
                worst = max(worst, abs(value))
    assert worst <= 0.25
    effects = geography.apply_effects(dict(sim.NEUTRAL_EFFECTS), 1)
    assert all(effects[k] >= 0.1 for k in effects if k.endswith("_mult"))


def test_descriptions_name_every_present_biome_boon_and_price():
    grid = geography.generate(geography.CASE_SEEDS["smokestack"])
    text = " ".join(geography.describe(grid))
    assert "River" in text and "Mountains" in text and "Coast" not in text
    assert "canal yield" in text and "land recovery" in text
    assert geography.describe([]) == []
    assert geography.summary_text([]) == "open land"


def test_the_map_svg_labels_every_cell_and_never_relies_on_colour():
    grid = geography.generate(3)
    svg = geography.map_svg(grid)
    assert svg.count("<rect") == geography.WIDTH * geography.HEIGHT
    assert "<title>River</title>" in svg and "~" in svg and "▲" in svg
    assert geography.map_svg([]) == ""


def test_terrain_cells_for_the_scene_cover_only_non_plains_in_unit_range():
    cells = geography.terrain_cells(geography.generate(3))
    assert cells and all(c["biome"] != geography.PLAINS for c in cells)
    assert all(-1.0 <= c["x"] <= 1.0 and -1.0 <= c["z"] <= 1.0 for c in cells)
    assert geography.terrain_cells([]) == []


def test_seed_storage_is_validated():
    ui = {}
    assert geography.set_seed(ui, 55) == 55 and geography.chosen_seed(ui) == 55
    assert geography.set_seed(ui, "x") is None and geography.KEY not in ui
    assert geography.chosen_seed({geography.KEY: "junk"}) is None
    assert geography.chosen_seed({geography.KEY: {"seed": [3]}}) is None
    assert geography.chosen_seed(None) is None
    assert geography.active_seed({geography.KEY: {"seed": 9}}, "smokestack") == geography.CASE_SEEDS["smokestack"]
    assert geography.active_seed({geography.KEY: {"seed": 9}}, "nope") == 9


# --- the consulting cases stay winnable on their inherited ground -----------------------
def _play(case_id, plan_buildings, allocation_changes, absolute=None):
    c = _fresh(case_id)
    s = c.state
    for role, value in (absolute or {}).items():
        s.allocation[role] = value
    for role, delta in allocation_changes.items():
        s.allocation[role] = s.allocation.get(role, 0) + delta
    seed = geography.CASE_SEEDS[case_id]
    entry = None
    for _ in range(consulting.SEASON_LIMIT):
        ef = geography.apply_effects(c.tree.effects(), seed)
        for b, cap in plan_buildings:
            while s.can_build(b) and s.buildings[b] < cap:
                if b == "hearth" and s.culture_capacity(ef) >= s.population:
                    break
                if b == "shelter" and s.housing_capacity(ef) >= s.population + 3:
                    break
                s.build(b)
        s.clamp_allocation()
        s.advance_season(ef)
        entry = consulting.step(c, ef)
        if entry["result"]:
            break
    return entry["result"]


def test_smokestack_is_still_winnable_on_its_river_valley():
    result = _play("smokestack", (("sanitation_works", 4), ("shelter", 99), ("hearth", 99)),
                   {"gatherers": 5, "keepers": 6}, {"factory_workers": 9})
    assert result == "turned_around"


def test_sprawl_is_still_winnable_on_its_coast():
    result = _play("sprawl", (("sanitation_works", 4), ("transit_hubs", 4), ("public_works", 5), ("shelter", 99), ("hearth", 99)),
                   {"gatherers": 3, "keepers": 5}, {"factory_workers": 9, "planners": 8})
    assert result == "turned_around"


# --- the game ---------------------------------------------------------------------------
def test_the_panel_draws_a_map_and_the_map_changes_the_season(game_env):
    module = game_env.module
    elements = game_env.elements
    base = module.current_effects()["canal_yield_bonus"]
    module.on_toggle_geography()
    assert "Open land" in elements["geography-seed"].innerText
    assert elements["geography-off-button"].disabled is True
    elements["geography-use-seed-button"].disabled = False
    elements["geography-seed-input"].value = "3"
    elements["geography-use-seed-button"].dispatch("click", None)
    assert geography.chosen_seed(module.campaign.ui) == 3
    assert "Seed 3" in elements["geography-seed"].innerText and "river 7" in elements["geography-seed"].innerText
    assert module.current_effects()["canal_yield_bonus"] > base
    assert elements["geography-map"].innerHTML.startswith("<svg")
    assert len(elements["geography-list"].children) >= 2
    elements["geography-off-button"].dispatch("click", None)
    assert geography.chosen_seed(module.campaign.ui) is None
    assert module.current_effects()["canal_yield_bonus"] == base


def test_a_bad_seed_is_refused_with_a_message(game_env):
    module = game_env.module
    elements = game_env.elements
    module.on_toggle_geography()
    for bad in ("", "abc", "0", "99999999999"):
        elements["geography-seed-input"].value = bad
        elements["geography-use-seed-button"].dispatch("click", None)
        assert geography.chosen_seed(module.campaign.ui) is None
        assert "whole number" in elements["geography-status"].innerText


def test_new_map_draws_a_valid_seed(game_env):
    module = game_env.module
    module.on_toggle_geography()
    game_env.elements["geography-new-button"].dispatch("click", None)
    seed = geography.chosen_seed(module.campaign.ui)
    assert seed is not None and geography.generate(seed)


def test_the_map_is_locked_after_the_first_season_and_in_a_look_back(game_env):
    module = game_env.module
    elements = game_env.elements
    module.on_toggle_geography()
    elements["geography-new-button"].dispatch("click", None)
    seed = geography.chosen_seed(module.campaign.ui)
    game_env.advance_season()
    assert elements["geography-new-button"].disabled is True and elements["geography-off-button"].disabled is True
    module.on_geography_off()
    assert geography.chosen_seed(module.campaign.ui) == seed
    assert "before the first season" in elements["geography-status"].innerText
    assert "fixed" in elements["geography-note"].innerText


def test_a_consulting_case_carries_its_inherited_map_and_a_challenge_run_ignores_the_choice(game_env):
    module = game_env.module
    elements = game_env.elements
    geography.set_seed(module.campaign.ui, 5)
    elements["consulting-case-smokestack-button"].dispatch("click", None)
    assert module._geo_seed() == geography.CASE_SEEDS["smokestack"]
    module.render()
    assert module.get_visual_state()["terrain"]
    module.on_consulting_abandon()
    geography.set_seed(module.campaign.ui, 5)
    module.campaign.ui["challenge_run"] = {"kind": "custom"}
    try:
        if module.challengerun.get(module.campaign.ui) is not None:
            assert module._geo_seed() is None
    finally:
        module.campaign.ui.pop("challenge_run", None)


def test_the_visual_state_and_dashboard_report_the_terrain(game_env):
    module = game_env.module
    assert module.get_visual_state()["terrain"] == []
    geography.set_seed(module.campaign.ui, 3)
    data = module.get_visual_state()
    assert data["terrain"] and {c["biome"] for c in data["terrain"]} <= set(geography.BIOMES)
    json.dumps(data)
    rows = module._extra_dashboard_sections()[0]["rows"]
    assert ("Geography", "river 7, mountains 4") in rows


def test_maps_survive_a_save_and_old_or_junk_saves_mean_open_land(game_env):
    module = game_env.module
    geography.set_seed(module.campaign.ui, 3)
    data = json.loads(json.dumps(module.get_state()))
    module.campaign.ui.pop(geography.KEY)
    module.load_state(data)
    assert geography.chosen_seed(module.campaign.ui) == 3
    data["ui"].pop(geography.KEY)
    module.load_state(data)
    assert geography.chosen_seed(module.campaign.ui) is None
    for junk in ("x", {"seed": "7"}, {"seed": -1}, {"seed": None}, 5):
        data["ui"][geography.KEY] = junk
        module.load_state(data)
        assert geography.chosen_seed(module.campaign.ui) is None
    assert save.Campaign().ui == {}
