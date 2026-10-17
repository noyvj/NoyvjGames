"""2026-10-09 pass, part 2 of 2: GD-8 Trade Winds, GD-11 crew, D-11 autosave history, D-5 Workshop, GD-9 postcard, GD-12
Acid Tide boss, GD-3 storm bracing. Part 1 is test_oct9_pass.py."""

import pytest


@pytest.fixture
def storage(game_env, monkeypatch):
    store = {}
    monkeypatch.setattr(game_env.module, "_read_local_storage_item", lambda key: store.get(key))
    monkeypatch.setattr(game_env.module, "_write_local_storage_item", lambda key, value: store.__setitem__(key, value))
    return store


# ---- GD-8 Trade Winds ----

def _to_season(s, n):
    while s.season < n:
        s.advance_season()
        s.market_event = None if s.season != n else s.market_event


def test_a_deal_is_offered_every_fourth_season_and_telegraphed_before(game_env):
    m = game_env.module
    s = m.state
    for _ in range(2):
        s.advance_season()
    assert s.season == 3 and s.market_event is None and "next season" in s.market_telegraph_text()
    s.advance_season()
    assert s.season == m.MARKET_EVERY and s.market_event is not None
    assert s.market_event["kind"] in m.MARKET_KINDS
    assert "Trade Winds" in s.market_offer_text() and any("Trade Winds" in line for line in s.ticker_log)
    assert s.market_telegraph_text() == ""


def test_an_unanswered_deal_lapses_when_the_next_season_resolves(game_env):
    m = game_env.module
    s = m.state
    for _ in range(m.MARKET_EVERY - 1):
        s.advance_season()
    assert s.market_event is not None
    s.advance_season()
    assert s.market_event is None and any("lapsed" in line for line in s.ticker_log)


def test_insurance_is_only_offered_when_a_row_has_flooded(game_env):
    m = game_env.module
    s = m.state
    s.sea_level = 0.0
    assert all(s._market_kind_for(season) != "insurance" for season in range(4, 80, 4))
    s.sea_level = m.row_flood_threshold(m.COASTLINE_ROWS - 1) + 1
    assert any(s._market_kind_for(season) == "insurance" for season in range(4, 80, 4))


def test_gains_scale_with_diversification(game_env):
    m = game_env.module
    s = m.state
    base_export, base_tour = s._market_gain("export"), s._market_gain("tourism")
    s.diversification["aquaculture"] = 2
    s.diversification["tourism"] = 2
    assert s._market_gain("export") > base_export and s._market_gain("tourism") == base_tour + 50


def test_accepting_pays_and_charges_the_price_declining_does_neither(game_env):
    m = game_env.module
    s = m.state
    s.market_event = {"kind": "export", "gain": 40.0, "season": 4}
    funds, acid = s.funds, s.acidity
    assert s.answer_market(True) is True
    assert s.funds == funds + 40 and s.acidity == pytest.approx(acid + 0.6) and s.market_accepted == 1 and s.market_event is None
    s.market_event = {"kind": "tourism", "gain": 25.0, "season": 8}
    s.answer_market(True)
    assert s.income_dip_seasons == 1
    s.market_event = {"kind": "insurance", "gain": 20.0, "season": 12}
    s.answer_market(True)
    assert s.income_dip_seasons == 2
    s.market_event = {"kind": "export", "gain": 99.0, "season": 16}
    funds = s.funds
    s.answer_market(False)
    assert s.funds == funds and s.market_accepted == 3
    assert s.answer_market(True) is False  # nothing on the table


def test_the_dip_trims_income_for_that_many_seasons(game_env):
    m = game_env.module
    s = m.state
    s.capacity["output"] = 10
    s.funds = 100
    s.income_dip_seasons = 1
    s.advance_season()
    dipped = s.funds - 100
    s.funds = 100
    s.advance_season()
    normal = s.funds - 100
    assert dipped == pytest.approx(normal * m.MARKET_DIP_FACTOR, rel=0.05) and s.income_dip_seasons == 0


