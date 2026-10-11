"""A-9 (Observatory: Survey Data, the star chart, relays) and A-10 (rogue comets)."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _panel_text(env):
    return "\n".join(t for t in _texts(env.elements["observatory-panel"]) if t)


def _open(env):
    env.elements["observatory-toggle-button"].dispatch("click")


def _buttons(env, text_part):
    return [e for e in env.elements["observatory-panel"].descendants()
            if getattr(e, "tagName", "") == "BUTTON" and text_part in e.innerText]


def _reveal(m, count, data=None):
    m.survey_data = sum(e["cost"] for e in m.CHART[:count]) if data is None else data
    for _ in range(count):
        assert m.survey_region() is not None


# --- the chart -----------------------------------------------------------------


def test_chart_has_four_points_and_four_comets_with_rising_costs(game_env):
    m = game_env.module
    ids = [e["id"] for e in m.CHART]
    assert len(ids) == 8 and len(set(ids)) == 8
    assert [e["kind"] for e in m.CHART].count("point") == 4
    assert [e["kind"] for e in m.CHART].count("comet") == 4
    costs = [e["cost"] for e in m.CHART]
    assert costs == sorted(costs) and costs[0] == 1
    assert [e["rank"] for e in m.CHART if e["kind"] == "comet"] == [1, 2, 3, 4]


def test_a_fresh_game_has_no_survey_data_and_no_bonus(game_env):
    m = game_env.module
    assert m.survey_data == 0 and m.chart_revealed == 0 and m.relay_bonus() == 0
    m.tick()
    assert game_env.elements["comet-strip"].hidden is True
    assert game_env.elements["observatory-toggle-button"].innerText.endswith("(0/8)")
    assert "survey_data" not in m.serialize_state()


# --- Survey Data sources and spending -----------------------------------------------


def test_prestige_gives_two_survey_data(game_env):
    m = game_env.module
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    game_env.prestige()
    assert m.survey_data == m.SURVEY_PER_PRESTIGE == 2


def test_a_charter_stamp_gives_one_survey_data(game_env):
    m = game_env.module
    m.tick()
    game_env.earth["resource_count"] = 5000
    m.tick()
    assert m.mission_stamps and m.survey_data == len(m.mission_stamps)


def test_a_codex_clue_gives_one_survey_data(game_env):
    m = game_env.module
    m.planet_state["Moon"]["generator_count"] = 13
    m.tick()
    assert m.codex_found and m.survey_data >= 1


def test_survey_uncovers_the_next_region_in_fixed_order_and_spends_the_cost(game_env):
    m = game_env.module
    m.survey_data = 1
    first = m.survey_region()
    assert first["id"] == "wanderer" and m.survey_data == 0 and m.chart_revealed == 1
    assert m.survey_region() is None  # the second region costs 1 and there is none left
    m.survey_data = 4
    assert m.survey_region()["id"] == "harbour_light"
    assert m.survey_data == 3 and m.chart_revealed == 2
    assert m.survey_region()["id"] == "ember"  # costs 2
    assert m.survey_data == 1 and m.chart_revealed == 3
    assert m.survey_region() is None  # the fourth costs 2, only 1 left
    assert m.survey_data == 1 and m.chart_revealed == 3


def test_the_whole_chart_can_be_uncovered_and_then_there_is_nothing_more(game_env):
    m = game_env.module
    _reveal(m, 8)
    assert m.chart_revealed == 8 and m.survey_data == 0
    m.survey_data = 9
    assert m.survey_region() is None and m.chart_next() is None
    assert m.survey_data == 9


# --- relays ----------------------------------------------------------------------------


def test_a_hidden_point_cannot_be_claimed_and_an_open_one_costs_a_pile(game_env):
    m = game_env.module
    game_env.earth["resource_count"] = 1000
    assert m.point_state("harbour_light") is None
    assert m.claim_point("harbour_light") is False
    _reveal(m, 2)
    assert m.point_state("harbour_light") == "open"
    assert m.claim_point("harbour_light") is True
    assert m.point_state("harbour_light") == "yours"
    assert abs(game_env.earth["resource_count"] - (1000 - m.CLAIM_COST)) < 1e-9
    assert m.claim_point("harbour_light") is False  # already yours
    assert m.claim_point("comet") is False and m.claim_point("wanderer") is False


def test_claiming_needs_a_pile_big_enough(game_env):
    m = game_env.module
    _reveal(m, 2)
    game_env.earth["resource_count"] = m.CLAIM_COST - 1
    assert m.claim_point("harbour_light") is False
    assert m.point_state("harbour_light") == "open"


def test_a_relay_adds_one_percent_yield_everywhere_including_clicks(game_env):
    m = game_env.module
    _reveal(m, 2)
    game_env.earth["resource_count"] = 1000
    m.claim_point("harbour_light")
    assert abs(m.relay_bonus() - 0.01) < 1e-12
    assert abs(m.stamp_bonus("Mars") - 0.01) < 1e-12
    game_env.earth["resource_count"] = 0.0
    game_env.click()
    assert abs(game_env.earth["resource_count"] - 1.01) < 1e-9


# --- comets ------------------------------------------------------------------------------


def test_no_comet_until_one_is_uncovered_then_it_shows_in_the_strip(game_env):
    m = game_env.module
    m.tick()
    assert game_env.elements["comet-strip"].hidden is True
    _reveal(m, 1)
    m.tick()
    strip = game_env.elements["comet-strip"]
    assert strip.hidden is False
    assert "Wanderer" in strip.innerText and "overhead" in strip.innerText
    assert "comet-strip--bright" in strip.className


def test_the_comet_fades_with_time_but_never_goes_away(game_env):
    m = game_env.module
    _reveal(m, 1)
    m.tick()
    strip = game_env.elements["comet-strip"]
    m.total_ticks += m.COMET_BRIGHT_TICKS
    m.tick()
    assert "comet-strip--fading" in strip.className and "fading" in strip.innerText
    m.total_ticks += m.COMET_FADING_TICKS
    m.tick()
    assert "comet-strip--faint" in strip.className and "nothing is lost" in strip.innerText
    assert strip.hidden is False
    game_env.elements["comet-strip"].dispatch("click")
    assert strip.hidden is True


def test_catching_a_comet_pays_every_world_you_have_and_is_once_per_run(game_env):
    m = game_env.module
    game_env.unlock_tier(1)
    _reveal(m, 1)
    m.tick()
    before = {p: m.planet_state[p]["resource_count"] for p in m._overview_planets()}
    amounts = m.catch_comet()
    assert set(amounts) == set(m._overview_planets()) and len(amounts) >= 3
    for planet, amount in amounts.items():
        assert amount >= m.COMET_FLOOR
        assert abs(m.planet_state[planet]["resource_count"] - before[planet] - amount) < 1e-9
    assert m.comets_caught_run == ["wanderer"] and m.comets_caught_total == 1
    assert m.catch_comet() is None  # the only uncovered comet is caught
    m.tick()
    assert game_env.elements["comet-strip"].hidden is True


def test_a_bigger_comet_pays_more_and_a_big_economy_pays_more_than_the_floor(game_env):
    m = game_env.module
    _reveal(m, 3)
    m.comets_caught_run.append("wanderer")
    amounts = m.catch_comet()  # Ember, rank 2
    assert amounts["Earth"] == m.COMET_FLOOR * 2
    m2 = m.CHART_BY_ID["ember"]
    game_env.earth["generator_count"] = 400
    big = m.comet_windfall(m2)["Earth"]
    assert big > m.COMET_FLOOR * 2 and big == round(m.COMET_SECONDS_OF_OUTPUT * m._output_per_second("Earth"))


def test_comets_come_back_after_a_prestige(game_env):
    m = game_env.module
    _reveal(m, 1)
    m.catch_comet()
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    game_env.prestige()
    assert m.comets_caught_run == [] and m.comets_caught_total == 1
    assert m.comet_ready()["id"] == "wanderer"


def test_the_strip_is_a_real_button_on_both_pages(game_env):
    for name in ("index.html", "pc.html"):
        html = (GAME_DIR / name).read_text(encoding="utf-8")
        assert re.search(r'<button id="comet-strip"[^>]*type="button"', html), name
        for element_id in ("observatory-toggle-button", "observatory-panel"):
            assert f'id="{element_id}"' in html, (name, element_id)


# --- the panel -----------------------------------------------------------------------------


def test_the_panel_shows_masked_regions_and_an_enabled_survey_button_only_when_affordable(game_env):
    m = game_env.module
    _open(game_env)
    text = _panel_text(game_env)
    assert "Unmapped region 1" in text and "Unmapped region 8" in text
    assert "Wanderer" not in text  # nothing leaks before it is uncovered
    survey = _buttons(game_env, "Survey the next region")[0]
    assert survey.disabled is True and "costs 1 Survey Data" in survey.innerText
    m.survey_data = 1
    m.tick()
    assert _buttons(game_env, "Survey the next region")[0].disabled is False


def test_surveying_from_the_panel_uncovers_a_region_and_rebuilds_it(game_env):
    m = game_env.module
    m.survey_data = 1
    _open(game_env)
    game_env.panel_click("observatory-panel", action="survey")
    assert m.chart_revealed == 1
    text = _panel_text(game_env)
    assert "Comet Wanderer" in text and "Unmapped region 1" not in text and "Unmapped region 2" in text


def test_claiming_from_the_panel_and_the_card_text(game_env):
    m = game_env.module
    _reveal(m, 2)
    game_env.earth["resource_count"] = 500
    _open(game_env)
    assert "Nobody holds this point" in _panel_text(game_env)
    claim = _buttons(game_env, "Claim")[0]
    assert "200 Iron" in claim.innerText and claim.disabled is False
    game_env.panel_click("observatory-panel", action="claim", point="harbour_light")
    text = _panel_text(game_env)
    assert "Your relay" in text and "Relays held: 1 of 4" in text and "+1% yield" in text


def test_the_toggle_label_counts_regions_and_closes_the_panel(game_env):
    m = game_env.module
    _reveal(m, 3)
    _open(game_env)
    toggle = game_env.elements["observatory-toggle-button"]
    assert toggle.innerText == "Hide Observatory (3/8)"
    assert game_env.elements["observatory-panel"].hidden is False
    _open(game_env)
    assert game_env.elements["observatory-panel"].hidden is True
    assert toggle.innerText == "\U0001f52d Observatory (3/8)"


# --- saves ----------------------------------------------------------------------------------


def test_everything_round_trips_through_a_save(game_env):
    m = game_env.module
    _reveal(m, 3)
    m.survey_data = 6
    game_env.earth["resource_count"] = 1000
    m.claim_point("harbour_light")
    m.catch_comet()
    saved = m.serialize_state()
    assert saved["survey_data"] == 6 and saved["chart_revealed"] == 3
    assert saved["point_claims"] == {"harbour_light": "yours"}
    assert saved["comets_caught_run"] == ["wanderer"] and saved["comets_caught_total"] == 1
    m.survey_data, m.chart_revealed, m.comets_caught_total = 0, 0, 0
    m.point_claims.clear()
    m.comets_caught_run.clear()
    m.deserialize_state(saved)
    assert (m.survey_data, m.chart_revealed, m.comets_caught_total) == (6, 3, 1)
    assert m.point_claims == {"harbour_light": "yours"} and m.comets_caught_run == ["wanderer"]


def test_an_old_save_loads_with_an_empty_observatory(game_env):
    m = game_env.module
    saved = m.serialize_state()
    for key in ("survey_data", "chart_revealed", "point_claims", "comets_caught_run", "comets_caught_total"):
        saved.pop(key, None)
    m.survey_data, m.chart_revealed = 4, 4
    m.deserialize_state(saved)
    assert m.survey_data == 0 and m.chart_revealed == 0 and m.point_claims == {}


def test_a_tampered_save_is_cleaned(game_env):
    m = game_env.module
    saved = m.serialize_state()
    saved.update({
        "survey_data": -5, "chart_revealed": 99, "comets_caught_total": "lots",
        "point_claims": {"harbour_light": "yours", "cairn": "yours", "nope": "yours", "far_anchor": 7, "wanderer": "yours"},
        "comets_caught_run": ["wanderer", "wanderer", "harbour_light", "quiet_one", 5],
    })
    m.deserialize_state(saved)
    assert m.survey_data == 0 and m.chart_revealed == 0 and m.comets_caught_total == 0
    assert m.point_claims == {} and m.comets_caught_run == []
    saved.update({"chart_revealed": 3, "survey_data": True})
    m.deserialize_state(saved)
    assert m.chart_revealed == 3 and m.survey_data == 0
    assert m.point_claims == {"harbour_light": "yours"}  # cairn is still hidden at 3
    assert m.comets_caught_run == ["wanderer"]


# --- achievements ------------------------------------------------------------------------------


def test_star_cartographer_and_comet_catcher(game_env):
    m = game_env.module
    assert not {"star_cartographer", "comet_catcher"} & set(m.achievement_ids_earned())
    assert m.ACHIEVEMENT_PROGRESS["star_cartographer"]() == (0, 8)
    m.chart_revealed = 8
    m.comets_caught_total = 3
    assert "star_cartographer" in m.achievement_ids_earned()
    assert "comet_catcher" not in m.achievement_ids_earned()
    assert m.ACHIEVEMENT_PROGRESS["comet_catcher"]() == (3, 4)
    m.comets_caught_total = 4
    assert "comet_catcher" in m.achievement_ids_earned()
