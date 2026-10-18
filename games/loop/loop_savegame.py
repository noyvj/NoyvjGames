"""get_state() and the pieces that read a save back safely (integrity report, load note, buy log)."""

import copy

import loop_runstate as runstate
from loop_achievements import achievement_ids_earned
from loop_career import career_state
from loop_ghost_codes import _plain_int
from loop_ledger import ledger_to_save, past_chains
from loop_rules import BUY_KINDS, GOODS_CATEGORIES, LEDGER_MAX


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state()/load_state() are the per-game contract the widget calls
# (get_state()/load_state() on save/load respectively). SOL is the
# reference integration for this contract; Loop follows the same
# thin/direct pattern rather than reinventing it.


def get_state():
    """Return every piece of Loop's tracked state as a plain, JSON-safe
    dict. `chain` is the primary stateful object in the game — its dict/
    list attributes (`circularity_investment`, `circular_fraction_log`)
    are deep-copied so the saved snapshot doesn't alias a live reference;
    continued play after saving would otherwise silently mutate it, same
    reasoning as SOL's serialize_state(). `chains_completed_count`/
    `goods_categories_tried` are module-level (not on `chain`) since they
    deliberately survive a "Start New Chain" reset. `achievements_earned`
    is always freshly recomputed and never read back by load_state()
    (ACHIEVEMENTS-SYSTEM-DESIGN.md §1)."""
    state = {
        "cycle_number": runstate.chain.cycle_number,
        "funds": runstate.chain.funds,
        "total_extracted": runstate.chain.total_extracted,
        "total_produced": runstate.chain.total_produced,
        # H5: a derived, read-only field -- not restored by load_state()
        # below, just recomputed fresh from total_extracted/total_produced
        # every call. Exposed here purely so app/stats.py's STATS_FIELDS
        # whitelist (a plain top-level get_state() field, planning/TODO.md
        # Z1) can read it directly instead of a consumer having to derive
        # the fraction itself from two separate raw-count fields.
        "lifetime_circular_fraction": runstate.chain.lifetime_circular_fraction(),
        "circularity_investment": copy.deepcopy(runstate.chain.circularity_investment),
        "circular_fraction_log": copy.deepcopy(runstate.chain.circular_fraction_log),
        "trade_link_investment": runstate.chain.trade_link_investment,
        "regional_trade_investment": runstate.chain.regional_trade_investment,
        "overseas_trade_investment": runstate.chain.overseas_trade_investment,
        "first_loop_closed_cycle": runstate.chain.first_loop_closed_cycle,
        "regional_hint_seen": runstate.regional_hint_seen,
        "goods_category": runstate.chain.goods_category,
        "lifetime_investment_spend": runstate.chain.lifetime_investment_spend,
        "lifetime_export_revenue": runstate.chain.lifetime_export_revenue,
        **({"donate_surplus": True} if runstate.chain.donate_surplus else {}),
        **({"lifetime_pool_donated": runstate.chain.lifetime_pool_donated} if runstate.chain.lifetime_pool_donated > 0 else {}),
        "closed_loop_streak": runstate.chain.closed_loop_streak,
        "best_closed_loop_streak": runstate.chain.best_closed_loop_streak,
        "chains_completed_count": runstate.chains_completed_count,
        "goods_categories_tried": sorted(runstate.goods_categories_tried),
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
    }
    # H13/H23: written only when a mode is on, so older/default saves are unchanged.
    if runstate.chain.challenge_mode:
        state["challenge_mode"] = True
    if runstate.chain.zero_waste:
        state["zero_waste"] = True
    if runstate.chain.waste_focus is not None:
        state["waste_focus"] = runstate.chain.waste_focus
    if any(runstate.chain.redesign_level.values()):
        state["redesign_level"] = dict(runstate.chain.redesign_level)
    if runstate.chain.culture_level:
        state["culture_level"] = runstate.chain.culture_level
    if runstate.chain.passport:
        state["passport"] = [dict(e) for e in runstate.chain.passport]
    # Round 3 additions: each is written only when it differs from a fresh chain, so older
    # and default saves keep exactly the shape they had.
    if runstate.chain.picked_category != runstate.chain.goods_category:
        state["picked_category"] = runstate.chain.picked_category
    if runstate.chain.head_start > 0:
        state["head_start"] = runstate.chain.head_start
    if runstate.chain.perfect_bonus > 0:
        state["perfect_bonus"] = runstate.chain.perfect_bonus
    if runstate.chain.insurance_used:
        state["insurance_used"] = True
    if runstate.chain.insurance_armed:
        state["insurance_armed"] = True
    if runstate.chain.first_close_extracted is not None:
        state["first_close_extracted"] = runstate.chain.first_close_extracted
    if runstate.chain.first_close_trade_free is not None:
        state["first_close_trade_free"] = runstate.chain.first_close_trade_free
    if runstate.chain.rewind_used:
        state["rewind_used"] = True
    if runstate.chain.ledger:
        state["ledger"] = ledger_to_save()
    if past_chains:
        state["past_chains"] = copy.deepcopy(past_chains)
    if runstate.chain.rival_on:
        state["rival_on"] = True
    if runstate.chain.rival_crossover_cycle is not None:
        state["rival_crossover_cycle"] = runstate.chain.rival_crossover_cycle
    if runstate.chain.assist != "off":
        state["assist"] = runstate.chain.assist
    if runstate.chain.assist_used:
        state["assist_used"] = True
    if any(runstate.chain.buys_now) or runstate.chain.buy_log:
        state["buy_log"] = [list(row) for row in runstate.chain.buy_log]
        state["buys_now"] = list(runstate.chain.buys_now)
    if runstate.chain.market_shocks:
        state["market_shocks"] = True
    if runstate.chain.shocks_shrugged:
        state["shocks_shrugged"] = runstate.chain.shocks_shrugged
    career = career_state()
    if career:
        state["career"] = career
    return state


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Circular share of all production", "value": round(runstate.chain.lifetime_circular_fraction() * 100), "unit": "%"},
        {"label": "Goods categories tried", "value": len(runstate.goods_categories_tried & set(GOODS_CATEGORIES)),
         "unit": f"of {len(GOODS_CATEGORIES)}"},
        {"label": "Chains completed", "value": int(runstate.chains_completed_count), "unit": ""},
    ]


