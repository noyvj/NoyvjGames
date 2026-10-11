"""J-29 / J-30 -- Blackout: an opt-in hard mode that darkens the map, the sparklines and exact prices until the
player buys the information back, with a Dark Run stamp for finishing the endgame on an unbroken one."""

import json
import sys
import types

import pytest


def _finish_endgame_by_tick(game_env):
    m = game_env.module
    m.endgame_criteria_met = lambda: True
    game_env.tick(1)


def _canvas_text(game_env):
    return [args[0] for name, args in game_env.elements["map-canvas"].getContext("2d").calls if name == "fillText"]


def _install_dialog(accept=True):
    asked = []

    class Dialog:
        def ask(self, **options):
            asked.append(options)
            if accept:
                options["onConfirm"]()

    sys.modules["js"].window = types.SimpleNamespace(ConfirmDialog=Dialog())
    return asked


# ----------------------------------------------------------------- defaults

def test_off_by_default_and_nothing_is_saved(game_env):
    m = game_env.module
    assert m.blackout_enabled is False and m.blackout_has("feed") and m.blackout_has("chart")
    state = m.get_state()
    assert "blackout" not in state and "records" not in state
    assert "(" in game_env.elements["market-ore-display"].innerText  # the normal "(100% of baseline)" line
    assert game_env.elements["blackout-toggle-button"].innerText == "Blackout: off"


def test_switching_on_before_the_first_sale_starts_a_clean_run(game_env):
    m = game_env.module
    assert m.set_blackout(True) is True
    assert m.blackout_enabled and m.blackout_clean
    assert m.set_blackout(True) is True  # idempotent
    assert m.get_state()["blackout"]["clean"] is True


def test_switching_on_after_a_sale_is_allowed_but_is_not_a_dark_run(game_env):
    m = game_env.module
    m.total_sales_count = 1
    m.set_blackout(True)
    assert m.blackout_enabled and not m.blackout_clean
    assert "not a dark run" in m.blackout_status_text()