def test_panel_and_buttons(game_env):
    m = game_env.module
    s = m.state
    m.render()
    assert game_env.elements["market-panel"].hidden is True
    s.season = 3
    m.render()
    assert game_env.elements["market-panel"].hidden is False and game_env.elements["market-accept-button"].hidden is True
    s.market_event = {"kind": "tourism", "gain": 50.0, "season": 4}
    s.season = 4
    m.render()
    assert game_env.elements["market-accept-button"].hidden is False and "tourism boom" in game_env.elements["market-text"].innerText
    funds = s.funds
    game_env.elements["market-accept-button"].dispatch("click", None)
    assert s.funds == funds + 50 and game_env.elements["market-accept-button"].hidden is True


def test_market_state_saves_and_validates(game_env):
    m = game_env.module
    s = m.state
    assert "market" not in m.get_state()
    s.market_event = {"kind": "export", "gain": 33.0, "season": 4}
    s.market_accepted, s.income_dip_seasons = 2, 1
    saved = m.get_state()
    s.market_event, s.market_accepted, s.income_dip_seasons = None, 0, 0
    m.load_state(saved)
    assert s.market_event == {"kind": "export", "gain": 33.0, "season": 4} and (s.market_accepted, s.income_dip_seasons) == (2, 1)
    saved["market"] = {"event": {"kind": "piracy", "gain": 5, "season": 4}, "accepted": -3, "dip": 99}
    m.load_state(saved)
    assert s.market_event is None and s.market_accepted == 0 and s.income_dip_seasons == 2


# ---- GD-11 crew ----

def test_hiring_costs_a_fee_and_respects_the_cap_and_funds(game_env):
    m = game_env.module
    s = m.state
    s.funds = 1000
    assert s.hire("biologist") is True and s.funds == 1000 - m.CREW_HIRE_COST
    assert s.hire("biologist") is False and s.hire("pirate") is False
    s.hire("engineer")
    s.hire("broker")
    assert len(s.crew) == m.CREW_MAX
    s.crew.remove("broker")
    s.funds = m.CREW_HIRE_COST - 1
    assert s.hire("broker") is False
    assert s.dismiss("engineer") is True and s.dismiss("engineer") is False


def test_the_biologist_shortens_the_fish_lag_by_one_season(game_env):
    m = game_env.module
    s = m.state
    assert s._effective_fish_lag() == m.FISH_LAG_SEASONS
    s.crew = ["biologist"]
    assert s._effective_fish_lag() == m.FISH_LAG_SEASONS - 1
    s.hard_lag_mode = True
    assert s._effective_fish_lag() == m.FISH_LAG_SEASONS_HARD - 1


def test_the_engineer_cuts_adaptation_costs_and_stacks_with_the_domino_discount(game_env):
    m = game_env.module
    s = m.state
    assert s.invest_cost("adaptation") == 30
    s.crew = ["engineer"]
    assert s.invest_cost("adaptation") == 26  # 30 less 15%, rounded up
    assert s.invest_cost("output") == m.INVEST_COST["output"]
    s.domino_seasons_left = 1
    assert s.invest_cost("adaptation") == 20  # 30 x 0.75 x 0.85, rounded up


def test_wages_are_paid_each_season_and_shown_in_the_breakdown(game_env):
    m = game_env.module
    s = m.state
    s.funds = 100
    s.crew = ["engineer", "broker"]
    s.advance_season()
    assert s.funds == pytest.approx(100 - 2 * m.CREW_WAGE)
    assert dict(s.last_breakdown["funds"]["parts"])["Crew wages"] == pytest.approx(-2 * m.CREW_WAGE)
    s.funds = 3
    s.advance_season()
    assert s.funds >= 0


def test_the_broker_improves_deals_and_the_offer_text_says_so(game_env):
    m = game_env.module
    s = m.state
    s.market_event = {"kind": "tourism", "gain": 100.0, "season": 4}
    plain_text = s.market_offer_text()
    assert "100 funds" in plain_text and "10%" in plain_text
    s.crew = ["broker"]
    assert "130 funds" in s.market_offer_text() and "no income dip" in s.market_offer_text()
    funds = s.funds
    s.answer_market(True)
    assert s.funds == pytest.approx(funds + 130) and s.income_dip_seasons == 0
    s.market_event = {"kind": "insurance", "gain": 10.0, "season": 8}
    s.answer_market(True)
    assert s.income_dip_seasons == 1


