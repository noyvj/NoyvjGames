"""Round-3 Herd batch (planning/TODO.md "GF + F. Herd"): perfect-round streak (GF-15),
lever history (F-17), funds per methane saved (F-13), cap headroom (F-24), breed shelf
(GF-16), combo book (GF-5), rating titles (GF-22), highlights reel (GF-29) and the
aria-live round announcer (F-10, partial)."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _perfect_rounds(env, count, herd=10):
    """Plays `count` rounds that each add less methane than the last and still end up
    richer: first a plain round to set the pace, then one capture unit per round."""
    farm = env.farm
    farm.funds = 5000.0
    farm.herd_size = herd
    env.advance_round()
    for _ in range(count):
        env.invest_decoupling("capture")
        env.advance_round()


# ---- GF-15 perfect-round streak --------------------------------------------------------
def test_a_plain_round_is_never_perfect(game_env):
    game_env.farm.herd_size = 5
    game_env.farm.funds = 1000
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.farm.last_round_perfect is False
    assert game_env.farm.perfect_streak == 0


def test_investing_each_round_builds_a_streak(game_env):
    _perfect_rounds(game_env, 2)
    assert game_env.farm.perfect_streak == 2
    assert game_env.farm.last_round_perfect is True


def test_streak_needs_funds_to_rise_as_well(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 5000.0
    farm.herd_size = 10
    game_env.advance_round()
    # Buy so much that funds end the round lower than the round before.
    farm.decoupling_investment["capture"] = 1
    farm.funds -= 2000
    game_env.advance_round()
    assert farm.methane_history[-1] - farm.methane_history[-2] < farm.methane_history[-2]
    assert farm.last_round_perfect is False
    assert farm.perfect_streak == 0
    assert m.PERFECT_STREAK_BONUSES  # constants exist


def test_streak_bonus_pays_the_real_farm_only(game_env):
    m = game_env.module
    farm = game_env.farm
    _perfect_rounds(game_env, 2)
    game_env.invest_decoupling("capture")
    funds_before = farm.funds
    game_env.advance_round()
    assert farm.perfect_streak == 3
    bonus = m.PERFECT_STREAK_BONUSES[3]
    income_only = farm.funds - bonus - funds_before
    assert income_only > 0
    assert farm.funds_history[-1] == farm.funds  # history records the post-bonus figure
    assert farm.counterfactual_funds < farm.funds


def test_streak_resets_when_a_round_is_not_perfect(game_env):
    _perfect_rounds(game_env, 2)
    game_env.advance_round()  # no purchase: same methane as the round before
    assert game_env.farm.perfect_streak == 0
    assert game_env.farm.best_perfect_streak == 2


def test_streak_message_names_the_next_bonus(game_env):
    m = game_env.module
    _perfect_rounds(game_env, 1)
    text = m.streak_message()
    assert "streak: 1" in text and "Bonus at 3" in text


def test_streak_and_best_round_trip_through_a_save(game_env):
    m = game_env.module
    _perfect_rounds(game_env, 2)
    state = m.get_state()
    assert state["perfect_streak"] == 2 and state["best_perfect_streak"] == 2
    m.farm.perfect_streak = 0
    m.farm.best_perfect_streak = 0
    assert m.load_state(state)
    assert m.farm.perfect_streak == 2 and m.farm.best_perfect_streak == 2


def test_streak_display_hidden_on_round_one(game_env):
    game_env.module.render()
    assert game_env.elements["streak-display"].hidden is True
    game_env.advance_round()
    assert game_env.elements["streak-display"].hidden is False


# ---- F-17 lever history ----------------------------------------------------------------
def test_every_purchase_is_logged_with_round_lever_and_cost(game_env):
    farm = game_env.farm
    farm.funds = 1000
    game_env.grow_herd()
    game_env.invest_decoupling("capture")
    game_env.advance_round()
    game_env.invest_decoupling("feed")
    assert [(r, k) for r, k, _c in farm.lever_log] == [(1, "herd"), (1, "capture"), (2, "feed")]
    assert farm.lever_log[1][2] == 20


def test_failed_purchases_are_not_logged(game_env):
    game_env.farm.funds = 0
    game_env.grow_herd()
    game_env.invest_decoupling("capture")
    assert game_env.farm.lever_log == []


def test_every_purchase_method_logs_under_a_known_lever_key(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 10000
    farm.certified = True
    farm.herd_size = 6
    farm.grow_herd()
    farm.invest_decoupling("feed")
    farm.invest_plant_pivot()
    farm.grow_poultry()
    farm.invest_poultry("litter")
    farm.invest_poultry("biofilter")
    farm.invest_genetics()
    farm.invest_supply_chain()
    farm.open_satellite()
    farm.grow_satellite()
    farm.retrofit_satellite()
    keys = {entry[1] for entry in farm.lever_log}
    assert keys == {"herd", "feed", "pivot", "poultry", "litter", "biofilter", "genetics", "supply",
                    "satellite_open", "satellite_grow", "satellite_retrofit"}
    assert keys <= set(m.LEVER_LABELS)


def test_log_is_capped(game_env):
    m = game_env.module
    for index in range(m.LEVER_LOG_MAX + 25):
        game_env.farm.log_purchase("feed", 15)
    assert len(game_env.farm.lever_log) == m.LEVER_LOG_MAX


def test_history_list_is_newest_first_and_worded_like_the_spec(game_env):
    m = game_env.module
    game_env.farm.funds = 1000
    game_env.invest_decoupling("capture")
    game_env.advance_round()
    game_env.grow_herd()
    html = m.lever_history_html()
    assert html.index("Grow Herd") < html.index("Capture Systems")
    assert "Round 1: bought Capture Systems (-20)" in html


def test_history_filter_narrows_the_list(game_env):
    m = game_env.module
    game_env.farm.funds = 1000
    game_env.grow_herd()
    game_env.invest_decoupling("capture")
    select = game_env.elements["lever-history-filter"]
    select.value = "capture"
    select.dispatch("change", None)
    list_html = game_env.elements["lever-history-list"].innerHTML
    assert "Capture Systems" in list_html and "Grow Herd" not in list_html
    select.value = "bogus"
    select.dispatch("change", None)
    assert m.lever_history_filter == "all"


def test_empty_history_says_so(game_env):
    assert "Nothing bought yet" in game_env.module.lever_history_html()


def test_history_notes_how_many_earlier_entries_are_not_shown(game_env):
    m = game_env.module
    for _ in range(m.LEVER_HISTORY_SHOWN + 5):
        game_env.farm.log_purchase("feed", 15)
    assert "and 5 earlier" in m.lever_history_html()


def test_lever_log_round_trips_and_bad_entries_are_dropped(game_env):
    m = game_env.module
    game_env.farm.funds = 1000
    game_env.grow_herd()
    state = m.get_state()
    assert state["lever_log"] == [[1, "herd", 20.0]]
    state["lever_log"] += [["x", "feed", 1], [1, "nonsense", 1], [1, "feed"], "junk", [True, "feed", 1], [1, "feed", float("nan")]]
    assert m.load_state(state)
    assert m.farm.lever_log == [[1, "herd", 20.0]]


def test_old_save_without_a_log_loads_with_an_empty_one(game_env):
    m = game_env.module
    state = m.get_state()
    state.pop("lever_log", None)
    assert m.load_state(state)
    assert m.farm.lever_log == []


def test_filter_options_in_both_pages_match_the_lever_labels(game_env):
    m = game_env.module
    for name in ("index.html", "pc.html"):
        html = (GAME_DIR / name).read_text(encoding="utf-8")
        select = html[html.index('id="lever-history-filter"'):]
        select = select[:select.index("</select>")]
        values = re.findall(r'<option value="([^"]+)"', select)
        assert values == ["all"] + list(m.LEVER_LABELS)


# ---- F-13 funds per methane saved --------------------------------------------------------
def test_methane_saved_by_does_not_change_state(game_env):
    farm = game_env.farm
    farm.herd_size = 10
    before = (dict(farm.decoupling_investment), farm.plant_pivot_investment, farm.methane_this_round())
    for key in ("feed", "caps", "capture", "pivot", "litter", "biofilter", "genetics", "satellite_retrofit", "nonsense"):
        farm.methane_saved_by(key)
    assert (dict(farm.decoupling_investment), farm.plant_pivot_investment, farm.methane_this_round()) == before


def test_capture_saves_a_tenth_of_the_herd_methane(game_env):
    farm = game_env.farm
    farm.herd_size = 10
    assert abs(farm.methane_saved_by("capture") - 1.0) < 1e-9
    assert abs(farm.methane_saved_by("feed") - 0.4) < 1e-9


def test_pivot_saving_uses_the_blended_ratio(game_env):
    farm = game_env.farm
    farm.herd_size = 10
    assert farm.methane_saved_by("pivot") > farm.methane_saved_by("capture") * 0.4
    farm.plant_pivot_investment = 12  # at the 60% cap: nothing more to save
    assert farm.methane_saved_by("pivot") == 0.0


def test_lever_without_a_herd_saves_nothing_and_says_so(game_env):
    m = game_env.module
    assert m.lever_efficiency_message("capture", 20) == m.EFFICIENCY_NONE


def test_efficiency_message_is_cost_divided_by_saving(game_env):
    m = game_env.module
    game_env.farm.herd_size = 10
    assert "20.0 funds per methane saved" in m.lever_efficiency_message("capture", 20)
    assert "Saves 1.00 methane/round" in m.lever_efficiency_message("capture", 20)


def test_efficiency_lines_render_on_every_lever_row(game_env):
    game_env.farm.herd_size = 10
    game_env.module.render()
    for key in ("feed", "caps", "capture", "pivot", "litter", "biofilter"):
        assert game_env.elements[f"{key}-efficiency"].innerText
    assert "funds per methane saved" in game_env.elements["capture-efficiency"].innerText


def test_efficiency_uses_the_subsidised_cost(game_env):
    farm = game_env.farm
    farm.herd_size = 10
    farm.subsidy_rounds_left = 3
    game_env.module.render()
    assert "14.0 funds per methane saved" in game_env.elements["capture-efficiency"].innerText


def test_satellite_retrofit_saving_includes_the_network_offset(game_env):
    farm = game_env.farm
    farm.satellite_open = True
    farm.satellite_size = 5
    assert farm.methane_saved_by("satellite_retrofit") > 0


# ---- F-24 cap headroom -----------------------------------------------------------------------
def test_headroom_hidden_when_the_cap_is_off(game_env):
    game_env.module.render()
    assert game_env.module.cap_headroom_message() == ""
    assert game_env.elements["cap-headroom-meter"].hidden is True


def test_headroom_reports_free_methane_and_rounds(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.regional_cap_enabled = True
    farm.herd_size = 5
    farm.round_number = 6  # five animals in five rounds: one a round
    assert farm.cap_headroom() == 15.0
    assert farm.rounds_until_cap() == 15
    text = m.cap_headroom_message()
    assert "15.0 methane/round free" in text and "within 15 rounds" in text


def test_headroom_falls_as_the_herd_grows_and_decoupling_buys_it_back(game_env):
    farm = game_env.farm
    farm.regional_cap_enabled = True
    farm.herd_size = 10
    farm.round_number = 11
    tight = farm.rounds_until_cap()
    farm.decoupling_investment["capture"] = 5
    assert farm.rounds_until_cap() > tight


def test_at_the_cap_the_message_says_growth_is_blocked(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.regional_cap_enabled = True
    farm.herd_size = 20
    assert farm.rounds_until_cap() == 0
    assert "next animal is blocked" in m.cap_headroom_message()


def test_a_static_herd_is_not_close_to_the_cap(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.regional_cap_enabled = True
    assert farm.rounds_until_cap() is None
    assert "not growing" in m.cap_headroom_message()


def test_headroom_bar_width_tracks_cap_use(game_env):
    farm = game_env.farm
    farm.regional_cap_enabled = True
    farm.herd_size = 10
    game_env.module.render()
    assert game_env.elements["cap-headroom-bar"].style.width == "50%"
    assert game_env.elements["cap-headroom-meter"].hidden is False


# ---- GF-16 breed shelf -------------------------------------------------------------------------
def test_first_animal_earns_the_first_breed(game_env):
    m = game_env.module
    assert m.breeds_collected == []
    game_env.farm.funds = 100
    game_env.grow_herd()
    assert "clover_calf" in m.breeds_collected


def test_each_breed_condition_can_be_met(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.herd_size = 25
    farm.decoupling_investment = {"feed": 3, "caps": 3, "capture": 3}
    farm.plant_pivot_investment = 4
    farm.poultry_size = 5
    farm.satellite_open = True
    farm.satellite_size = 3
    farm.certified = True
    m.render()
    assert set(m.breeds_collected) >= {b["id"] for b in m.BREEDS if not b.get("hidden")}


def test_hidden_breed_needs_a_clean_and_happy_herd(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.herd_size = 10
    farm.decoupling_investment = {"feed": 4, "caps": 0, "capture": 5}  # clean but welfare 70
    m.render()
    assert "methane_eater_cow" not in m.breeds_collected
    farm.decoupling_investment = {"feed": 8, "caps": 0, "capture": 5}  # ratio 0.18, welfare 90
    m.render()
    assert "methane_eater_cow" in m.breeds_collected


def test_locked_hidden_breed_shows_a_silhouette_and_a_rumour_not_its_name(game_env):
    m = game_env.module
    html = m.breed_shelf_html()
    assert "Methane-Eater Cow" not in html
    assert "???" in html and "Rumoured" in html
    assert "breed-card--locked" in html


def test_earned_hidden_breed_glows_and_is_named(game_env):
    m = game_env.module
    game_env.farm.herd_size = 10
    game_env.farm.decoupling_investment = {"feed": 8, "caps": 0, "capture": 5}
    m.render()
    html = m.breed_shelf_html()
    assert "Methane-Eater Cow" in html and "breed-card--legend" in html


def test_shelf_and_summary_render_into_the_page(game_env):
    m = game_env.module
    game_env.farm.funds = 100
    game_env.grow_herd()
    assert "Clover Calf" in game_env.elements["breed-shelf-grid"].innerHTML
    assert f"Breeds 1/{len(m.BREEDS)}" in game_env.elements["collection-summary"].innerText


def test_breeds_survive_a_handover_and_a_save(game_env):
    m = game_env.module
    game_env.farm.herd_size = 12
    game_env.farm.certified = True
    m.render()
    owned = list(m.breeds_collected)
    assert "certified_jersey" in owned
    m.hand_over_farm()
    m.render()
    assert set(owned) <= set(m.breeds_collected)
    assert m.get_state()["breeds_collected"] == m.breeds_collected


def test_loading_a_save_records_breeds_but_never_changes_funds(game_env):
    m = game_env.module
    state = m.get_state()
    state.update({"herd_size": 12, "funds": 321.0, "decoupling_investment": {"feed": 3, "caps": 2, "capture": 3}})
    assert m.load_state(state)
    assert m.farm.funds == 321.0
    assert "brindle_belle" in m.breeds_collected and "circular_barn" in m.combos_found


def test_bad_collection_ids_in_a_save_are_dropped(game_env):
    m = game_env.module
    state = m.get_state()
    state["breeds_collected"] = ["clover_calf", "clover_calf", "bogus", 7, None]
    state["combos_found"] = "not a list"
    assert m.load_state(state)
    assert m.breeds_collected[:1] == ["clover_calf"]
    assert "bogus" not in m.breeds_collected and m.breeds_collected.count("clover_calf") == 1
    assert m.combos_found == []


# ---- GF-5 combo book ------------------------------------------------------------------------------
def test_a_combo_pays_once_to_the_real_farm_only(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 500
    farm.decoupling_investment = {"feed": 2, "caps": 0, "capture": 2}
    m.render()
    assert "circular_barn" not in m.combos_found
    counterfactual = farm.counterfactual_funds
    farm.decoupling_investment["capture"] = 3
    funds = farm.funds
    m.render()
    assert "circular_barn" in m.combos_found
    assert farm.funds == funds + m.COMBO_REWARD_FUNDS
    assert farm.counterfactual_funds == counterfactual
    m.render()
    m.render()
    assert farm.funds == funds + m.COMBO_REWARD_FUNDS


def test_combo_book_hides_the_name_until_found_but_shows_the_rule(game_env):
    m = game_env.module
    html = m.combo_book_html()
    assert "Circular Barn" not in html and "3 Capture Systems and 2 Feed Additives." in html
    game_env.farm.decoupling_investment = {"feed": 2, "caps": 0, "capture": 3}
    m.render()
    assert "Circular Barn" in m.combo_book_html()
    assert "combo-card--found" in m.combo_book_html()


def test_two_combos_at_once_both_pay(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 100
    farm.decoupling_investment = {"feed": 2, "caps": 0, "capture": 5}
    m.render()
    assert {"circular_barn", "biogas_baron"} <= set(m.combos_found)
    assert farm.funds == 100 + 2 * m.COMBO_REWARD_FUNDS


def test_every_combo_can_be_found_with_a_reachable_farm(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 0
    farm.decoupling_investment = {"feed": 2, "caps": 3, "capture": 5}
    farm.plant_pivot_investment = 3
    farm.supply_chain_investment = 2
    farm.genetics_active = 2
    farm.poultry_size = 3
    farm.poultry_investment = {"litter": 1, "biofilter": 1}
    farm.satellite_open = True
    farm.satellite_retrofits = 3
    m.render()
    assert len(m.combos_found) == len(m.COMBOS)


def test_combo_reward_text_in_the_page_matches_the_constant(game_env):
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert f'<span class="combo-reward">{game_env.module.COMBO_REWARD_FUNDS}</span>' in html


# ---- GF-22 rating titles --------------------------------------------------------------------------
def test_new_farm_is_a_hobby_farmer_with_the_next_title_named(game_env):
    m = game_env.module
    assert m.rating_index() == 0
    text = m.rating_message()
    assert "Hobby Farmer" in text and "Next, Feed Hand" in text and "10%" in text


def test_rating_climbs_with_decoupling(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.decoupling_investment["capture"] = 1  # 10% decoupled
    assert m.RATING_TITLES[m.rating_index()][0] == "Feed Hand"
    farm.decoupling_investment["capture"] = 3  # 30%
    assert m.RATING_TITLES[m.rating_index()][0] == "Careful Rancher"


def test_ahead_of_the_curve_needs_the_score_lead_too(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.decoupling_investment["capture"] = 4  # 40%
    farm.counterfactual_funds = farm.funds + 1000  # baseline far ahead
    assert m.RATING_TITLES[m.rating_index()][0] == "Careful Rancher"
    farm.counterfactual_funds = farm.funds - 1000
    assert m.RATING_TITLES[m.rating_index()][0] == "Ahead of the Curve"


def test_top_of_the_ladder(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.decoupling_investment = {"feed": 8, "caps": 0, "capture": 5}  # 82% decoupled
    farm.certified = True
    farm.funds = 2000
    farm.counterfactual_funds = 400
    farm.methane = 10
    farm.counterfactual_methane = 100
    assert m.RATING_TITLES[m.rating_index()][0] == "Decoupling Legend"
    assert "top of the ladder" in m.rating_message()


def test_rating_shows_in_the_side_column_and_the_report_card(game_env):
    m = game_env.module
    m.render()
    assert "Rating: Hobby Farmer" in game_env.elements["rating-display"].innerText
    assert "Rating: Hobby Farmer" in m.report_card_html()


def test_rating_is_display_only(game_env):
    m = game_env.module
    before = json.dumps(m.get_state(), sort_keys=True)
    m.rating_message()
    m.report_card_html()
    assert json.dumps(m.get_state(), sort_keys=True) == before


# ---- GF-29 highlights reel -------------------------------------------------------------------------
def test_reel_waits_for_the_first_round(game_env):
    m = game_env.module
    assert m.highlights_lines() == [m.RATING_FIRST_MESSAGE]


def test_reel_names_the_biggest_round_and_best_methane_cut(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 5000
    farm.herd_size = 10
    game_env.advance_round()
    game_env.invest_decoupling("capture")
    game_env.invest_decoupling("capture")
    game_env.advance_round()
    lines = m.highlights_lines()
    assert len(lines) == 3
    assert lines[0].startswith("Biggest single round: round ")
    assert "Best methane cut in one round: round 2, 2.0 less" in lines[1]
    assert "Herd peaked at 10 animals" in lines[2]


def test_reel_without_any_cut_says_so_and_mentions_a_flock(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.herd_size = 4
    farm.poultry_size = 3
    game_env.advance_round()
    game_env.advance_round()
    lines = m.highlights_lines()
    assert "none yet" in lines[1]
    assert "plus a flock of 3" in lines[2]


def test_reel_appears_on_the_report_card(game_env):
    m = game_env.module
    game_env.farm.herd_size = 3
    game_env.advance_round()
    assert 'class="highlights-reel"' in m.report_card_html()
    assert "Highlights" in m.report_card_html()


def test_funds_history_round_trips_and_pads_old_saves(game_env):
    m = game_env.module
    game_env.farm.herd_size = 3
    game_env.advance_round()
    game_env.advance_round()
    state = m.get_state()
    assert len(state["funds_history"]) == len(state["methane_history"])
    assert m.load_state(state)
    assert len(m.farm.funds_history) == len(m.farm.methane_history)
    state.pop("funds_history")
    assert m.load_state(state)
    assert m.farm.funds_history[:-1] == [None, None]
    assert m.farm.funds_history[-1] == m.farm.funds
    assert m.highlights_lines()  # None padding must not crash the reel


def test_bad_funds_history_is_rebuilt(game_env):
    m = game_env.module
    state = m.get_state()
    state["funds_history"] = "oops"
    assert m.load_state(state)
    assert len(m.farm.funds_history) == len(m.farm.methane_history)
    state["funds_history"] = [1.0, float("nan"), True, "x"]
    assert m.load_state(state)
    assert len(m.farm.funds_history) == len(m.farm.methane_history)


def test_new_save_keys_are_omitted_until_there_is_something_to_save(game_env):
    state = game_env.module.get_state()
    for key in ("lever_log", "perfect_streak", "best_perfect_streak", "breeds_collected", "combos_found", "funds_history"):
        assert key not in state


# ---- F-10 (partial) aria-live announcer --------------------------------------------------------------
def test_advance_round_announces_the_result_for_screen_readers(game_env):
    game_env.farm.herd_size = 4
    game_env.advance_round()
    text = game_env.elements["round-announcer"].innerText
    assert text.startswith("Round 1 done. Funds ")
    assert "up" in text and "Methane added 4.0" in text and "Herd 4" in text


def test_announcer_is_a_polite_live_region_in_both_pages():
    for name in ("index.html", "pc.html"):
        html = (GAME_DIR / name).read_text(encoding="utf-8")
        assert re.search(r'<p id="round-announcer" class="sr-only" role="status" aria-live="polite">', html)


# ---- Desktop reachability ------------------------------------------------------------------------------
def test_collection_is_a_desktop_window_and_the_classic_wrapper_is_hidden_there():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    collection = [c for c in cfg["composites"] if c["id"] == "pc-collection-panel"]
    assert collection and set(collection[0]["members"]) == {
        "#collection-summary", "#breed-shelf", "#combo-book", "#hall-of-fame", "#lever-history"}
    assert "#collection-extras" in cfg["zones"]["hidden"]
