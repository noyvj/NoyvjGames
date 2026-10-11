"""A-15 (rival colonies: trade pressure you can ignore, share or end) and A-16 (ticker gossip)."""


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _panel_text(env):
    return "\n".join(t for t in _texts(env.elements["observatory-panel"]) if t)


def _buttons(env, text_part):
    return [e for e in env.elements["observatory-panel"].descendants()
            if getattr(e, "tagName", "") == "BUTTON" and text_part in e.innerText]


def _reveal(m, count):
    m.survey_data = sum(e["cost"] for e in m.CHART[:count])
    for _ in range(count):
        assert m.survey_region() is not None


def _routes_to_mars(env):
    env.unlock_tier(1)
    env.earth["trade_routes"] = {"Mars": 4}


def _plain_restore(m, planet):
    return m._incoming_trade_restore(planet)


# --- the rivals and their points ------------------------------------------------------------


def test_three_rivals_each_hold_one_of_the_four_points(game_env):
    m = game_env.module
    points = [e for e in m.CHART if e["kind"] == "point"]
    assert [e.get("rival") for e in points] == [None, "helios", "ceres", "outer"]
    assert {r["id"] for r in m.RIVALS} == {"helios", "ceres", "outer"}
    _reveal(m, 8)
    assert [m.point_state(e["id"]) for e in points] == ["open", "rival", "rival", "rival"]
    assert m.rival_points_held() == 3


def test_no_rival_pressure_until_a_rival_point_is_uncovered(game_env):
    m = game_env.module
    _reveal(m, 2)  # the open point only
    assert m.rival_points_held() == 0 and m.rival_pressure() == 0
    m.survey_data = 2
    m.survey_region()
    m.survey_data = 2
    m.survey_region()  # Ember then Cairn
    assert m.chart_revealed == 4 and m.rival_points_held() == 1
    assert abs(m.rival_pressure() - 0.08) < 1e-12


# --- the pressure itself -----------------------------------------------------------------------


def test_each_rival_point_cuts_trade_restore_by_eight_percent_up_to_three(game_env):
    m = game_env.module
    _routes_to_mars(game_env)
    base = _plain_restore(m, "Mars")
    assert base > 0
    _reveal(m, 4)
    assert abs(_plain_restore(m, "Mars") - base * 0.92) < 1e-12
    m.survey_data = 100
    while m.survey_region():
        pass
    assert m.chart_revealed == 8 and m.rival_points_held() == 3
    assert abs(_plain_restore(m, "Mars") - base * (1 - 0.24)) < 1e-12


def test_a_world_with_a_focus_is_not_pressured(game_env):
    m = game_env.module
    _routes_to_mars(game_env)
    m.survey_data = 100
    while m.survey_region():
        pass
    pressured = _plain_restore(m, "Mars")
    game_env.mars["terraform_progress"] = 80.0
    game_env.mars["specialization"] = "stability"
    free = _plain_restore(m, "Mars")
    assert abs(free - pressured / 0.76) < 1e-12
    assert m.rival_pressure("Mars") == 0 and m.rival_pressure("Earth") > 0


def test_the_settings_switch_removes_pressure_gossip_and_says_so(game_env):
    m = game_env.module
    _routes_to_mars(game_env)
    game_env.local_storage.setItem("sol-rivals", "off")
    m.survey_data = 100
    while m.survey_region():
        pass
    assert m.rival_pressure() == 0
    assert not [e for e in m.story_log if e.startswith("rumor:")]
    game_env.elements["observatory-toggle-button"].dispatch("click")
    assert "switched off in Settings" in _panel_text(game_env)
    game_env.local_storage.setItem("sol-rivals", "on")
    assert m.rival_pressure() > 0


def test_sandbox_is_never_pressured(game_env):
    m = game_env.module
    m.survey_data = 100
    while m.survey_region():
        pass
    for planet in m.PLANETS:
        m.planet_state[planet]["terraform_progress"] = m.TERRAFORM_MAX
    assert m.rival_pressure() > 0
    m.sandbox_mode = True
    assert m.rival_pressure() == 0


# --- sharing, taking over, ignoring --------------------------------------------------------------


