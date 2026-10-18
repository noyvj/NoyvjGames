"""Smaller text readouts for the status block: score pie, audit, supply text map, near miss, equation, combo, pool, buy labels."""

import math

from js import document

import loop_runstate as runstate
from loop_career import career_plates
from loop_rules import (
    BURST_MILESTONES, CHALLENGE_MODE_SUPPLY_MULTIPLIER, CIRCULARITY_BONUS_WEIGHT, CIRCULARITY_INVESTMENTS,
    COMBO_CAP, ENVIRONMENTAL_DAMAGE_SCALE, EXPORT_PRICE_PER_UNIT, EXTRACTION_COST_PER_UNIT,
    GOODS_CATEGORIES, IMPORT_SUPPLY_PER_UNIT, INSURANCE_COST, MAX_COST_MULTIPLIER, NEAR_MISS_STEP_UNITS,
    NEAR_MISS_UNITS, OVERSEAS_IMPORT_SUPPLY_PER_UNIT, OVERSEAS_TRADE_COST, PRODUCTION_TARGET,
    REGIONAL_IMPORT_SUPPLY_PER_UNIT, REGIONAL_TRADE_COST, RIVAL_NAME, SALE_PRICE_PER_UNIT,
    STREAK_PROGRESS_STEP, TRADE_LINK_COST, ZERO_WASTE_EXTRACTION_CAP, rival_extracted_after,
    rival_funds_after, rival_profit_in_cycle,
)