def test_crew_buttons_and_status(game_env):
    m = game_env.module
    s = m.state
    s.funds = 500
    m.render()
    assert "No crew hired" in game_env.elements["crew-text"].innerText
    assert game_env.elements["crew-biologist-button"].innerText.startswith("Hire a Marine Biologist")
    game_env.elements["crew-biologist-button"].dispatch("click", None)
    assert s.crew == ["biologist"] and "Dismiss the Marine Biologist" in game_env.elements["crew-biologist-button"].innerText
    assert "Crew: Marine Biologist" in game_env.elements["crew-text"].innerText
    s.funds = 10
    m.render()
    assert game_env.elements["crew-engineer-button"].disabled is True
    assert game_env.elements["crew-biologist-button"].disabled is False  # dismissing is always possible


def test_crew_saves_and_validates(game_env):
    m = game_env.module
    s = m.state
    assert "crew" not in m.get_state()
    s.crew = ["engineer", "broker"]
    saved = m.get_state()
    s.crew = []
    m.load_state(saved)
    assert s.crew == ["engineer", "broker"]
    saved["crew"] = ["broker", "broker", "pirate", "biologist", "engineer", 4]
    m.load_state(saved)
    assert s.crew == ["broker", "biologist", "engineer"]
    saved["crew"] = "oops"
    m.load_state(saved)
    assert s.crew == []


# ---- D-11 autosave history ----

def test_each_season_keeps_a_slot_and_only_the_last_three(game_env, storage):
    m = game_env.module
    for _ in range(5):
        m.on_advance_season()
    slots = m.load_autosaves()
    assert [s["season"] for s in slots] == [4, 5, 6]
    assert all(isinstance(s["state"], dict) and "funds" in s["state"] for s in slots)


def test_x5_stores_one_slot_for_the_end_state(game_env, storage):
    m = game_env.module
    m.on_advance_x5()
    slots = m.load_autosaves()
    assert len(slots) == 1 and slots[0]["season"] == m.state.season


def test_restoring_goes_back_and_clears_the_failed_flag(game_env, storage):
    m = game_env.module
    for _ in range(4):
        m.on_advance_season()
    target = m.load_autosaves()[0]
    m._autosave_info["load_failed"] = True
    assert m.restore_autosave(0) is True
    assert m.state.season == target["season"] and m._autosave_info["load_failed"] is False
    assert any("Restored the autosave" in line for line in m.state.ticker_log)
    assert m.restore_autosave(9) is False and m.restore_autosave(-1) is False


def test_an_unreadable_load_opens_the_panel_and_explains(game_env, storage):
    m = game_env.module
    m.on_advance_season()
    assert m.load_state("not a dict") is False
    m.render()
    assert game_env.elements["autosave-panel"].open is True
    assert "could not be read" in game_env.elements["autosave-note"].innerText
    assert game_env.elements["autosave-list"].children and "Restore Season" in game_env.elements["autosave-list"].children[0].innerText


def test_buttons_restore_the_slot_they_name(game_env, storage):
    m = game_env.module
    for _ in range(3):
        m.on_advance_season()
    m.render()
    buttons = game_env.elements["autosave-list"].children
    assert [b.getAttribute("data-slot") for b in buttons][0] == str(len(buttons) - 1)  # newest first
    oldest = buttons[-1]

    class _Event:
        target = oldest

    m.on_autosave_click(_Event())
    assert m.state.season == m.load_autosaves()[int(oldest.getAttribute("data-slot"))]["season"]


def test_bad_or_oversized_slots_are_ignored(game_env, storage, monkeypatch):
    m = game_env.module
    storage[m.AUTOSAVE_KEY] = "garbage"
    assert m.load_autosaves() == []
    storage[m.AUTOSAVE_KEY] = '[{"season": "x", "funds": 1, "state": {}}, {"season": 3, "funds": 5.5, "state": {"a": 1}}, 7]'
    assert [s["season"] for s in m.load_autosaves()] == [3]
    monkeypatch.setattr(m, "AUTOSAVE_MAX_BYTES", 10)
    assert m.record_autosave() is False


def test_empty_state_says_so(game_env, storage):
    m = game_env.module
    m.render()
    assert "No autosaves yet" in game_env.elements["autosave-list"].innerText


