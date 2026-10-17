"""R-30: the community coastline line. The save carries a write-only `coastline_kept` (rows still dry) for
comparable settlements; the page hands in the community average from GET /stats/games/tide and
game.py owns the rule and the wording. Until app/stats.py lists the field the line simply stays hidden."""

import json
from pathlib import Path

import pytest

from .pagefiles import page_text

GAME_DIR = Path(__file__).resolve().parent.parent


def _play(m, seasons):
    for _ in range(seasons):
        m.state.advance_season()


# ---- the write-only save field ---------------------------------------------------------------------

def test_no_field_before_any_season_is_played(game_env):
    m = game_env.module
    assert m.state.season == 1
    assert "coastline_kept" not in m.get_state()


def test_field_is_the_number_of_dry_rows_and_matches_the_steward_summary(game_env):
    m = game_env.module
    _play(m, 3)
    state = m.get_state()
    assert state["coastline_kept"] == m.state.rows_dry_count()
    steward_dry = next(i["value"] for i in state["summary"] if i["label"] == "Coastline rows still dry")
    assert state["coastline_kept"] == steward_dry
    assert isinstance(state["coastline_kept"], int) and 0 <= state["coastline_kept"] <= m.COASTLINE_ROWS


def test_field_counts_rows_given_up_by_managed_retreat(game_env):
    m = game_env.module
    _play(m, 2)
    before = m.get_state()["coastline_kept"]
    m.state.funds = 10_000
    assert m.state.managed_retreat()
    assert m.get_state()["coastline_kept"] == before - 1


def test_field_follows_the_sea_over_a_long_run(game_env):
    m = game_env.module
    seen = []
    for _ in range(40):
        m.state.advance_season()
        seen.append(m.get_state()["coastline_kept"])
    assert seen == sorted(seen, reverse=True)  # rows only ever go under
    assert seen[0] > seen[-1]


@pytest.mark.parametrize("change", ["coastline", "sea_scenario", "chess", "workshop", "daily"])
def test_field_is_left_out_on_non_standard_terms(game_env, change):
    m = game_env.module
    if change == "coastline":
        assert m.state.set_coastline("delta")
    elif change == "sea_scenario":
        assert m.state.set_sea_scenario("severe")
    elif change == "chess":
        m.state.chess_mode = True
    elif change == "workshop":
        m.state.workshop = dict(m.state.workshop, funds=m.WORKSHOP_DEFAULTS["funds"] + 1)
    else:
        m.state.daily = {"date": "2026-10-11", "seasons": 12}
    _play(m, 3)
    assert "coastline_kept" not in m.get_state()


def test_extra_key_is_ignored_on_load(game_env):
    m = game_env.module
    _play(m, 3)
    state = m.get_state()
    assert "coastline_kept" in state
    assert m.load_state(state) is not False
    state["coastline_kept"] = 0  # a hand-edited value changes nothing: the line is derived, never read back
    m.load_state(state)
    assert m.get_state()["coastline_kept"] == m.state.rows_dry_count()


# ---- the community figure handed in by the page ----------------------------------------------------

@pytest.mark.parametrize("bad", [None, "4.2", float("nan"), float("inf"), -0.5, 6.5, True, [], {}])
def test_unusable_figures_clear_the_line(game_env, bad):
    m = game_env.module
    m.set_community_coastline(4.2, 12)
    assert m.coastline_community_text()
    assert m.set_community_coastline(bad) is False
    assert m.community_coastline is None
    assert m.coastline_community_text() == ""


def test_no_figure_means_nothing_shown(game_env):
    m = game_env.module
    assert m.community_coastline is None
    assert m.coastline_community_text() == ""
    el = game_env.elements["coastline-community"]
    m.render()
    assert el.hidden is True


@pytest.mark.parametrize("value", [0, 4, 4.25, 6])
def test_valid_figures_are_kept(game_env, value):
    m = game_env.module
    assert m.set_community_coastline(value, 9) is True
    assert m.community_coastline == {"mean": float(value), "count": 9}


def test_line_names_the_average_out_of_six_and_your_own_count(game_env):
    m = game_env.module
    _play(m, 3)
    m.set_community_coastline(4.26, 12)
    dry = m.state.rows_dry_count()
    assert m.coastline_community_text() == (
        f"Players keep on average 4.3 of {m.COASTLINE_ROWS} coastline rows dry; you keep {dry} (from 12 settlements)."
    )


def test_line_without_a_count_leaves_the_parenthesis_out(game_env):
    m = game_env.module
    m.set_community_coastline(4.0)
    text = m.coastline_community_text()
    assert text.startswith("Players keep on average 4.0 of 6 coastline rows dry; you keep ")
    assert "settlements" not in text


def test_your_count_updates_as_the_sea_rises(game_env):
    m = game_env.module
    m.set_community_coastline(3.0, 5)
    texts = set()
    for _ in range(40):
        m.state.advance_season()
        m.render()
        texts.add(game_env.elements["coastline-community"].innerText)
    assert len(texts) > 1
    assert all(t.startswith("Players keep on average 3.0 of 6") for t in texts)


def test_render_writes_and_shows_the_line(game_env):
    m = game_env.module
    el = game_env.elements["coastline-community"]
    m.set_community_coastline(4.0, 7)
    assert el.hidden is False and "you keep" in el.innerText
    m.set_community_coastline(None)
    assert el.hidden is True and el.innerText == ""


def test_other_terms_get_no_comparison_but_still_show_the_average(game_env):
    m = game_env.module
    assert m.state.set_coastline("atoll")
    m.set_community_coastline(4.0, 7)
    text = m.coastline_community_text()
    assert "you keep" not in text
    assert "standard coastline" in text and "4.0 of 6" in text and "nothing to compare" in text


def test_missing_element_is_harmless(game_env):
    m = game_env.module
    del game_env.elements["coastline-community"]
    assert m.set_community_coastline(4.0, 3) is True
    m.render()


def test_a_comparison_is_never_a_percentile_of_one_player(game_env):
    """Small-group suppression lives in the backend (fields need 3 values): the page only ever shows a mean."""
    m = game_env.module
    m.set_community_coastline(5.0, 3)
    assert "percentile" not in m.coastline_community_text()


# ---- page wiring -----------------------------------------------------------------------------------

@pytest.mark.parametrize("page", ["index.html", "pc.html"])
def test_both_pages_have_the_line_and_the_fetch(page):
    html = page_text(page)
    assert 'id="coastline-community"' in html
    assert "set_community_coastline" in html
    assert "/stats/games/tide" in html
    assert "coastline_kept" in html
    assert "hub_reduce_data" in html  # honours the hub's "reduce data" choice
    assert html.index('id="community-index"') < html.index('id="coastline-community"')


def test_dashboard_and_desktop_window_carry_the_line_with_the_coast_panel():
    assert '"#coastline-community"' in (GAME_DIR / "ui.js").read_text(encoding="utf-8")
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    members = [m for c in config["composites"] for m in c["members"]]
    assert "#coastline-community" in members