# H-27: what a load had to repair. Each optional save key, the plain name shown to the player, and the value
# a fresh chain has (a key whose saved value would reload as a different value than was written was repaired).
LOAD_CHECKS = (
    ("challenge_mode", "Circular design challenge", False),
    ("zero_waste", "Zero-waste challenge", False),
    ("waste_focus", "Waste stream focus", None),
    ("redesign_level", "Redesign levels", None),
    ("culture_level", "Culture campaign level", 0),
    ("passport", "Material passport", None),
    ("picked_category", "Picked goods", None),
    ("head_start", "Yard scrap line", 0.0),
    ("perfect_bonus", "Combo bonus", 0.0),
    ("insurance_used", "Streak insurance", False),
    ("insurance_armed", "Streak insurance", False),
    ("first_close_extracted", "First-close record", None),
    ("first_close_trade_free", "First-close record", None),
    ("rewind_used", "Rewind token", False),
    ("market_shocks", "Market shocks switch", False),
    ("shocks_shrugged", "Market shock count", 0),
    ("rival_on", "Rival Corporation switch", False),
    ("rival_crossover_cycle", "Rival Corporation crossover", None),
    ("ledger", "Cycle ledger", None),
    ("past_chains", "Past chains", None),
    ("career", "Career records", None),
    ("assist", "Assist mode", "off"),
    ("assist_used", "Assisted tag", False),
    ("buy_log", "Purchases per cycle", None),
    ("buys_now", "Purchases this cycle", None),
    ("donate_surplus", "Surplus donation switch", False),
    ("lifetime_pool_donated", "Pool donation total", 0.0),
)
load_report = []  # [(name, "reset" | "repaired")] from the most recent load


def integrity_report(data):
    """H-27: compares the optional keys of a save with what the game would write back after loading it.
    A key that comes back missing (and was not just a default) was reset; one that comes back changed was
    repaired (a bad ledger row dropped, a note trimmed). Derived and write-only keys are not checked."""
    again = get_state()
    report = []
    for key, name, default in LOAD_CHECKS:
        if key not in data:
            continue
        raw = data[key]
        if key not in again:
            harmless = raw in (None, False, 0, 0.0, [], {}) or raw == default
            if key == "picked_category" and raw == data.get("goods_category"):
                harmless = True
            if not harmless:
                report.append((name, "reset"))
        elif again[key] != raw:
            report.append((name, "repaired"))
    unique = []
    for item in report:
        if item not in unique:
            unique.append(item)
    return unique


def load_note_lines():
    """H-27: friendly lines for the note shown after a load ('' list when nothing was touched)."""
    lines = []
    repaired = [name for name, kind in load_report if kind == "repaired"]
    reset = [name for name, kind in load_report if kind == "reset"]
    if repaired:
        lines.append("Repaired: " + ", ".join(repaired) + ".")
    if reset:
        lines.append("Reset to the starting value: " + ", ".join(reset) + ".")
    if lines:
        lines.append("Everything else loaded as saved.")
    return lines


def _buy_row(raw):
    """A saved purchase row (one count per BUY_KINDS) or None when it is not exactly that."""
    if isinstance(raw, list) and len(raw) == len(BUY_KINDS) and all(_plain_int(v, 0, 100_000) for v in raw):
        return list(raw)
    return None


def buy_log_from_save(raw):
    """H-26 / GH-28: keeps the saved purchase rows only if EVERY row is well formed (a half-kept log would put
    purchases against the wrong cycles); otherwise the log starts empty."""
    if not isinstance(raw, list):
        return []
    rows = [_buy_row(item) for item in raw[-LEDGER_MAX:]]
    return rows if all(row is not None for row in rows) else []


def buys_now_from_save(raw):
    return _buy_row(raw) or [0] * len(BUY_KINDS)