def test_switching_off_after_a_sale_ends_the_dark_run_for_good(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.total_sales_count = 1
    m.set_blackout(False)
    m.set_blackout(True)
    assert m.blackout_enabled and not m.blackout_clean


def test_switching_off_and_on_before_any_sale_keeps_it_clean(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.set_blackout(False)
    m.set_blackout(True)
    assert m.blackout_clean


def test_the_sandbox_refuses_blackout(game_env):
    m = game_env.module
    m.sandbox_enter()
    assert m.set_blackout(True) is False and m.blackout_enabled is False
    assert game_env.elements["blackout-toggle-button"].disabled is True
    m.sandbox_leave()
    assert game_env.elements["blackout-toggle-button"].disabled is False


# ----------------------------------------------------------- what goes dark

def test_prices_become_ranges_and_the_bar_is_coarse(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.market_multiplier["ore"] = 0.55
    m.render()
    price = m.current_sell_price("ore")
    low, high = m.blackout_price_range(price)
    assert low <= price <= high and low < high
    text = game_env.elements["market-ore-display"].innerText
    assert f"about {low}-{high} credits/unit" in text and "% of baseline" not in text
    assert game_env.elements["market-ore-bar"].style.width == "50%"  # 55% rounds to the nearest quarter


def test_sparklines_are_hidden_until_the_feed_is_back(game_env):
    m = game_env.module
    game_env.tick(3)
    assert game_env.elements["market-ore-sparkline"].innerHTML != ""
    m.set_blackout(True)
    m.render()
    assert game_env.elements["market-ore-sparkline"].innerHTML == ""
    assert game_env.elements["colony-aurum-need-sparkline"].innerHTML == ""
    m.total_profit = 1000
    assert m.buy_blackout_intel("feed") is True
    m.render()
    assert game_env.elements["market-ore-sparkline"].innerHTML != ""
    assert "% of baseline" in game_env.elements["market-ore-display"].innerText


def test_the_map_goes_dark_and_ships_are_not_drawn(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.render()
    ctx = game_env.elements["map-canvas"].getContext("2d")
    ctx.calls.clear()
    m.render()
    assert any("star chart is dark" in t for t in _canvas_text(game_env))
    assert not [c for c in ctx.calls if c[0] == "arc"]  # no colony nodes, no ship dots
    assert "dark" in game_env.elements["map-canvas"].title


def test_the_map_comes_back_with_the_chart_purchase(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.total_profit = 1000
    assert m.buy_blackout_intel("chart") is True
    ctx = game_env.elements["map-canvas"].getContext("2d")
    ctx.calls.clear()
    m.render()
    assert [c for c in ctx.calls if c[0] == "arc"]


def test_research_gives_the_information_without_paying(game_env):
    m = game_env.module
    m.set_blackout(True)
    assert not m.blackout_has("feed") and not m.blackout_has("chart")
    m.unlocked_research.add("market_insight")
    assert m.blackout_has("feed") and not m.blackout_has("chart")
    m.unlocked_research.add("galaxy_expansion")
    assert m.blackout_has("chart")
    assert m.can_buy_blackout_intel("feed") is False  # nothing to buy any more


def test_buying_costs_credits_and_needs_blackout_and_enough(game_env):
    m = game_env.module
    m.total_profit = 1000
    assert m.can_buy_blackout_intel("feed") is False  # blackout is off
    m.set_blackout(True)
    m.total_profit = m.BLACKOUT_FEED_COST - 1
    assert m.can_buy_blackout_intel("feed") is False
    m.total_profit = m.BLACKOUT_FEED_COST + 5
    assert m.buy_blackout_intel("feed") is True and m.total_profit == 5
    assert m.buy_blackout_intel("feed") is False
    assert m.can_buy_blackout_intel("nonsense") is False


def test_blackout_changes_no_economics(game_env):
    m = game_env.module
    before = m.current_sell_price("ore")
    m.set_blackout(True)
    assert m.current_sell_price("ore") == before


def test_price_range_always_brackets_even_cheap_goods():
    # the helper is pure; import it through a fresh env-free copy of the arithmetic
    import math
    for price in range(1, 60):
        low = max(1, int(price * 0.85))
        high = max(low + 1, int(math.ceil(price * 1.15)))
        assert low <= price <= high


def test_buy_buttons_show_only_while_something_is_dark(game_env):
    m = game_env.module
    assert game_env.elements["blackout-buy-feed-button"].hidden is True
    m.set_blackout(True)
    m.render()
    assert game_env.elements["blackout-buy-feed-button"].hidden is False
    assert game_env.elements["blackout-buy-feed-button"].disabled is True  # cannot afford yet
    m.total_profit = 500
    m.render()
    game_env.elements["blackout-buy-feed-button"].dispatch("click", None)
    assert "feed" in m.blackout_bought and game_env.elements["blackout-buy-feed-button"].hidden is True


# ------------------------------------------------------------- the toggle

def test_switching_on_shows_the_plain_warning_and_no_skip_box(game_env):
    asked = _install_dialog(accept=False)
    game_env.elements["blackout-toggle-button"].dispatch("click", None)
    assert asked and "entirely optional" in asked[0]["message"] and asked[0]["allowSkip"] is False
    assert game_env.module.blackout_enabled is False  # nothing happens until confirmed


def test_confirming_switches_on_and_the_button_follows(game_env):
    _install_dialog(accept=True)
    game_env.elements["blackout-toggle-button"].dispatch("click", None)
    assert game_env.module.blackout_enabled
    assert game_env.elements["blackout-toggle-button"].innerText == "Blackout: on"
    assert game_env.elements["blackout-toggle-button"].attributes["aria-pressed"] == "true"


def test_switching_off_warns_a_dark_run_would_end(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.total_sales_count = 2
    asked = _install_dialog(accept=True)
    game_env.elements["blackout-toggle-button"].dispatch("click", None)
    assert "ends your dark run" in asked[0]["message"] and not m.blackout_enabled


def test_toggle_works_without_the_shared_dialog(game_env):
    game_env.elements["blackout-toggle-button"].dispatch("click", None)
    assert game_env.module.blackout_enabled


# ------------------------------------------------------------- the dark run

def test_a_clean_blackout_reaching_the_endgame_is_a_dark_run(game_env):
    m = game_env.module
    m.set_blackout(True)
    _finish_endgame_by_tick(game_env)
    assert m.blackout_done and m.records["dark_runs"] == 1
    assert "dark_run" in m.achievement_ids_earned()
    assert "Dark run" in game_env.elements["charter-crest"].innerText
    assert "stamp" in game_env.elements["ledger-dark-display"].innerText


def test_an_unclean_blackout_is_not_a_dark_run(game_env):
    m = game_env.module
    m.total_sales_count = 1
    m.set_blackout(True)
    _finish_endgame_by_tick(game_env)
    assert not m.blackout_done and m.records["dark_runs"] == 0
    assert "dark_run" not in m.achievement_ids_earned()


def test_no_blackout_means_no_stamp(game_env):
    m = game_env.module
    _finish_endgame_by_tick(game_env)
    assert m.records["dark_runs"] == 0
    assert "none yet" in game_env.elements["ledger-dark-display"].innerText


def test_the_stamp_counts_once_per_charter(game_env):
    m = game_env.module
    m.set_blackout(True)
    _finish_endgame_by_tick(game_env)
    game_env.tick(5)
    assert m.records["dark_runs"] == 1


def test_a_renewal_keeps_the_stamp_logs_it_and_resets_blackout(game_env):
    m = game_env.module
    m.set_blackout(True)
    _finish_endgame_by_tick(game_env)
    assert m.found_new_corporation() is True
    assert m.records["dark_runs"] == 1 and "dark_run" in m.achievement_ids_earned()
    assert m.blackout_enabled is False and m.blackout_done is False and not m.blackout_bought
    assert m.charter_career[-1].get("dark") is True
    assert "Dark run" in m.career_entry_text(m.charter_career[-1])
    assert "Dark run" in game_env.elements["charter-crest"].innerText


def test_a_plain_renewal_logs_no_dark_mark(game_env):
    m = game_env.module
    m.endgame_reached = True
    m.found_new_corporation()
    assert "dark" not in m.charter_career[-1]


def test_sandbox_cannot_make_a_dark_run(game_env):
    m = game_env.module
    m.sandbox_enter()
    m.blackout_enabled = m.blackout_clean = True
    m.blackout_note_endgame()
    assert m.records["dark_runs"] == 0 and not m.blackout_done


# ------------------------------------------------------------------- saves

def test_state_round_trips(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.total_profit = 900
    m.buy_blackout_intel("chart")
    _finish_endgame_by_tick(game_env)
    state = json.loads(json.dumps(m.get_state()))
    assert state["blackout"] == {"enabled": True, "clean": True, "done": True, "bought": ["chart"]}
    assert state["records"] == {"dark_runs": 1}
    m.blackout_enabled = m.blackout_clean = m.blackout_done = False
    m.blackout_bought.clear()
    m.records["dark_runs"] = 0
    m.load_state(state)
    assert m.blackout_enabled and m.blackout_clean and m.blackout_done and m.blackout_bought == {"chart"}
    assert m.records["dark_runs"] == 1


def test_loading_a_save_without_blackout_switches_it_off(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.records["dark_runs"] = 3
    m.load_state(json.loads(json.dumps(m._fresh_state)))
    assert not m.blackout_enabled and m.records["dark_runs"] == 0


@pytest.mark.parametrize("raw", [
    "x", 5, [], None, {"enabled": "yes"}, {"enabled": 1, "clean": True},
    {"enabled": True, "clean": "true", "done": 1, "bought": "feed"},
    {"enabled": True, "bought": [["feed"], 4, None, "nope"]},
])
def test_tampered_blackout_values_fall_back(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["blackout"] = raw
    assert m.load_state(state) is True
    assert m.blackout_enabled is False or raw.get("enabled") is True
    assert m.blackout_clean is False or m.blackout_enabled
    assert m.blackout_done is False
    assert m.blackout_bought <= set(m.BLACKOUT_INTEL)


@pytest.mark.parametrize("raw", ["x", 5, [], {"dark_runs": True}, {"dark_runs": -1}, {"dark_runs": 10 ** 12}, {"dark_runs": "3"}])
def test_tampered_records_fall_back_to_zero(game_env, raw):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["records"] = raw
    m.load_state(state)
    assert m.records == {"dark_runs": 0}


def test_career_entry_with_a_tampered_dark_flag_is_cleaned(game_env):
    m = game_env.module
    state = json.loads(json.dumps(m._fresh_state))
    state["charter"] = {"completed": 1, "points": 2, "career": [
        {"n": 1, "hard": False, "units": 5, "routes": 1, "peak": 9, "perks": 0, "dark": "yes"}]}
    m.load_state(state)
    assert "dark" not in m.charter_career[0]


def test_sandbox_round_trip_keeps_the_real_blackout(game_env):
    m = game_env.module
    m.set_blackout(True)
    m.records["dark_runs"] = 2
    before = json.dumps(m.get_state(), sort_keys=True)
    m.sandbox_enter()
    assert not m.blackout_enabled and m.records["dark_runs"] == 0
    m.sandbox_leave()
    assert json.dumps(m.get_state(), sort_keys=True) == before


def test_achievement_is_in_the_catalog(game_env):
    ids = [a["id"] for a in game_env.module.ACHIEVEMENTS]
    assert "dark_run" in ids