# ---- D-5 Workshop ----

def test_defaults_change_nothing(game_env):
    m = game_env.module
    s = m.state
    assert s.workshop_active() is False and s.workshop == m.WORKSHOP_DEFAULTS
    assert s.sea_rise_per_season() == m.SEA_SCENARIOS[s.sea_scenario]["rise"]
    assert s._effective_fish_lag() == m.FISH_LAG_SEASONS
    assert m.workshop_rating(m.WORKSHOP_DEFAULTS)[1] == "Standard"


def test_each_dial_changes_its_own_rule(game_env):
    m = game_env.module
    s = m.state
    base_rise = s.sea_rise_per_season()
    base_surge = s.storm_surge_strength()
    s.workshop.update(rise=2.0, surge=1.5, lag=5)
    assert s.sea_rise_per_season() == pytest.approx(2 * base_rise)
    assert s.storm_surge_strength() == pytest.approx(1.5 * base_surge)
    assert s._effective_fish_lag() == 5
    s.hard_lag_mode = True
    assert s._effective_fish_lag() == 5  # a chosen lag replaces both presets
    s.workshop.update(lag=0)
    s.hard_lag_mode = False
    s.acidity_history = [10.0, 0.0, 0.0]
    normal = s.fish_yield_multiplier()
    s.workshop["fish"] = 2.0
    assert s.fish_yield_multiplier() < normal


def test_values_are_snapped_clamped_and_cleaned(game_env):
    m = game_env.module
    assert m.clean_workshop_value("funds", 333) == 350 and m.clean_workshop_value("funds", 9999) == 600
    assert m.clean_workshop_value("lag", 3.4) == 3 and m.clean_workshop_value("rise", 1.1) == 1.0
    assert m.clean_workshop_value("rise", "x") == 1.0 and m.clean_workshop_value("lag", True) == 0


def test_rating_goes_up_with_harder_dials_and_has_labels(game_env):
    m = game_env.module
    easy = dict(m.WORKSHOP_DEFAULTS, rise=0.5, surge=0.5, fish=0.5, funds=600)
    hard = dict(m.WORKSHOP_DEFAULTS, rise=2.0, surge=2.0, fish=2.0, funds=100, lag=8)
    assert m.workshop_rating(easy)[0] < m.workshop_rating(m.WORKSHOP_DEFAULTS)[0] < m.workshop_rating(hard)[0]
    assert m.workshop_rating(easy)[1] == "Gentle" and m.workshop_rating(hard)[1] == "Brutal"


def test_apply_starts_a_new_run_with_the_funds_and_rules(game_env):
    m = game_env.module
    old = m.state
    m.on_advance_season()
    m.workshop_pending.update(funds=450, rise=1.5)
    m.on_workshop_apply()
    assert m.state is not old and m.state.funds == 450 and m.state.season == 1
    assert m.state.workshop_active() and m.state.workshop["rise"] == 1.5
    assert game_env.elements["custom-rules-badge"].hidden is False
    m.on_workshop_reset()
    assert m.workshop_pending == m.WORKSHOP_DEFAULTS
    m.on_workshop_apply()
    assert m.state.workshop_active() is False and m.state.funds == m.STARTING_FUNDS


def test_custom_rule_runs_stay_out_of_best_almanac_and_library(game_env, storage):
    m = game_env.module
    m.workshop_pending.update(rise=0.5)
    m.on_workshop_apply()
    s = m.state
    s.capacity["adaptation"] = 10
    for _ in range(6):
        s.advance_season()
    m.render()
    assert m.BEST_COASTLINE_STORAGE_KEY not in storage
    assert m.almanac["seasons"] == 0
    assert m.library_save_current() is False and "custom Workshop rules" in m._library_status


def test_slider_events_stage_values_and_the_status_text(game_env):
    m = game_env.module
    game_env.elements["workshop-surge"].value = "2"
    m.on_workshop_slider("surge")()
    assert m.workshop_pending["surge"] == 2.0
    text = game_env.elements["workshop-status"].innerText
    assert "custom rules" in text and "Apply starts a new run" in text and "standard rules" in text