def test_sharing_a_rival_point_costs_a_pile_ends_its_pressure_and_gives_half_a_relay(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.earth["resource_count"] = 1000
    assert m.partner_point("harbour_light") is False  # nobody to share with there
    assert m.partner_point("cairn") is True
    assert m.point_state("cairn") == "partner"
    assert abs(game_env.earth["resource_count"] - (1000 - m.PARTNER_COST)) < 1e-9
    assert m.rival_points_held() == 0 and m.rival_pressure() == 0
    assert abs(m.relay_bonus() - 0.005) < 1e-12
    assert m.partner_point("cairn") is False


def test_taking_over_costs_more_and_gives_the_full_relay(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.earth["resource_count"] = 5000
    assert m.claim_point("cairn") is False  # a rival's point is not "open"
    assert m.contest_cost("cairn") == m.CONTEST_COST == 800
    assert m.contest_point("cairn") is True
    assert m.point_state("cairn") == "yours"
    assert abs(game_env.earth["resource_count"] - (5000 - 800)) < 1e-9
    assert abs(m.relay_bonus() - 0.01) < 1e-12


def test_a_partner_can_be_bought_out_for_less(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.earth["resource_count"] = 5000
    m.partner_point("cairn")
    assert m.contest_cost("cairn") == m.TAKEOVER_COST == 500
    before = game_env.earth["resource_count"]
    assert m.contest_point("cairn") is True
    assert abs(game_env.earth["resource_count"] - (before - 500)) < 1e-9
    assert m.point_state("cairn") == "yours"


def test_a_payment_the_biggest_pile_cannot_cover_is_refused_and_nothing_changes(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.earth["resource_count"] = 299
    assert m.partner_point("cairn") is False and m.contest_point("cairn") is False
    assert m.point_state("cairn") == "rival" and game_env.earth["resource_count"] == 299


def test_ignoring_the_rivals_changes_nothing_by_itself(game_env):
    m = game_env.module
    _reveal(m, 8)
    before = dict(m.point_claims)
    for _ in range(50):
        m.tick()
    assert m.point_claims == before and m.rival_points_held() == 3


# --- the ticker -------------------------------------------------------------------------------------


def test_meeting_a_rival_adds_one_ticker_line_to_the_log_once(game_env):
    m = game_env.module
    _reveal(m, 4)  # Cairn is Helios
    assert "rumor:met:helios" in m.story_log
    lines = m.story_log_lines()
    assert any(line.startswith("Ticker: Helios Combine has run a flag up at Cairn") for line in lines)
    m._note_rumor("met:helios")
    assert m.story_log.count("rumor:met:helios") == 1
    assert "rumor:met:ceres" not in m.story_log


def test_the_ticker_never_becomes_the_headline_captains_log_line(game_env):
    m = game_env.module
    m.tick()
    headline = game_env.elements["captains-log-latest"].innerText
    _reveal(m, 4)
    assert game_env.elements["captains-log-latest"].innerText == headline
    items = [c.innerText for c in game_env.elements["captains-log-list"].children]
    assert items[0].startswith("Ticker:")  # newest first in the full list


def test_partnering_and_taking_over_each_add_their_own_line(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.earth["resource_count"] = 5000
    m.partner_point("cairn")
    assert "rumor:partner:helios" in m.story_log
    m.contest_point("cairn")
    assert "rumor:contest:helios" in m.story_log


def test_world_gossip_needs_the_rival_to_have_been_met(game_env):
    m = game_env.module
    game_env.unlock_tier(1)
    game_env.mars["terraform_progress"] = m.TERRAFORM_MAX
    m.tick()
    assert "rumor:world:Mars" not in m.story_log
    _reveal(m, 4)
    m.tick()
    assert "rumor:world:Mars" in m.story_log
    assert "rumor:world:AsteroidBelt" not in m.story_log
    count = len(m.story_log)
    m.tick()
    m.tick()
    assert len(m.story_log) == count


def test_gossip_has_zero_mechanical_effect(game_env):
    m = game_env.module
    _reveal(m, 4)
    before = {p: dict(v) for p, v in m.planet_state.items()}
    flags = (m.survey_data, m.chart_revealed, dict(m.point_claims), m.relay_bonus(), m.rival_pressure())
    for rumor in m.RUMORS:
        m._note_rumor(rumor["id"])
    assert {p: dict(v) for p, v in m.planet_state.items()} == before
    assert flags == (m.survey_data, m.chart_revealed, dict(m.point_claims), m.relay_bonus(), m.rival_pressure())


def test_every_rumour_is_a_single_plain_line_and_the_ids_are_unique(game_env):
    m = game_env.module
    ids = [r["id"] for r in m.RUMORS]
    assert len(ids) == len(set(ids)) == 12
    for rumor in m.RUMORS:
        assert "\n" not in rumor["text"] and 20 < len(rumor["text"]) < 160
    assert "reports record Belt yields" in m.RUMOR_BY_ID["world:AsteroidBelt"]["text"]


def test_rumours_survive_a_save_and_unknown_ones_are_dropped(game_env):
    m = game_env.module
    _reveal(m, 4)
    saved = m.serialize_state()
    assert "rumor:met:helios" in saved["story_log"]
    saved["story_log"] = saved["story_log"] + ["rumor:nope", "rumor:met:helios"]
    m.story_log.clear()
    m.deserialize_state(saved)
    assert m.story_log.count("rumor:met:helios") == 1 and "rumor:nope" not in m.story_log


# --- the panel ------------------------------------------------------------------------------------------


def test_the_panel_offers_share_and_take_over_on_a_rival_point(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.earth["resource_count"] = 400
    game_env.elements["observatory-toggle-button"].dispatch("click")
    text = _panel_text(game_env)
    assert "Held by Helios Combine" in text and "8% less ecology" in text
    share, take = _buttons(game_env, "Share it")[0], _buttons(game_env, "Take it over")[0]
    assert "300 Iron" in share.innerText and share.disabled is False
    assert "800" in take.innerText and take.disabled is True  # only 400 banked
    game_env.panel_click("observatory-panel", action="partner", point="cairn")
    text = _panel_text(game_env)
    assert "Shared with Helios Combine" in text and "Take it over" in text
    assert "Ticker: Helios Combine and you now share Cairn" in text


def test_the_rival_section_names_only_rivals_you_have_met_and_explains_the_pressure(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.elements["observatory-toggle-button"].dispatch("click")
    text = _panel_text(game_env)
    assert "Helios Combine" in text and "Ceres Freight Guild" not in text and "Outer Reach" not in text
    assert text.count("A rival") == 2 and "Not met yet" in text
    assert "Rival pressure: trade routes restore 8% less ecology on worlds with no Focus" in text
    assert "A Focus on a world" in text


def test_the_overview_says_which_worlds_are_pressured(game_env):
    m = game_env.module
    game_env.unlock_tier(1)
    _reveal(m, 4)
    game_env.elements["overview-toggle-button"].dispatch("click")
    m.tick()
    texts = "\n".join(t for t in _texts(game_env.elements["overview-panel"]) if t)
    assert "Rival pressure: trade restores 8% less" in texts


# --- saves and the achievement ---------------------------------------------------------------------------


def test_partner_state_round_trips_and_is_rejected_where_there_is_no_rival(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.earth["resource_count"] = 5000
    m.claim_point("harbour_light")
    m.partner_point("cairn")
    saved = m.serialize_state()
    assert saved["point_claims"] == {"harbour_light": "yours", "cairn": "partner"}
    m.point_claims.clear()
    m.deserialize_state(saved)
    assert m.point_state("cairn") == "partner" and m.point_state("harbour_light") == "yours"
    saved["point_claims"] = {"harbour_light": "partner", "cairn": "bogus"}
    m.deserialize_state(saved)
    assert m.point_claims == {}
    assert m.point_state("cairn") == "rival" and m.point_state("harbour_light") == "open"


def test_relay_network_needs_all_four_points_held_or_shared(game_env):
    m = game_env.module
    assert "relay_network" not in m.achievement_ids_earned()
    m.survey_data = 100
    while m.survey_region():
        pass
    game_env.earth["resource_count"] = 50000
    m.claim_point("harbour_light")
    m.partner_point("cairn")
    m.contest_point("meridian")
    assert "relay_network" not in m.achievement_ids_earned()
    assert m.ACHIEVEMENT_PROGRESS["relay_network"]() == (3, 4)
    m.partner_point("far_anchor")
    assert "relay_network" in m.achievement_ids_earned()
    for planet in m.PLANETS:
        m.planet_state[planet]["terraform_progress"] = m.TERRAFORM_MAX
    game_env.prestige()
    assert "relay_network" in m.achievement_ids_earned()  # points are lifetime, a prestige keeps them


def test_rival_blurbs_keep_their_capital_letters(game_env):
    m = game_env.module
    _reveal(m, 4)
    game_env.elements["observatory-toggle-button"].dispatch("click")
    text = _panel_text(game_env)
    assert "Inner-system haulers, fond of Mars and the Moon." in text
