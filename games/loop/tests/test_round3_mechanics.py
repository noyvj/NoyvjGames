"""Round 3 mechanics: Perfect Cycle combo (GH-12), secret category (GH-14), name plates and
career records (GH-15, H-9), speed-loop achievements (GH-20), streak insurance (GH-24),
near-miss messages (GH-25), and the career's save round trip."""

import json

import pytest


def close_loop(env, units=10):
    """Funds topped up, enough recycling to need no new extraction."""
    env.chain.funds = 5000.0
    for _ in range(units):
        env.invest_circularity("recycle")


def perfect_cycles(env, n):
    for _ in range(n):
        env.advance_cycle()


# ---------------------------------------------------------------- GH-12 combo
def test_first_perfect_cycle_banks_nothing_second_banks_three(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    assert game_env.chain.perfect_bonus == 0
    game_env.advance_cycle()
    assert game_env.chain.perfect_bonus == pytest.approx(3.0)
    game_env.advance_cycle()
    assert game_env.chain.perfect_bonus == pytest.approx(9.0)  # 0 + 3 + 6
    assert game_env.chain.combo_level() == 3


def test_combo_gain_is_capped(game_env):
    close_loop(game_env)
    perfect_cycles(game_env, 14)
    before = game_env.chain.perfect_bonus
    game_env.advance_cycle()
    assert game_env.chain.perfect_bonus - before == pytest.approx(
        game_env.module.COMBO_BONUS_PER_LEVEL * (game_env.module.COMBO_CAP - 1)
    )
    assert game_env.chain.combo_level() == game_env.module.COMBO_CAP


def test_a_miss_drops_the_combo_but_keeps_the_banked_bonus(game_env):
    close_loop(game_env)
    perfect_cycles(game_env, 3)
    banked = game_env.chain.perfect_bonus
    game_env.chain.circularity_investment["recycle"] = 0
    game_env.advance_cycle()
    assert game_env.chain.combo_level() == 0
    assert game_env.chain.perfect_bonus == banked
    assert "x0" in game_env.elements["combo-display"].innerText


def test_banked_bonus_is_part_of_the_score_and_the_breakdown(game_env):
    close_loop(game_env)
    perfect_cycles(game_env, 3)
    chain = game_env.chain
    expected = chain.funds + chain.lifetime_circular_fraction() * game_env.module.CIRCULARITY_BONUS_WEIGHT + 9.0
    assert chain.score() == pytest.approx(expected)
    assert "combo bonus (9)" in game_env.elements["score-breakdown-display"].innerText


def test_breakdown_has_no_combo_term_before_any_bonus(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    assert "combo" not in game_env.elements["score-breakdown-display"].innerText


def test_combo_text_announces_the_next_gain(game_env):
    close_loop(game_env)
    perfect_cycles(game_env, 2)
    text = game_env.elements["combo-display"].innerText
    assert "x2" in text and "+6" in text and "Banked so far: 3" in text


# ------------------------------------------------------------ GH-24 insurance
def test_insurance_needs_a_streak_and_funds(game_env):
    assert not game_env.chain.can_buy_insurance()
    close_loop(game_env)
    game_env.advance_cycle()
    assert game_env.chain.can_buy_insurance()
    game_env.chain.funds = 5.0
    assert not game_env.chain.can_buy_insurance()
    game_env.module.render()
    assert game_env.elements["insurance-button"].disabled is True


def test_insurance_freezes_the_streak_through_one_bad_cycle_once(game_env):
    close_loop(game_env)
    perfect_cycles(game_env, 3)
    game_env.chain.funds = 100.0
    game_env.elements["insurance-button"].dispatch("click", None)
    assert game_env.chain.funds == pytest.approx(90.0)
    assert game_env.chain.insurance_armed and game_env.chain.insurance_used
    game_env.chain.circularity_investment["recycle"] = 0
    game_env.advance_cycle()  # a bad cycle
    assert game_env.chain.closed_loop_streak == 3
    assert game_env.chain.insurance_armed is False
    assert game_env.chain.last_insurance_saved is True
    assert "insurance held" in game_env.elements["cycle-live-summary"].innerText
    game_env.advance_cycle()  # a second bad cycle is no longer covered
    assert game_env.chain.closed_loop_streak == 0
    game_env.chain.closed_loop_streak = 2
    game_env.chain.funds = 500.0
    assert not game_env.chain.can_buy_insurance()  # once per chain
    game_env.module.render()
    assert "already used" in game_env.elements["insurance-status"].innerText


def test_armed_insurance_is_not_spent_by_a_perfect_cycle(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    assert game_env.chain.buy_insurance()
    game_env.advance_cycle()
    assert game_env.chain.insurance_armed is True


def test_a_frozen_cycle_banks_no_combo(game_env):
    close_loop(game_env)
    perfect_cycles(game_env, 3)
    banked = game_env.chain.perfect_bonus
    game_env.chain.buy_insurance()
    game_env.chain.circularity_investment["recycle"] = 0
    game_env.advance_cycle()
    assert game_env.chain.perfect_bonus == banked


def test_insurance_is_per_chain(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    game_env.chain.buy_insurance()
    game_env.reset_chain()
    assert game_env.chain.insurance_used is False


# --------------------------------------------------------------- GH-25 near miss
def test_near_miss_names_the_cheapest_single_fix(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    chain.circularity_investment["recycle"] = 9  # 45 units supplied, 5 short of closing
    game_env.module.render()
    text = game_env.elements["near-miss-display"].innerText
    assert "So close: 5 units short of closing the loop" in text
    assert "Recycling Loops (30 funds, +5 units)" in text
    assert game_env.elements["near-miss-display"].hidden is False


def test_near_miss_is_silent_when_still_far(game_env):
    game_env.chain.funds = 5000.0
    game_env.chain.circularity_investment["recycle"] = 8  # 40 supplied, 10 short: too far for a note
    game_env.module.render()
    assert game_env.elements["near-miss-display"].hidden is True


def test_near_miss_uses_a_bigger_source_when_no_cheap_one_covers_the_gap(game_env):
    chain = game_env.chain
    chain.circularity_investment.update({"recycle": 8, "repair": 1})  # 43 supplied, 7 short
    info = game_env.module.near_miss_info()
    assert info[0] == pytest.approx(7.0)
    assert "Overseas Consortium" in info[2]  # only the +15 partner covers 7 in one purchase


def test_near_miss_prefers_the_regional_partner_for_a_six_unit_gap(game_env):
    game_env.chain.circularity_investment.update({"recycle": 8, "repair": 0, "reuse": 1})  # 44, 6 short
    info = game_env.module.near_miss_info()
    assert info[0] == pytest.approx(6.0) and "Regional Partner" in info[2]


def test_near_miss_for_the_next_quarter_step(game_env):
    chain = game_env.chain
    chain.circularity_investment["repair"] = 4  # 12 supplied = 24%: 0.5 of a unit... 1 unit short of 25%
    game_env.module.render()
    info = game_env.module.near_miss_info()
    assert info is not None and "25% mark" in info[1]
    assert "1 unit short of the 25% mark" in game_env.elements["near-miss-display"].innerText


def test_near_miss_shows_the_funds_gap_when_unaffordable(game_env):
    game_env.chain.funds = 10.0
    game_env.chain.circularity_investment["recycle"] = 9
    game_env.module.render()
    assert "you need 20 more" in game_env.elements["near-miss-display"].innerText


def test_no_near_miss_when_closed_or_far(game_env):
    assert game_env.module.near_miss_info() is None
    close_loop(game_env)
    assert game_env.module.near_miss_info() is None
    assert game_env.module.near_miss_message() == ""


# ------------------------------------------------------- GH-14 secret category
def _close_on(env, category):
    env.select_goods_category(category)
    close_loop(env)
    env.advance_cycle()
    env.reset_chain()


def test_secret_category_starts_locked_with_a_visible_hint(game_env):
    assert game_env.module.secret_unlocked() is False
    assert game_env.elements["goods-category-shipyard-button"].hidden is True
    hint = game_env.elements["secret-category-hint"]
    assert hint.hidden is False and "0 of 3" in hint.innerText


def test_closing_each_ordinary_category_unlocks_it(game_env):
    for done, category in enumerate(("electronics", "clothing", "furniture"), start=1):
        _close_on(game_env, category)
        if done < 3:
            assert game_env.module.secret_unlocked() is False
            assert f"{done} of 3" in game_env.elements["secret-category-hint"].innerText
    assert game_env.module.secret_unlocked() is True
    assert game_env.elements["goods-category-shipyard-button"].hidden is False
    assert game_env.elements["secret-category-hint"].hidden is True


def test_an_unclosed_cycle_does_not_count(game_env):
    game_env.select_goods_category("clothing")
    game_env.advance_cycle()
    assert "clothing" not in game_env.module.career_closed_categories


def test_relabelling_cannot_be_used_to_unlock_it(game_env):
    game_env.select_goods_category("electronics")
    game_env.elements["relabel-clothing-button"].dispatch("click", None)
    close_loop(game_env)
    game_env.advance_cycle()
    assert game_env.module.career_closed_categories == {"electronics"}


def _unlock(env):
    for category in ("electronics", "clothing", "furniture"):
        _close_on(env, category)


def test_picking_the_yard_gives_the_scrap_line(game_env):
    _unlock(game_env)
    game_env.select_goods_category("shipyard")
    chain = game_env.chain
    assert chain.goods_category == "shipyard" and chain.picked_category == "shipyard"
    assert chain.head_start == game_env.module.SECRET_HEAD_START_UNITS
    assert chain.internal_circular_supply() == pytest.approx(6.0)
    assert chain.circular_fraction_this_cycle() == pytest.approx(0.12)
    assert "yard scrap line +6" in game_env.elements["recycle-stats"].innerText


def test_yard_is_refused_while_locked_or_after_production(game_env):
    game_env.select_goods_category("shipyard")
    assert game_env.chain.goods_category == "electronics" and game_env.chain.head_start == 0
    _unlock(game_env)
    game_env.advance_cycle()
    game_env.select_goods_category("shipyard")
    assert game_env.chain.goods_category != "shipyard"


def test_head_start_counts_as_recycling_in_every_view(game_env):
    _unlock(game_env)
    game_env.select_goods_category("shipyard")
    module = game_env.module
    flows = {r[0]: r[4] for r in module.internal_measure_flows()}
    assert flows["recycle"] == pytest.approx(6.0)
    assert sum(flows.values()) == pytest.approx(game_env.chain.internal_circular_supply())
    assert game_env.chain.supply_mix() == {"repair": 0.0, "reuse": 0.0, "recycle": 1.0, "trade": 0.0}


def test_yard_flavour_text_and_passport_exist(game_env):
    _unlock(game_env)
    game_env.select_goods_category("shipyard")
    module = game_env.module
    assert "hull" in module.vignette_message(0.0)
    assert "Argo" in module.PASSPORT_PRODUCT_NAME["shipyard"]
    game_env.advance_cycle()
    assert "Argo" in game_env.elements["passport-summary"].innerText


def test_yard_does_not_disturb_the_goods_collector_progress(game_env):
    _unlock(game_env)
    game_env.select_goods_category("shipyard")
    module = game_env.module
    assert "shipyard" in module.goods_categories_tried
    assert module.ACHIEVEMENT_PROGRESS["goods_collector"]() == (3, 3)


def test_closing_a_yard_loop_earns_yard_boss(game_env):
    _unlock(game_env)
    game_env.select_goods_category("shipyard")
    assert "yard_boss" not in game_env.module.achievement_ids_earned()
    close_loop(game_env, units=9)  # 45 + the 6 scrap line covers 50
    game_env.advance_cycle()
    assert "yard_boss" in game_env.module.achievement_ids_earned()


# --------------------------------------------------------- GH-15 plates + H-9
@pytest.mark.parametrize(
    "setup,plate",
    [
        ({"recycle": 10}, "scrapper"),
        ({"repair": 17}, "fixer"),
        ({"reuse": 13}, "swapper"),
    ],
)
def test_dominant_measure_names_the_plate(game_env, setup, plate):
    game_env.chain.funds = 9999.0
    for measure, count in setup.items():
        game_env.chain.circularity_investment[measure] = count
    game_env.advance_cycle()
    assert plate in game_env.module.career_plates


def test_trade_dominant_chain_earns_the_diplomat(game_env):
    game_env.chain.overseas_trade_investment = 4  # 60 imported units
    game_env.advance_cycle()
    assert game_env.module.career_plates == {"diplomat"}


def test_a_balanced_mix_earns_the_allrounder(game_env):
    chain = game_env.chain
    chain.circularity_investment.update({"repair": 4, "reuse": 3, "recycle": 3})  # 12 + 12 + 15 = 39
    chain.trade_link_investment = 3  # +12 = 51
    game_env.advance_cycle()
    assert game_env.module.career_plates == {"allrounder"}


def test_no_plate_without_a_closed_cycle(game_env):
    game_env.chain.circularity_investment["recycle"] = 5
    game_env.advance_cycle()
    assert game_env.module.career_plates == set()


def test_live_plate_text_tracks_the_current_mix(game_env):
    assert "no plate" in game_env.module.live_plate_text()
    game_env.chain.circularity_investment["recycle"] = 2
    assert "The Scrapper" in game_env.module.live_plate_text()


def test_plates_and_records_survive_a_new_chain(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    game_env.reset_chain()
    assert "scrapper" in game_env.module.career_plates
    assert game_env.chain.first_loop_closed_cycle is None
    rows = game_env.elements["plates-list"].children
    assert len(rows) == 5 and rows[0].innerText.startswith("✓ The Scrapper")
    assert game_env.elements["plates-count"].innerText == "1 of 5 plates earned"


def test_collecting_all_five_plates_earns_the_achievement(game_env):
    module = game_env.module
    module.career_plates.update(module.PLATES)
    assert "plate_collector" in module.achievement_ids_earned()
    assert module.ACHIEVEMENT_PROGRESS["plate_collector"]() == (5, 5)


def test_career_records_track_the_best_per_category(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    record = game_env.module.career_best["electronics"]
    assert record["fastest_close"] == 1
    assert record["lowest_extraction"] == 0.0
    assert record["best_streak"] == 1
    lines = game_env.module.career_record_lines()
    assert lines and lines[0].startswith("Electronics: first close on cycle 1")
    assert any("first close on cycle 1" in c.innerText for c in game_env.elements["career-records"].children)


def test_records_never_get_worse(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    game_env.reset_chain()
    game_env.advance_cycle()  # a poor straight-line chain afterwards
    record = game_env.module.career_best["electronics"]
    assert record["fastest_close"] == 1 and record["best_streak"] == 1


# ---------------------------------------------------------- GH-20 speed loops
def test_closing_by_cycle_twelve_earns_the_speed_flag(game_env):
    close_loop(game_env)
    assert "cycle12" in game_env.module.career_speed
    assert "speed_close" in game_env.module.achievement_ids_earned()


def test_a_late_close_misses_the_speed_flag_but_can_still_be_lean(game_env):
    game_env.chain.cycle_number = 13
    close_loop(game_env)
    assert "cycle12" not in game_env.module.career_speed
    assert "lean" in game_env.module.career_speed  # nothing extracted yet


def test_heavy_extraction_misses_lean_flag(game_env):
    game_env.chain.total_extracted = 600.0
    close_loop(game_env)
    assert "lean" not in game_env.module.career_speed


def test_using_trade_misses_the_no_trade_flag(game_env):
    game_env.chain.funds = 5000.0
    game_env.invest_trade_link()
    close_loop(game_env, units=9)
    assert "no_trade" not in game_env.module.career_speed
    assert "no_trade_close" not in game_env.module.achievement_ids_earned()


def test_only_the_first_close_counts(game_env):
    game_env.chain.cycle_number = 20
    close_loop(game_env)
    assert "cycle12" not in game_env.module.career_speed
    game_env.chain.cycle_number = 2  # a later close can never rewrite the first
    game_env.chain.circularity_investment["recycle"] = 0
    close_loop(game_env)
    assert "cycle12" not in game_env.module.career_speed


def test_speed_achievements_never_pop_a_toast(game_env):
    toast = game_env.elements["achievement-toast-text"]
    close_loop(game_env)
    assert "Quick Study" not in toast.innerText
    assert "Light Touch" not in toast.innerText
    assert "Self-Reliant" not in toast.innerText
    ids = game_env.module.achievement_ids_earned()
    assert {"speed_close", "lean_close", "no_trade_close"} <= set(ids)
    panel_summary = {a["id"]: a["earned"] for a in game_env.module.achievements_summary()}
    assert panel_summary["speed_close"] is True


def test_speed_achievements_survive_a_new_chain(game_env):
    close_loop(game_env)
    game_env.reset_chain()
    assert "speed_close" in game_env.module.achievement_ids_earned()


# ----------------------------------------------------------------- save / load
def test_default_saves_gain_no_new_keys(game_env):
    data = game_env.module.get_state()
    for key in ("career", "perfect_bonus", "head_start", "insurance_used", "picked_category",
                "first_close_extracted"):
        assert key not in data


def test_round_trip_keeps_career_and_chain_fields(game_env):
    module = game_env.module
    _unlock(game_env)
    game_env.select_goods_category("shipyard")
    close_loop(game_env, units=9)
    perfect_cycles(game_env, 3)
    game_env.chain.buy_insurance()
    snapshot = json.loads(json.dumps(module.get_state()))
    module.career_plates.clear()
    module.career_closed_categories.clear()
    module.career_best.clear()
    module.career_speed.clear()
    game_env.chain.perfect_bonus = 0.0
    module.load_state(snapshot)
    chain = game_env.chain
    assert chain.picked_category == "shipyard" and chain.head_start == 6.0
    assert chain.perfect_bonus == pytest.approx(9.0)
    assert chain.insurance_used and chain.insurance_armed
    assert module.secret_unlocked()
    assert module.career_plates and "shipyard" in module.career_closed_categories
    assert module.career_best["shipyard"]["fastest_close"] == 1
    assert chain.first_close_trade_free is True


def test_malformed_career_is_dropped_quietly(game_env):
    module = game_env.module
    snapshot = module.get_state()
    snapshot["career"] = {
        "closed": ["electronics", "bogus", 5],
        "plates": ["fixer", "nope"],
        "speed": ["lean", "x"],
        "best": {"electronics": {"fastest_close": -3, "best_score": float("nan"), "best_streak": True,
                                 "lowest_extraction": 12.5},
                 "ghost": {"best_score": 1}, "clothing": "bad"},
    }
    snapshot["perfect_bonus"] = "lots"
    snapshot["head_start"] = float("inf")
    snapshot["picked_category"] = 7
    module.load_state(snapshot)
    assert module.career_closed_categories == {"electronics"}
    assert module.career_plates == {"fixer"} and module.career_speed == {"lean"}
    assert module.career_best == {"electronics": {"lowest_extraction": 12.5}}
    assert game_env.chain.perfect_bonus == 0.0 and game_env.chain.head_start == 0.0
    assert game_env.chain.picked_category == game_env.chain.goods_category


def test_loading_an_older_save_resets_the_career(game_env):
    module = game_env.module
    module.career_plates.add("fixer")
    snapshot = module.get_state()
    snapshot.pop("career", None)
    module.load_state(snapshot)
    assert module.career_plates == set()


def test_next_step_note_uses_the_tighter_window(game_env):
    game_env.chain.circularity_investment["repair"] = 2  # 6 units = 12%: 6.5 short of 25%, too far
    assert game_env.module.near_miss_info() is None
    game_env.chain.circularity_investment["repair"] = 3  # 9 units: 3.5 short of 25%
    info = game_env.module.near_miss_info()
    assert info is not None and info[0] == pytest.approx(3.5)
    assert "Reuse Systems" in info[2]


def test_closing_window_is_wider_than_the_step_window(game_env):
    assert game_env.module.NEAR_MISS_UNITS > game_env.module.NEAR_MISS_STEP_UNITS