def test_workshop_saves_only_when_custom_and_validates(game_env):
    m = game_env.module
    s = m.state
    assert "workshop" not in m.get_state()
    s.workshop.update(rise=1.5, funds=400)
    saved = m.get_state()
    s.workshop = dict(m.WORKSHOP_DEFAULTS)
    m.load_state(saved)
    assert s.workshop["rise"] == 1.5 and s.workshop["funds"] == 400
    saved["workshop"] = {"rise": 99, "lag": "x", "funds": -5, "surge": None}
    m.load_state(saved)
    assert s.workshop == dict(m.WORKSHOP_DEFAULTS, rise=2.0, funds=100)
    saved["workshop"] = "nope"
    m.load_state(saved)
    assert s.workshop == m.WORKSHOP_DEFAULTS


# ---- GD-9 postcard ----

def test_grade_follows_how_the_harbour_did(game_env):
    m = game_env.module
    s = m.state
    s.population = s.peak_population = 100
    best = m.postcard_score()
    assert m.postcard_grade(best) == "S"
    s.sea_level = m.row_flood_threshold(0) + 1  # everything flooded
    s.population = 20
    assert m.postcard_score() < best and m.postcard_grade() != "S"
    s.fish_yield_multiplier = lambda: 0.2
    s.population = 0
    s.undampened_damage_total, s.cumulative_damage = 100.0, 100.0
    assert m.postcard_grade() in ("D", "E")
    assert [m.postcard_grade(x) for x in (0.95, 0.8, 0.65, 0.5, 0.35, 0.1)] == list(m.POSTCARD_GRADES)


def test_nicknames_come_from_the_real_state(game_env):
    m = game_env.module
    s = m.state
    assert m.postcard_nickname() == "The Stubborn Harbour"
    s.crew = ["engineer", "broker"]
    assert m.postcard_nickname() == "The Busy Harbour"
    for site in m.HERITAGE_SITES:
        s.heritage[site["id"]] = m.HERITAGE_PROTECTED
    assert m.postcard_nickname() == "Keeper of Lights"
    s.capacity["adaptation"] = 10
    assert m.postcard_nickname() == "The Unflooded"
    s.ironman_earned = True
    assert m.postcard_nickname() == "The Anchor That Held"
    s.ironman_earned = False
    s.sea_level = m.row_flood_threshold(0) + 1
    assert m.postcard_nickname() == "The Drowned Quay"
    assert set(m.postcard_nickname() for _ in range(1)) <= set(m.POSTCARD_NICKNAMES)


