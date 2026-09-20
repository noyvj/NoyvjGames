"""K5 (planning/TODO.md) — the civilization summary report (summary.py).

Continuum has no forced end state (Space Age is simply the last era
transition.py knows how to leave — nothing stops play there), so per K5's
own "if there's no explicit end state... make it accessible as an
on-demand summary/report panel instead" instruction, this covers the pure
report-building logic (summary.py) the same way test_visual_state.py
covers visual.py: a plain, JSON-safe, pure function of a Campaign's own
state. game.py's DOM rendering of it is exercised indirectly through
game_env in the toggle/render tests at the bottom of this file.
"""

import json

import sim
import save
import summary
import sustainability


def test_fresh_campaign_reports_one_incomplete_tribal_row():
    campaign = save.Campaign()
    data = summary.summary(campaign)

    assert data["eras_completed"] == 0
    assert data["eras_total"] == len(sim.ERA_ORDER)
    assert len(data["eras"]) == 1
    row = data["eras"][0]
    assert row["era"] == "tribal"
    assert row["completed"] is False
    assert row["season_reached"] == 1
    assert row["population"] == campaign.state.population


def test_summary_is_json_serialisable():
    campaign = save.Campaign()
    json.loads(json.dumps(summary.summary(campaign)))


def test_summary_never_mutates_the_campaign_it_reads():
    import copy

    campaign = save.Campaign()
    before_state = copy.deepcopy(campaign.state.__dict__)
    before_snapshots = copy.deepcopy(campaign.era_snapshots)
    summary.summary(campaign)
    assert campaign.state.__dict__ == before_state
    assert campaign.era_snapshots == before_snapshots


def test_advancing_to_a_new_era_adds_a_completed_row_and_a_fresh_live_row():
    campaign = save.Campaign()
    campaign.state.population = 20
    assert campaign.advance_to_era("agrarian") is True

    data = summary.summary(campaign)
    assert data["eras_completed"] == 1
    assert [row["era"] for row in data["eras"]] == ["tribal", "agrarian"]

    tribal_row = data["eras"][0]
    assert tribal_row["completed"] is True
    assert tribal_row["population"] == 20
    assert tribal_row["score"] is not None
    assert tribal_row["score_label"] in sustainability.SCORE_LABELS

    agrarian_row = data["eras"][1]
    assert agrarian_row["completed"] is False
    assert agrarian_row["era"] == "agrarian"


def test_furthest_era_and_journey_complete_track_real_progress():
    campaign = save.Campaign()
    data = summary.summary(campaign)
    assert data["furthest_era"] == "tribal"
    assert data["journey_complete"] is False

    campaign.state.era = sim.ERA_ORDER[-1]
    campaign.furthest_era = sim.ERA_ORDER[-1]
    data = summary.summary(campaign)
    assert data["journey_complete"] is True


def test_total_seasons_reports_the_live_season_normally():
    campaign = save.Campaign()
    campaign.state.season = 7
    assert summary.total_seasons(campaign) == 7


def test_total_seasons_reports_the_parked_season_during_a_revisit():
    campaign = save.Campaign()
    campaign.state.population = 20
    campaign.advance_to_era("agrarian")
    for _ in range(4):
        campaign.state.advance_season(campaign.tree.effects())

    assert campaign.enter_revisit("tribal") is True
    # Mid-revisit, campaign.state.season belongs to the revisited Tribal
    # snapshot (season 1), not the campaign's real forward progress.
    assert campaign.state.season == 1
    assert summary.total_seasons(campaign) == 5  # the parked Agrarian season


def test_peak_population_includes_completed_rows_the_live_row_and_a_revisit_park():
    campaign = save.Campaign()
    campaign.state.population = 12
    campaign.advance_to_era("agrarian")
    campaign.state.population = 40
    rows = summary.eras_played(campaign)
    assert summary.peak_population(campaign, rows) == 40

    campaign.enter_revisit("tribal")
    rows = summary.eras_played(campaign)
    # The live row now describes the (smaller) revisited Tribal snapshot,
    # but the parked Agrarian population (40) must still count.
    assert summary.peak_population(campaign, rows) == 40


def test_peak_score_reads_the_real_score_history():
    campaign = save.Campaign()
    campaign.state.score_history = [40.0, 85.0, 60.0]
    assert summary.peak_score(campaign) == 85.0


def test_peak_score_is_none_for_a_brand_new_campaign_with_no_history():
    campaign = save.Campaign()
    assert campaign.state.score_history == []
    assert summary.peak_score(campaign) is None


def test_peak_score_during_a_revisit_reads_the_parked_history():
    campaign = save.Campaign()
    campaign.state.score_history = [90.0]
    campaign.advance_to_era("agrarian")
    campaign.enter_revisit("tribal")
    # The revisited Tribal snapshot's own score_history is whatever it was
    # frozen with, but peak_score() must still see the parked run's 90.0.
    assert summary.peak_score(campaign) == 90.0


# --- game.py wiring (panel toggle) ---------------------------------------


def test_summary_panel_starts_hidden_and_toggles_open(game_env):
    module = game_env.module
    assert module.summary_panel_open is False
    game_env.elements["summary-toggle-button"].dispatch("click", None)
    assert module.summary_panel_open is True
    assert game_env.elements["summary-panel"].hidden is False
    game_env.elements["summary-toggle-button"].dispatch("click", None)
    assert module.summary_panel_open is False
    assert game_env.elements["summary-panel"].hidden is True


def test_open_summary_panel_shows_a_tribal_era_row(game_env):
    game_env.elements["summary-toggle-button"].dispatch("click", None)
    panel = game_env.elements["summary-panel"]
    all_text = " ".join(_collect_text(panel))
    assert "Tribal" in all_text


def _collect_text(element):
    texts = [element.innerText] if getattr(element, "innerText", "") else []
    for child in getattr(element, "children", []):
        texts.extend(_collect_text(child))
    return texts