# ===========================================================================
# Round-2 helpers (H2, H12, H15, H18, H25a/H29a, H27, H30). Pure functions of
# state, so they are directly testable.
# ===========================================================================
def streak_progress_text():
    """H2: a small text progress bar toward the next 5-cycle streak mark.
    Deliberately neutral (no flame/guilt framing): a plain 'x of 5'."""
    streak = runstate.chain.closed_loop_streak
    into = streak % STREAK_PROGRESS_STEP
    target = (streak // STREAK_PROGRESS_STEP + 1) * STREAK_PROGRESS_STEP
    bar = "\u25b0" * into + "\u25b1" * (STREAK_PROGRESS_STEP - into)
    return f"{bar}  {streak} of {target} cycles toward the next streak mark"


def score_pie_percentages():
    """H12: (funds_pct, bonus_pct) shares of the score, summing to 100."""
    bonus = runstate.chain.lifetime_circular_fraction() * CIRCULARITY_BONUS_WEIGHT + runstate.chain.perfect_bonus
    total = runstate.chain.funds + bonus
    if total <= 0:
        return (100, 0)
    bonus_pct = round(bonus / total * 100)
    return (100 - bonus_pct, bonus_pct)


def score_pie_style():
    funds_pct, _ = score_pie_percentages()
    return f"conic-gradient(#e0c24c 0 {funds_pct}%, #4c9c6e {funds_pct}% 100%)"


def top_investment_measure():
    """H18: the circularity measure with the most invested (ties broken by
    catalog order); None if nothing is invested yet."""
    best, best_count = None, 0
    for measure in CIRCULARITY_INVESTMENTS:
        if runstate.chain.circularity_investment[measure] > best_count:
            best, best_count = measure, runstate.chain.circularity_investment[measure]
    return best


def _partner_options():
    """(label, cost, supply_per_unit) for every purchasable supply source."""
    options = [
        (spec["label"], spec["cost"], spec["supply_per_unit"]) for spec in CIRCULARITY_INVESTMENTS.values()
    ]
    options.append(("Trade Link", TRADE_LINK_COST, IMPORT_SUPPLY_PER_UNIT))
    options.append(("Regional Partner", REGIONAL_TRADE_COST, REGIONAL_IMPORT_SUPPLY_PER_UNIT))
    options.append(("Overseas Consortium", OVERSEAS_TRADE_COST, OVERSEAS_IMPORT_SUPPLY_PER_UNIT))
    return options


def audit_lines():
    """H15: where supply/money is being wasted right now, with an
    actionable suggestion each. Always returns at least one line."""
    lines = []
    gap = runstate.chain.new_extraction_needed()
    surplus = runstate.chain.exportable_surplus()
    if gap > 0:
        cost = gap * EXTRACTION_COST_PER_UNIT * runstate.chain.price_multiplier()
        lines.append(
            f"New extraction is {gap:.0f} units this cycle, costing about {cost:.0f} funds "
            f"(and adding to lasting damage)."
        )
        label, unit_cost, supply = min(_partner_options(), key=lambda o: o[1] / o[2])
        buys = math.ceil(gap / supply)
        lines.append(
            f"Cheapest way to cover it: {label} at {unit_cost / supply:.1f} funds/unit -- "
            f"about {buys} purchase(s), {buys * unit_cost} funds."
        )
    if surplus > 0:
        lines.append(
            f"{surplus:.0f} units of supply exceed the production target; they sell for only "
            f"{EXPORT_PRICE_PER_UNIT:.0f}/unit versus {SALE_PRICE_PER_UNIT:.0f} for goods, so more investment "
            f"here adds little."
        )
    if runstate.chain.extraction_cost_multiplier() > 1.5:
        lines.append(
            f"Damage has pushed extraction cost to x{runstate.chain.extraction_cost_multiplier():.2f}; "
            "each extracted unit now costs noticeably more."
        )
    if not lines:
        lines.append("Nothing is being wasted right now: supply matches the production target.")
    return lines


def _strike_note(kind):
    return "  (port strike: shut)" if runstate.chain.blocked_partner() == kind else ""


def network_map_text():
    """H25a/H29a: a simple, everywhere-works text map of the chain, the
    internal recovery loop, and every trade partner's flow."""
    internal = runstate.chain.internal_circular_supply()
    parts = " / ".join(
        f"{CIRCULARITY_INVESTMENTS[m]['icon']} {runstate.chain.circularity_investment[m] * CIRCULARITY_INVESTMENTS[m]['supply_per_unit']:.0f}"
        for m in CIRCULARITY_INVESTMENTS
    )
    lines = [
        "Extract -> Manufacture -> Use -> Discard",
        f"   new extraction: {runstate.chain.new_extraction_needed():.0f}/cycle",
        f"Internal loop back into Manufacture: {internal:.0f}/cycle  ({parts})",
        "Trade partners:",
        f"  Trade Link          in +{runstate.chain.partner_supply('trade'):.0f}{_strike_note('trade')}",
        f"  Regional Partner    in +{runstate.chain.partner_supply('regional'):.0f}{_strike_note('regional')}",
        f"  Overseas Consortium in +{runstate.chain.partner_supply('overseas'):.0f}{_strike_note('overseas')}",
        f"  surplus out -> {runstate.chain.exportable_surplus():.0f}/cycle",
    ]
    return "\n".join(lines)


def featured_goods_category(week_index=None):
    """H27: the 'challenge of the week' goods category -- deterministic
    rotation by week number, so no backend is needed and every player
    sees the same one. `week_index` defaults to the current UTC week."""
    if week_index is None:
        import time  # noqa: PLC0415
        week_index = int(time.time() // (7 * 24 * 3600))
    keys = list(GOODS_CATEGORIES)
    return keys[week_index % len(keys)]


def reset_chain_message():
    """H30: the confirmation shown after Start New Chain, naming the two
    lifetime counters that survive it."""
    return (
        f"New chain started. Kept from before: {runstate.chains_completed_count} chain(s) completed, "
        f"{len(runstate.goods_categories_tried)} goods categor{'y' if len(runstate.goods_categories_tried) == 1 else 'ies'} tried, "
        f"{len(career_plates)} name plate(s) and your records."
    )


# ===========================================================================
# Round-3 helpers (GH-12/14/15/24/25, H-4/9/15/22/23). Pure functions of state
# (plus the career records), so they are directly testable.
# ===========================================================================
def _supply_options():
    """(label, cost, units supplied per purchase) for every single purchase that adds
    supply right now, with every multiplier applied."""
    mult = runstate.chain.supply_multiplier()
    options = [
        (spec["label"], spec["cost"], spec["supply_per_unit"] * runstate.chain.measure_multiplier(m) * mult)
        for m, spec in CIRCULARITY_INVESTMENTS.items()
    ]
    options.append(("Trade Link", TRADE_LINK_COST, IMPORT_SUPPLY_PER_UNIT * mult))
    options.append(("Regional Partner", REGIONAL_TRADE_COST, REGIONAL_IMPORT_SUPPLY_PER_UNIT * mult))
    options.append(("Overseas Consortium", OVERSEAS_TRADE_COST, OVERSEAS_IMPORT_SUPPLY_PER_UNIT * mult))
    return options


def near_miss_info():
    """GH-25: None, or (units_short, goal_text, fix_text). 'Short' is how far the
    current mix falls below closing the loop or reaching the next 25% step, only when
    that is within NEAR_MISS_UNITS."""
    gap = runstate.chain.new_extraction_needed()
    if gap <= 0:
        return None
    fraction = runstate.chain.circular_fraction_this_cycle()
    next_step = (math.floor(fraction * BURST_MILESTONES + 1e-9) + 1) / BURST_MILESTONES
    short = gap - (1.0 - next_step) * PRODUCTION_TARGET
    limit = NEAR_MISS_UNITS if next_step >= 1.0 else NEAR_MISS_STEP_UNITS
    if short <= 1e-9 or short > limit:
        return None
    goal = "closing the loop" if next_step >= 1.0 else f"the {next_step * 100:.0f}% mark"
    options = _supply_options()
    single = [o for o in options if o[2] >= short - 1e-9]
    if single:
        label, cost, supply = min(single, key=lambda o: (o[1], -o[2]))
        fix = f"{label} ({cost} funds, +{supply:.0f} units) covers it"
    else:
        label, cost, supply = min(options, key=lambda o: math.ceil(short / o[2]) * o[1])
        count = math.ceil(short / supply)
        fix = f"{count} x {label} ({count * cost} funds) would cover it"
    return short, goal, fix


def near_miss_message():
    info = near_miss_info()
    if info is None:
        return ""
    short, goal, fix = info
    shown = math.ceil(short - 1e-9)
    text = f"So close: {shown} unit{'' if shown == 1 else 's'} short of {goal}! Cheapest fix: {fix}."
    cost_note = None
    for label, cost, supply in _supply_options():
        if fix.startswith(label) or f" x {label}" in fix:
            cost_note = cost
            break
    if cost_note is not None and runstate.chain.funds < cost_note:
        text += f" You have {runstate.chain.funds:.0f} funds, so you need {cost_note - runstate.chain.funds:.0f} more."
    return text


def cycle_summary_text():
    """H-4: one plain sentence about the cycle that just finished, for the screen-reader
    live region ('' before any cycle has run)."""
    log = runstate.chain.circular_fraction_log
    if not log:
        return ""
    done = runstate.chain.cycle_number - 1
    now = PRODUCTION_TARGET * (1.0 - log[-1])
    before = PRODUCTION_TARGET * (1.0 - log[-2]) if len(log) >= 2 else None
    # The ledger holds the real extraction (a demand surge can need more than the target).
    if runstate.chain.ledger and runstate.chain.ledger[-1]["cycle"] == done:
        now = runstate.chain.ledger[-1]["extraction"]
        if len(runstate.chain.ledger) >= 2 and runstate.chain.ledger[-2]["cycle"] == done - 1:
            before = runstate.chain.ledger[-2]["extraction"]
    text = f"Cycle {done} complete: {log[-1] * 100:.0f}% circular"
    if before is not None:
        delta = round(before - now)
        if delta > 0:
            text += f", extraction down {delta} unit{'' if delta == 1 else 's'}"
        elif delta < 0:
            text += f", extraction up {-delta} unit{'' if delta == -1 else 's'}"
        else:
            text += ", extraction unchanged"
    else:
        text += f", {now:.0f} units extracted"
    text += "."
    if now <= 0:
        text += f" Loop closed. Combo times {runstate.chain.combo_level()}."
    if runstate.chain.last_insurance_saved:
        text += " Streak insurance held your streak."
    return text


def cost_equation_text():
    """H-15: the extraction price worked out, so the number is not a mystery."""
    mult = runstate.chain.extraction_cost_multiplier()
    spike = runstate.chain.shock_price_multiplier()
    if spike != 1.0:
        return (
            f"Each extracted unit costs: base {EXTRACTION_COST_PER_UNIT:.1f} x damage multiplier {mult:.2f} "
            f"(cap {MAX_COST_MULTIPLIER:.1f}) x price spike {spike:.1f} = "
            f"{EXTRACTION_COST_PER_UNIT * mult * spike:.2f} funds."
        )
    return (
        f"Each extracted unit costs: base {EXTRACTION_COST_PER_UNIT:.1f} x damage multiplier {mult:.2f} "
        f"(cap {MAX_COST_MULTIPLIER:.1f}) = {EXTRACTION_COST_PER_UNIT * mult:.2f} funds."
    )


def combo_text():
    """GH-12: the Perfect Cycle combo line."""
    level = runstate.chain.combo_level()
    gain = runstate.chain.next_combo_gain()
    line = f"Perfect combo: x{level}"
    if level == 0:
        line += " (close the loop for a full cycle to start one)"
    else:
        line += f", {runstate.chain.closed_loop_streak} perfect cycle{'' if runstate.chain.closed_loop_streak == 1 else 's'} in a row"
    if gain > 0:
        line += f". Next perfect cycle banks +{gain:.0f}"
    else:
        line += ". Banking starts with the second perfect cycle in a row"
    line += f". Banked so far: {runstate.chain.perfect_bonus:.0f}."
    if level >= COMBO_CAP:
        line += " (combo maxed)"
    return line


def insurance_text():
    if runstate.chain.insurance_armed:
        return "Streak insurance is armed: your next cycle that needs extraction will not reset the streak."
    if runstate.chain.insurance_used:
        return "Streak insurance already used on this chain."
    if runstate.chain.closed_loop_streak < 1:
        return "Streak insurance (once per chain) protects a streak: close the loop for a cycle first."
    return (
        f"Pay {INSURANCE_COST} funds, once per chain, to freeze your {runstate.chain.closed_loop_streak}-cycle "
        "streak through one cycle that needs extraction."
    )


def rival_lines():
    """GH-5: the comparison lines under the switch ('' list when the rival is off)."""
    if not runstate.chain.rival_on:
        return []
    done = runstate.chain.cycle_number - 1
    mine = runstate.chain.funds
    theirs = rival_funds_after(done)
    gap = mine - theirs
    if done == 0:
        lines = [f"Both of you start with {mine:.0f} funds. Advance a cycle and the race begins."]
    elif abs(gap) < 0.5:
        lines = [f"After {done} cycle{'' if done == 1 else 's'}: level on funds ({mine:.0f} each)."]
    else:
        word = "ahead of" if gap > 0 else "behind"
        lines = [
            f"After {done} cycle{'' if done == 1 else 's'}: you have {mine:.0f} funds, {RIVAL_NAME} has "
            f"{theirs:.0f}. You are {abs(gap):.0f} {word} it."
        ]
    extracted_rival = rival_extracted_after(done)
    saved = extracted_rival - runstate.chain.total_extracted
    if done > 0:
        if saved >= 0:
            lines.append(
                f"{RIVAL_NAME} has dug up {extracted_rival:.0f} units; you have dug up {runstate.chain.total_extracted:.0f}, "
                f"{saved:.0f} fewer."
            )
        else:
            lines.append(
                f"{RIVAL_NAME} has dug up {extracted_rival:.0f} units; you have dug up {runstate.chain.total_extracted:.0f}, "
                f"{-saved:.0f} more (a demand surge can cause that)."
            )
        profit = rival_profit_in_cycle(done)
        damage = min(1.0, extracted_rival / ENVIRONMENTAL_DAMAGE_SCALE)
        if profit < 0.5:
            lines.append(
                f"Its damage is at {damage * 100:.0f}%, so its raw material now costs x{MAX_COST_MULTIPLIER:.1f} "
                "and it earns nothing more from a cycle."
            )
        else:
            lines.append(
                f"Its damage is at {damage * 100:.0f}%, so it now makes only {profit:.0f} funds a cycle "
                "and every extra unit it digs up costs more."
            )
    if runstate.chain.rival_crossover_cycle is not None:
        lines.append(f"You pulled ahead of {RIVAL_NAME} on cycle {runstate.chain.rival_crossover_cycle}.")
    elif done > 0 and gap < 0:
        lines.append("Circularity costs funds up front, so a rival that only digs and sells looks ahead early on. Its costs only climb.")
    return lines


def rival_bar_widths():
    """GH-5: (you %, rival %) bar widths, each against the larger of the two."""
    done = runstate.chain.cycle_number - 1
    mine, theirs = max(0.0, runstate.chain.funds), max(0.0, rival_funds_after(done))
    top = max(mine, theirs, 1.0)
    return round(mine / top * 100), round(theirs / top * 100)


def _report_pool_donation():
    """H11: hands this cycle's donated units to the shared community-pool
    client (batched and rate limited there). Silent without the script."""
    if runstate.chain.last_donation <= 0:
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    pool = getattr(window, "NoyvjPool", None)
    if pool is not None:
        pool.add("loop", "recovered_units", float(runstate.chain.last_donation))


def pool_donation_text():
    if runstate.chain.donate_surplus:
        return (
            f"Donating surplus to the regional pool instead of selling it. You have given "
            f"{runstate.chain.lifetime_pool_donated:.0f} units so far."
        )
    return (
        "Surplus supply is sold outward for funds. Donate it instead and it joins the regional "
        "recycling pool that every player shares (you forgo the sale price)."
    )


def render_pool_donation():
    button = document.getElementById("pool-donate-button")
    button.innerText = "Surplus donation: on" if runstate.chain.donate_surplus else "Surplus donation: off"
    button.setAttribute("aria-pressed", "true" if runstate.chain.donate_surplus else "false")
    document.getElementById("pool-donate-status").innerText = pool_donation_text()


def _requested_count(event=None):
    """How many purchases one click asks for: the chip, or x5 for a shift-click on x1."""
    if runstate.buy_multiple == 1 and getattr(event, "shiftKey", False) is True:
        return 5
    return runstate.buy_multiple


def purchase_label(kind, label):
    """H-14: button text with a running total. x1 keeps the plain 'Label (cost)'."""
    cost = runstate.chain.unit_cost(kind)
    if runstate.buy_multiple == 1:
        return f"{label} ({cost})"
    count = max(1, runstate.chain.affordable_count(kind, runstate.buy_multiple))
    return f"{label} x{count} ({count * cost})"


def spend_confirm_text(count, cost, label):
    return f"Spend {count * cost} of {runstate.chain.funds:.0f} funds on {count} x {label}?"


def mode_status_text():
    """H13/H23: one line describing the modes in force, or '' for none."""
    parts = []
    if runstate.chain.challenge_mode:
        parts.append(
            f"Circular design challenge: all circular supply counts at "
            f"{CHALLENGE_MODE_SUPPLY_MULTIPLIER * 100:.0f}%, so closing the loop takes more investment."
        )
    if runstate.chain.zero_waste:
        used = runstate.chain.total_extracted
        if runstate.chain.zero_waste_holding():
            parts.append(
                f"Zero-waste challenge: {used:.0f} of {ZERO_WASTE_EXTRACTION_CAP:.0f} units extracted "
                f"\u2014 still under the cap."
            )
        else:
            parts.append(
                f"Zero-waste challenge missed: {used:.0f} units extracted, over the "
                f"{ZERO_WASTE_EXTRACTION_CAP:.0f} cap. Play carries on."
            )
    return " ".join(parts)