def test_the_svg_is_valid_and_shows_flooded_rows_as_sunken_roofs(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    s = m.state
    dry = m.postcard_svg()
    ET.fromstring(dry)
    s.sea_level = m.row_flood_threshold(m.COASTLINE_ROWS - 1) + 1
    s.settlement_name = "Port <Regret>"
    wet = m.postcard_svg()
    ET.fromstring(wet)
    assert "#1a5876" in wet and "#1a5876" not in dry and "Port &lt;Regret&gt;" in wet
    assert f"grade {m.postcard_grade()}" in wet


def test_the_gallery_collects_each_variant_once_and_needs_a_few_seasons(game_env, storage):
    m = game_env.module
    assert m.collect_postcard() == "early"
    for _ in range(4):
        m.state.advance_season()
    assert m.collect_postcard() == "new"
    assert m.collect_postcard() == "seen"
    assert len(m.load_postcards()) == 1 and "1 of 42" in m.gallery_text()
    m.state.sea_level = m.row_flood_threshold(0) + 1
    assert m.collect_postcard() == "new" and len(m.load_postcards()) == 2


def test_custom_rule_runs_do_not_fill_the_gallery(game_env, storage):
    m = game_env.module
    for _ in range(4):
        m.state.advance_season()
    m.state.workshop["rise"] = 0.5
    assert m.collect_postcard() == "early"


def test_bad_gallery_data_is_ignored(game_env, storage):
    m = game_env.module
    storage[m.POSTCARD_KEY] = "junk"
    assert m.load_postcards() == []
    storage[m.POSTCARD_KEY] = '[{"grade": "Z", "nickname": "The Stubborn Harbour"}, {"grade": "A", "nickname": "Made Up"}, {"grade": "B", "nickname": "The Quiet Nets", "season": 7}, 5]'
    cards = m.load_postcards()
    assert len(cards) == 1 and cards[0]["season"] == 7


def test_button_and_panel(game_env, storage):
    m = game_env.module
    m.session_summary_open = True
    m.render()
    assert "<svg" in game_env.elements["postcard-view"].innerHTML and "0 of 42" in game_env.elements["postcard-gallery"].innerText
    game_env.elements["postcard-button"].dispatch("click", None)
    assert "Play at least" in game_env.elements["postcard-status"].innerText
    for _ in range(4):
        m.state.advance_season()
    game_env.elements["postcard-button"].dispatch("click", None)
    assert "new postcard variant" in game_env.elements["postcard-status"].innerText
    game_env.elements["postcard-button"].dispatch("click", None)
    assert "already have" in game_env.elements["postcard-status"].innerText
    m.session_summary_open = False
    m.render()
    assert game_env.elements["postcard-view"].innerHTML == ""


# ---- GD-12 Acid Tide boss ----

def _to_boss_season(s, m):
    while s.season < m.ACID_BOSS_SEASON:
        s.advance_season()


def test_nothing_happens_with_the_boss_off(game_env):
    m = game_env.module
    s = m.state
    _to_boss_season(s, m)
    s.advance_season()
    assert s.acid_boss_result == "" and s.acidity == 0.0
    assert "boss is off" in m.acid_boss_text()


def test_an_unbraced_harbour_takes_the_spike(game_env):
    m = game_env.module
    s = m.state
    s.acid_boss_mode = True
    _to_boss_season(s, m)
    before = s.acidity
    s.advance_season()
    assert s.acid_boss_result == "hit" and s.acidity == pytest.approx(before + m.ACID_BOSS_SPIKE)
    assert s.acidity_history[-1] == pytest.approx(s.acidity)
    assert any("Acid Tide struck" in line for line in s.ticker_log)
    assert s.fish_yield_multiplier() <= 1.0


def test_bracing_needs_funds_and_reduction_and_absorbs_the_spike(game_env):
    m = game_env.module
    s = m.state
    s.acid_boss_mode = True
    s.funds = 1000
    assert s.can_brace() is False  # no reduction yet
    s.capacity["reduction"] = m.ACID_BRACE_MIN_REDUCTION
    assert s.can_brace() is True
    funds = s.funds
    assert s.brace_for_acid_tide() is True and s.funds == funds - m.ACID_BRACE_COST
    assert s.brace_for_acid_tide() is False
    s.funds = 100000
    _to_boss_season(s, m)
    before = s.acidity
    s.advance_season()
    assert s.acid_boss_result == "survived" and s.acidity <= before
    assert any("harbour held" in line for line in s.ticker_log)


def test_the_boss_only_happens_once(game_env):
    m = game_env.module
    s = m.state
    s.acid_boss_mode = True
    _to_boss_season(s, m)
    s.advance_season()
    acidity = s.acidity
    s.season = m.ACID_BOSS_SEASON
    s._resolve_acid_boss()
    assert s.acidity == acidity
    assert s.acid_boss_pending() is False


def test_the_warning_text_and_buttons(game_env):
    m = game_env.module
    s = m.state
    s.acid_boss_mode = True
    m.render()
    assert "A warning will appear" in game_env.elements["acid-boss-text"].innerText
    s.season = m.ACID_BOSS_SEASON - 4
    m.render()
    assert "surge in 4 seasons" in game_env.elements["acid-boss-text"].innerText
    assert game_env.elements["acid-boss-brace-button"].hidden is False and game_env.elements["acid-boss-brace-button"].disabled is True
    s.funds, s.capacity["reduction"] = 500, 8
    m.render()
    game_env.elements["acid-boss-brace-button"].dispatch("click", None)
    assert s.acid_braced is True and "Braced." in game_env.elements["acid-boss-text"].innerText
    game_env.elements["acid-boss-toggle-button"].dispatch("click", None)
    assert s.acid_boss_mode is False


def test_surviving_upgrades_the_recovery_banner(game_env):
    m = game_env.module
    s = m.state
    s.acid_boss_result = "survived"
    s.recovery_celebrated_season = s.season
    m.render()
    assert "Victory!" in game_env.elements["fish-recovery-banner"].innerText
    s.acid_boss_result = ""
    m.render()
    assert "Recovery!" in game_env.elements["fish-recovery-banner"].innerText


def test_boss_state_saves_and_validates(game_env):
    m = game_env.module
    s = m.state
    assert "acid_boss" not in m.get_state()
    s.acid_boss_mode, s.acid_braced = True, True
    saved = m.get_state()
    s.acid_boss_mode, s.acid_braced = False, False
    m.load_state(saved)
    assert s.acid_boss_mode is True and s.acid_braced is True and s.acid_boss_result == ""
    saved["acid_boss"] = {"mode": "yes", "braced": 1, "result": "exploded"}
    m.load_state(saved)
    assert (s.acid_boss_mode, s.acid_braced, s.acid_boss_result) == (False, False, "")
    saved["acid_boss"] = {"mode": True, "result": "hit"}
    m.load_state(saved)
    assert s.acid_boss_result == "hit"


# ---- GD-3 storm bracing ----

def _storm_ready(m):
    s = m.state
    s.set_storm_mode(True)
    s.funds = 1000
    s.season = m.STORM_INTERVAL - 1  # a storm is within the brace window
    return s


def test_bracing_is_only_open_in_the_window_before_a_storm(game_env):
    m = game_env.module
    s = m.state
    assert s.can_brace_storm() is False and s.add_brace("barriers") is False
    s.set_storm_mode(True)
    s.season = 1
    assert s.can_brace_storm() is (s.seasons_until_storm() <= m.BRACE_WINDOW)
    _storm_ready(m)
    assert s.can_brace_storm() is True


def test_commitments_cost_funds_and_stay_capped_by_what_you_have(game_env):
    m = game_env.module
    s = _storm_ready(m)
    assert s.add_brace("barriers") and s.add_brace("stockpile") and s.add_brace("evacuate")
    assert s.funds == 1000 - 2 * m.BRACE_STEP - m.EVACUATE_COST
    assert s.add_brace("evacuate") is False  # once only
    s.funds = 5
    assert s.add_brace("barriers") is False
    assert s.add_brace("nonsense") is False


def test_evacuate_needs_an_exposed_site(game_env):
    m = game_env.module
    s = _storm_ready(m)
    for site in m.HERITAGE_SITES:
        s.heritage[site["id"]] = m.HERITAGE_PROTECTED
    assert s.add_brace("evacuate") is False


def test_barriers_hold_back_more_surge_and_the_storm_is_graded(game_env):
    m = game_env.module
    s = _storm_ready(m)
    s.season = m.STORM_INTERVAL
    plain = m.copy.deepcopy(s)
    s._resolve_storm()
    unbraced_taken = s.storm_log[-1]["taken"]
    t = plain
    m.state = t
    t.season = m.STORM_INTERVAL
    t.brace["barriers"] = 50
    t._resolve_storm()
    m.state = s
    assert t.storm_log[-1]["taken"] == pytest.approx(max(0.0, unbraced_taken - 10))
    assert t.last_storm_result in [label for _l, label in m.STORM_RESULT_TIERS]
    assert t.brace == {"barriers": 0, "stockpile": 0, "evacuate": False}


def test_result_tiers(game_env):
    m = game_env.module
    s = _storm_ready(m)
    s.season = m.STORM_INTERVAL
    s.capacity["adaptation"] = 15  # barriers tier, 95% dampening
    s._resolve_storm()
    assert s.last_storm_result == "Shrugged Off"
    s.capacity["adaptation"] = 0
    s.workshop["surge"] = 1.0
    s._resolve_storm()
    assert s.last_storm_result == "Breached"
    s.capacity["adaptation"] = 6
    s.storm_log = []
    s._resolve_storm()
    assert s.last_storm_result in ("Battered", "Shrugged Off")


def test_a_breach_loses_unprotected_sites_unless_evacuated(game_env):
    m = game_env.module
    s = _storm_ready(m)
    s.season = m.STORM_INTERVAL
    s.brace["evacuate"] = True
    s._resolve_storm()
    assert s.last_storm_result == "Breached"
    assert all(v == m.HERITAGE_UNPROTECTED for v in s.heritage.values())
    s.brace["evacuate"] = False
    s._resolve_storm()
    assert all(v == m.HERITAGE_LOST for v in s.heritage.values())


def test_the_stockpile_absorbs_cost_and_the_rest_comes_back(game_env):
    m = game_env.module
    s = _storm_ready(m)
    s.season = m.STORM_INTERVAL
    s.capacity["adaptation"] = 10
    s.funds = 500
    s.brace["stockpile"] = 1000
    s._resolve_storm()
    taken = s.storm_log[-1]["taken"]
    expected_loss = taken * m.STORM_FUNDS_PER_DAMAGE
    assert s.funds == pytest.approx(500 + 1000 - expected_loss)


def test_panel_text_buttons_and_state_round_trip(game_env):
    m = game_env.module
    s = _storm_ready(m)
    m.render()
    assert game_env.elements["brace-panel"].hidden is False
    game_env.elements["brace-barriers-button"].dispatch("click", None)
    assert s.brace["barriers"] == m.BRACE_STEP and "barriers 10" in game_env.elements["brace-text"].innerText
    saved = m.get_state()
    s.brace = {"barriers": 0, "stockpile": 0, "evacuate": False}
    m.load_state(saved)
    assert s.brace["barriers"] == m.BRACE_STEP
    saved["brace"] = {"barriers": 7, "stockpile": -10, "evacuate": "yes"}
    saved["storm_result"] = "Obliterated"
    m.load_state(saved)
    assert s.brace == {"barriers": 0, "stockpile": 0, "evacuate": False} and s.last_storm_result == ""
    s.set_storm_mode(False)
    m.render()
    assert game_env.elements["brace-panel"].hidden is True


# ---- GD-4 Tidal Chess ----

def test_chess_can_only_be_switched_on_before_the_first_season(game_env):
    m = game_env.module
    s = m.state
    assert s.set_chess_mode(True) is True and s.workshop_active() is True
    s.advance_season()
    assert s.set_chess_mode(False) is False and s.chess_mode is True


def test_half_the_output_acidity_arrives_two_seasons_late(game_env):
    m = game_env.module
    s = m.state
    s.set_chess_mode(True)
    s.capacity["output"] = 4
    full = 4 * m.ACIDITY_RISE_PER_OUTPUT
    s.advance_season()
    assert s.acidity == pytest.approx(full * (1 - m.CHESS_RUNOFF_SHARE))
    s.advance_season()
    s.advance_season()
    # the first season's late share has now arrived on top of this season's immediate share
    assert s.acidity_history[2] - s.acidity_history[1] == pytest.approx(full * (1 - m.CHESS_RUNOFF_SHARE) + full * m.CHESS_RUNOFF_SHARE)


def test_dips_are_counted_and_the_acidity_readouts_are_hidden_by_attribute(game_env):
    m = game_env.module
    s = m.state
    s.set_chess_mode(True)
    s.acidity_history = [40.0] * 6
    s.advance_season()
    assert s.chess_dips >= 1
    m.render()
    assert "fewer is better" in game_env.elements["chess-text"].innerText
    root = getattr(m.document, "documentElement", None)
    if root is not None:
        assert root.getAttribute("data-tidal-chess") == "on"
    assert game_env.elements["chess-toggle-button"].disabled is True


def test_chess_saves_and_validates_and_stays_out_of_the_almanac(game_env, storage):
    m = game_env.module
    s = m.state
    assert "chess" not in m.get_state()
    s.set_chess_mode(True)
    s.runoff_queue, s.chess_dips = [1.5, 2.5], 3
    saved = m.get_state()
    s.chess_mode, s.runoff_queue, s.chess_dips = False, [], 0
    m.load_state(saved)
    assert s.chess_mode and s.runoff_queue == [1.5, 2.5] and s.chess_dips == 3
    saved["chess"] = {"on": "yes", "runoff": [1], "dips": 5}
    m.load_state(saved)
    assert s.chess_mode is False and s.runoff_queue == [] and s.chess_dips == 0
    s.set_chess_mode(True)
    for _ in range(3):
        s.advance_season()
    m.render()
    assert m.almanac["seasons"] == 0
