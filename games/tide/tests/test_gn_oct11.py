"""GN-8 (Workshop, Restore and Crew live in a Desktop window) and GN-9 (next season if you do nothing)."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
PC_HTML = (ROOT / "pc.html").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "settings.js").read_text(encoding="utf-8")
CONFIG = json.loads((ROOT / "pc-config.json").read_text(encoding="utf-8"))


@pytest.fixture
def storage(game_env, monkeypatch):
    store = {}
    monkeypatch.setattr(game_env.module, "_read_local_storage_item", lambda key: store.get(key))
    monkeypatch.setattr(game_env.module, "_write_local_storage_item", lambda key, value: store.__setitem__(key, value))
    return store


KEYS = ("funds", "acidity", "fish_yield", "sea_level", "damage", "rows_dry")


def _numbers(m):
    s = m.state
    return {"funds": s.funds, "acidity": s.acidity, "fish_yield": s.fish_yield_multiplier(), "sea_level": s.sea_level,
            "damage": s.cumulative_damage, "rows_dry": s.rows_dry_count()}


def _assert_forecast_matches_the_next_season(env):
    m = env.module
    predicted = m.season_forecast()
    assert predicted["now"] == _numbers(m)
    env.advance_season()
    actual = _numbers(m)
    for key in KEYS:
        assert predicted["next"][key] == pytest.approx(actual[key]), key


# --- GN-9: the projection is the real next season ---------------------------------------------------------------------

def test_the_forecast_matches_what_advancing_without_acting_really_does_every_season(game_env):
    m = game_env.module
    for _ in range(14):
        _assert_forecast_matches_the_next_season(game_env)
    assert m.state.season == 15


def test_the_forecast_matches_after_investing_in_all_three_and_with_a_mixed_output(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.invest("output")
    game_env.invest("reduction")
    game_env.set_output_mix("mixed")
    for _ in range(10):
        _assert_forecast_matches_the_next_season(game_env)
        if m.state.funds >= m.state.invest_cost("adaptation"):
            game_env.invest("adaptation")


def test_the_forecast_matches_with_storms_on_a_severe_sea_hard_lag_crew_and_the_sister_town(game_env):
    m = game_env.module
    s = m.state
    s.set_sea_scenario("severe")
    s.set_hard_lag_mode(True)
    s.set_storm_mode(True)
    s.enable_sister()
    s.funds = 900
    s.hire(next(iter(m.CREW)))
    for _ in range(3):
        game_env.invest("output")
    for _ in range(18):
        _assert_forecast_matches_the_next_season(game_env)


def test_the_forecast_changes_nothing_in_the_real_run(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.invest("output")
    game_env.advance_season()
    real = m.state
    before = json.dumps(m.get_state(), sort_keys=True, default=str)
    ticker = list(real.ticker_full_history)
    m.season_forecast()
    m.render()
    assert m.state is real
    assert json.dumps(m.get_state(), sort_keys=True, default=str) == before
    assert real.ticker_full_history == ticker


def test_the_forecast_restores_the_real_state_even_if_the_projection_fails(game_env, monkeypatch):
    m = game_env.module
    real = m.state

    def boom(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(m.SettlementState, "advance_season", boom)
    with pytest.raises(RuntimeError):
        m.season_forecast()
    assert m.state is real


# --- GN-9: the line on the page ------------------------------------------------------------------------------------

def test_the_line_shows_each_readout_with_an_arrow_the_number_and_a_tooltip(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.invest("output")
    m.render()
    line = game_env.elements["forecast-line"]
    assert line.hidden is False
    text = line.innerHTML
    assert "Next season if you do nothing" in text
    for label in ("Funds", "Acidity", "Fishing yield", "Sea level", "Damage"):
        assert label in text
    assert "→" in text and "▲" in text           # funds and acidity and the sea go up
    assert text.count('title="') >= 6                      # the lead and each chip explain themselves
    assert "nothing is spent" in text


def test_an_unchanged_readout_says_no_change_instead_of_a_zero_arrow(game_env):
    m = game_env.module
    m.render()
    chips = dict((key, text) for key, text, _tip in m.forecast_chips())
    assert "no change" in chips["acidity"] and "▲" not in chips["acidity"]
    assert "no change" in chips["fish_yield"]


def test_a_row_that_would_flood_is_called_out(game_env):
    m = game_env.module
    m.state.sea_level = m.row_flood_threshold(m.COASTLINE_ROWS - 1) - 1.0
    m.render()
    chips = dict((key, text) for key, text, _tip in m.forecast_chips())
    assert "rows_dry" in chips and "▼" in chips["rows_dry"]


def test_the_setting_is_on_by_default_and_hides_the_line_when_off(game_env, storage):
    m = game_env.module
    assert m.forecast_on() is True
    m.render()
    assert game_env.elements["forecast-line"].hidden is False
    storage[m.FORECAST_KEY] = "off"
    m.render()
    assert game_env.elements["forecast-line"].hidden is True and game_env.elements["forecast-line"].innerHTML == ""
    storage[m.FORECAST_KEY] = "on"
    m.render()
    assert game_env.elements["forecast-line"].hidden is False


def test_the_settings_panel_has_the_checkbox_checked_and_the_script_stores_it():
    assert re.search(r'<input type="checkbox" id="forecast-checkbox" checked>', HTML)
    assert "tide-season-forecast" in SETTINGS_JS and '"off"' in SETTINGS_JS
    assert 'id="forecast-checkbox"' in PC_HTML and 'id="forecast-line"' in HTML and 'id="forecast-line"' in PC_HTML


def test_the_line_sits_in_the_desktop_stage_bar_beside_the_readouts():
    assert "#forecast-line" in CONFIG["zones"]["stagebar"]


# --- GN-8: Workshop, Restore and Crew in a window -----------------------------------------------------------------

def test_workshop_restore_and_crew_are_one_desktop_window_in_the_menu():
    tools = [c for c in CONFIG["composites"] if c["id"] == "pc-tools-panel"]
    assert len(tools) == 1
    members = tools[0]["members"]
    assert ".workshop-panel" in members and "#autosave-panel" in members and ".crew-panel" in members
    assert tools[0]["group"] == "Game"
    for zone in CONFIG["zones"].values():
        assert not {".workshop-panel", "#autosave-panel", ".crew-panel"} & set(zone)


def test_the_classic_page_keeps_the_three_folds_where_they_were():
    assert HTML.index("Tide Workshop (custom rules)") < HTML.index("Restore a previous save") < HTML.index("Harbour crew")
