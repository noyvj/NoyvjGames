"""load_state(): restores a save into the live game, then redraws."""

import loop_runstate as runstate
from loop_achievements import _seed_achievement_toast_baseline
from loop_career import _finite_number, load_career
from loop_ledger import ledger_from_save, past_chains, past_chains_from_save
from loop_planner import plan_clear
from loop_renderer import render
from loop_rules import (
    ALL_GOODS, ASSIST_MODES, CIRCULARITY_INVESTMENTS, CULTURE_MAX_LEVEL, DEFAULT_GOODS_CATEGORY,
    PASSPORT_MAX_ENTRIES, PASSPORT_SOURCES, REDESIGN_MAX_LEVEL,
)
from loop_savegame import buy_log_from_save, buys_now_from_save, integrity_report, load_report


def load_state(data):
    """Take the dict from get_state() (possibly from a previous session)
    and restore `chain` to that point — the exact inverse of
    get_state() — then re-render so the UI reflects the loaded state
    immediately.

    `circularity_investment` is merged key-by-key against the current
    CIRCULARITY_INVESTMENTS schema rather than wholesale-replaced: every
    render() reads chain.circularity_investment[measure] for every measure
    currently in CIRCULARITY_INVESTMENTS, so a snapshot missing a key (an
    older/hand-edited save) would otherwise leave that key absent entirely
    and crash the very next render with a KeyError. Merging also drops any
    stale key no longer in CIRCULARITY_INVESTMENTS (e.g. a retired
    measure) instead of letting it linger in the live dict forever.

    Every field added after the original save contract (regional trade
    investment, goods category, the lifetime tallies/streaks, the two
    module-level reset-survivor counters) defaults defensively via
    `.get(..., <safe default>)` so a save from before that field existed
    loads cleanly instead of raising KeyError."""

    runstate.chain.cycle_number = data["cycle_number"]
    runstate.chain.funds = data["funds"]
    runstate.chain.total_extracted = data["total_extracted"]
    runstate.chain.total_produced = data["total_produced"]
    saved_investment = data["circularity_investment"]
    runstate.chain.circularity_investment = {
        measure: saved_investment.get(measure, 0) for measure in CIRCULARITY_INVESTMENTS
    }
    runstate.chain.circular_fraction_log = list(data["circular_fraction_log"])
    # A save from before the trade-network field existed (Pass 2) won't
    # have this key — default to 0 (a fresh chain's own starting value)
    # rather than raising KeyError and failing the whole load.
    runstate.chain.trade_link_investment = data.get("trade_link_investment", 0)
    runstate.chain.regional_trade_investment = data.get("regional_trade_investment", 0)
    runstate.chain.overseas_trade_investment = data.get("overseas_trade_investment", 0)
    runstate.chain.first_loop_closed_cycle = data.get("first_loop_closed_cycle", None)
    runstate.regional_hint_seen = bool(data.get("regional_hint_seen", False))
    runstate.chain.goods_category = data.get("goods_category", DEFAULT_GOODS_CATEGORY)
    # H13/H23: strictly booleans; anything else loads as off.
    runstate.chain.challenge_mode = data.get("challenge_mode") is True
    runstate.chain.zero_waste = data.get("zero_waste") is True
    saved_focus = data.get("waste_focus")
    runstate.chain.waste_focus = saved_focus if isinstance(saved_focus, str) and saved_focus in CIRCULARITY_INVESTMENTS else None
    saved_culture = data.get("culture_level")
    runstate.chain.culture_level = (
        saved_culture
        if isinstance(saved_culture, int) and not isinstance(saved_culture, bool) and 0 <= saved_culture <= CULTURE_MAX_LEVEL
        else 0
    )
    runstate.chain.passport = []
    saved_passport = data.get("passport")
    if isinstance(saved_passport, list):
        for entry in saved_passport:
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("cycle"), int) and not isinstance(entry.get("cycle"), bool)
                and entry["cycle"] >= 1
                and isinstance(entry.get("source"), str) and entry["source"] in PASSPORT_SOURCES
            ):
                runstate.chain.passport.append({"cycle": entry["cycle"], "source": entry["source"]})
        del runstate.chain.passport[:-PASSPORT_MAX_ENTRIES]
    runstate.chain.redesign_level = {m: 0 for m in CIRCULARITY_INVESTMENTS}
    saved_redesign = data.get("redesign_level")
    if isinstance(saved_redesign, dict):
        for m in CIRCULARITY_INVESTMENTS:
            level = saved_redesign.get(m)
            if isinstance(level, int) and not isinstance(level, bool) and 0 <= level <= REDESIGN_MAX_LEVEL:
                runstate.chain.redesign_level[m] = level
    picked = data.get("picked_category")
    runstate.chain.picked_category = picked if isinstance(picked, str) and picked in ALL_GOODS else runstate.chain.goods_category
    head_start = data.get("head_start")
    runstate.chain.head_start = float(head_start) if _finite_number(head_start, 0.0, 1000.0) else 0.0
    perfect = data.get("perfect_bonus")
    runstate.chain.perfect_bonus = float(perfect) if _finite_number(perfect, 0.0, 1e9) else 0.0
    runstate.chain.insurance_used = data.get("insurance_used") is True
    runstate.chain.insurance_armed = data.get("insurance_armed") is True
    if runstate.chain.insurance_armed:
        runstate.chain.insurance_used = True
    first_extracted = data.get("first_close_extracted")
    runstate.chain.first_close_extracted = (
        float(first_extracted) if _finite_number(first_extracted, 0.0, 1e12) else None
    )
    trade_free = data.get("first_close_trade_free")
    runstate.chain.first_close_trade_free = trade_free if isinstance(trade_free, bool) else None
    runstate.chain.last_cycle_mix = None
    runstate.chain.last_combo_gain = 0.0
    runstate.chain.last_insurance_saved = False
    runstate.chain.rewind_used = data.get("rewind_used") is True
    runstate.chain.market_shocks = data.get("market_shocks") is True
    runstate.chain.rival_on = data.get("rival_on") is True
    runstate.chain.ledger = ledger_from_save(data.get("ledger"))
    past_chains[:] = past_chains_from_save(data.get("past_chains"))
    crossover = data.get("rival_crossover_cycle")
    runstate.chain.rival_crossover_cycle = (
        crossover if isinstance(crossover, int) and not isinstance(crossover, bool) and 1 <= crossover <= 1_000_000 else None
    )
    shrugged = data.get("shocks_shrugged")
    runstate.chain.shocks_shrugged = (
        shrugged if isinstance(shrugged, int) and not isinstance(shrugged, bool) and 0 <= shrugged <= 1_000_000 else 0
    )
    runstate.chain.rewind_snapshot = None  # the undo point is a visit-only thing: advance a cycle to set a new one
    saved_assist = data.get("assist")
    runstate.chain.assist = saved_assist if isinstance(saved_assist, str) and saved_assist in ASSIST_MODES else "off"
    runstate.chain.assist_used = data.get("assist_used") is True or runstate.chain.assist != "off"
    runstate.chain.buy_log = buy_log_from_save(data.get("buy_log"))
    runstate.chain.buys_now = buys_now_from_save(data.get("buys_now"))
    plan_clear()
    load_career(data.get("career"))
    runstate.chain.lifetime_investment_spend = data.get("lifetime_investment_spend", 0.0)
    runstate.chain.lifetime_export_revenue = data.get("lifetime_export_revenue", 0.0)
    runstate.chain.donate_surplus = data.get("donate_surplus") is True
    donated = data.get("lifetime_pool_donated")
    runstate.chain.lifetime_pool_donated = (
        float(donated)
        if isinstance(donated, (int, float)) and not isinstance(donated, bool) and donated == donated and 0 <= donated < 1e12
        else 0.0
    )
    runstate.chain.last_donation = 0.0
    runstate.chain.closed_loop_streak = data.get("closed_loop_streak", 0)
    runstate.chain.best_closed_loop_streak = data.get("best_closed_loop_streak", 0)

    runstate.chains_completed_count = data.get("chains_completed_count", 0)
    # Backfill (same pattern as SOL's visited_bodies): a save predating
    # this field won't list the restored chain's own category as
    # "tried" yet — add it unconditionally so goods_explorer's count
    # never undercounts a category the player is demonstrably playing.
    runstate.goods_categories_tried = set(data.get("goods_categories_tried", []))
    runstate.goods_categories_tried.add(runstate.chain.goods_category)

    load_report[:] = integrity_report(data)
    render()
    _seed_achievement_toast_baseline()
    return True
