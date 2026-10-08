"""C-4 plant-mix hover/focus readout, C-26 repaired-fields note, and the GC-4 demolition puff."""
import json


# --- C-4 ------------------------------------------------------------------------------------------

def test_hover_text_gives_capacity_revenue_and_emissions_shares(game_env):
    g = game_env.module
    s = game_env.state
    s.plant_counts["coal"] = 2      # 40 capacity, 120 emissions
    s.plant_counts["solar"] = 6     # 60 capacity, 0 emissions
    text = g.mix_hover_text("coal")
    assert text.startswith("Coal: 40% of capacity") and "about 40% of revenue" in text
    assert "80 of 200 funds per round" in text          # 40% of 100 paid units x 2 funds
    assert "100% of emissions (120 of 120 per round)" in text
    solar = g.mix_hover_text("solar")
    assert "60% of capacity" in solar and "0% of emissions (0 of 120 per round)" in solar


def test_hover_text_for_an_empty_grid_and_a_clean_grid(game_env):
    g = game_env.module
    s = game_env.state
    assert "no generation on the grid yet" in g.mix_hover_text("coal")
    s.plant_counts["nuclear"] = 2
    assert "0% of emissions (the grid emits nothing)" in g.mix_hover_text("nuclear")
    assert g.mix_hover_text("gas").startswith("Gas: 0% of capacity")


def test_revenue_is_capped_by_demand(game_env):
    g = game_env.module
    s = game_env.state
    s.plant_counts["nuclear"] = 5       # 500 capacity against 100 demand
    assert "200 of 200 funds per round" in g.mix_hover_text("nuclear")


def test_hovering_highlights_the_plant_row_and_leaving_clears_it(game_env):
    el = game_env.elements
    game_env.state.plant_counts["wind"] = 3
    el["wind-mix-row"].dispatch("mouseenter", None)
    assert "plant-row--highlight" in el["wind-row"].classList and "mix-row--active" in el["wind-mix-row"].classList
    assert el["mix-hover-readout"].innerText.startswith("Wind: 100% of capacity")
    el["wind-mix-row"].dispatch("mouseleave", None)
    assert "plant-row--highlight" not in el["wind-row"].classList
    assert el["mix-hover-readout"].innerText.startswith("Hover or focus")
    el["hydro-mix-row"].dispatch("focus", None)
    assert "plant-row--highlight" in el["hydro-row"].classList
    el["hydro-mix-row"].dispatch("blur", None)
    assert "plant-row--highlight" not in el["hydro-row"].classList


# --- C-26 ------------------------------------------------------------------------------------------

def test_a_complete_save_reports_nothing_repaired(game_env):
    g = game_env.module
    g.load_state(json.loads(json.dumps(g.get_state())))
    assert g.load_report["loaded"] and g.load_report["fields"] == []
    assert "nothing had to be repaired" in g.load_report_text()


def test_missing_fields_are_counted_and_named(game_env):
    g = game_env.module
    data = json.loads(json.dumps(g.get_state()))
    for key in ("funds_history", "last_round_recap", "seed", "perfect_streak"):
        del data[key]
    del data["plant_counts"]["hydro"]
    g.load_state(data)
    fields = g.load_report["fields"]
    assert fields == ["funds_history", "last_round_recap", "perfect_streak", "seed", "plant_counts.hydro"]
    text = g.load_report_text()
    assert "repaired 5 missing fields" in text and "funds_history" in text
    assert game_env.state.plant_counts["hydro"] == 0   # still defaulted safely, no crash


def test_an_old_save_with_only_the_early_keys_loads_and_says_so(game_env):
    g = game_env.module
    g.load_state({"round_number": 4, "funds": 321.0})
    assert game_env.state.round_number == 4 and game_env.state.funds == 321.0
    assert len(g.load_report["fields"]) > 20
    assert "more)" in g.load_report_text()


def test_the_note_appears_in_the_whats_new_panel(game_env):
    g = game_env.module
    game_env.toggle_changelog()
    assert not any("Last save loaded" in c.innerText for c in game_env.elements["changelog-panel"].children)
    data = json.loads(json.dumps(g.get_state()))
    del data["bau_emissions"]
    g.load_state(data)
    panel = game_env.elements["changelog-panel"]
    assert panel.children[0].className == "changelog-load-note"
    assert "repaired 1 missing field " in panel.children[0].innerText and "bau_emissions" in panel.children[0].innerText


def test_an_empty_save_reports_every_field_without_crashing(game_env):
    g = game_env.module
    assert len(g.compute_load_report({})) == len(set(g.get_state()) - g.LOAD_REPORT_IGNORED_KEYS)


# --- GC-4 demolition puff ---------------------------------------------------------------------------

def test_retiring_the_last_coal_plant_replays_the_puff(game_env):
    el = game_env.elements
    game_env.build("coal")
    game_env.retire("coal")
    assert game_env.timers.pending, "the puff is started from a short timer"
    game_env.timers.flush()
    assert "eulogy-puff" in el["eulogy-display"].classList
    game_env.build("gas")
    game_env.retire("gas")
    assert not any(delay == 30 for _callback, delay in game_env.timers.pending)
