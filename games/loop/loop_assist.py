"""Assist (H-8): ranks purchases and writes the hint."""

from js import document

import loop_runstate as runstate
from loop_rules import (
    BUY_KINDS, BUY_LABELS, CIRCULARITY_INVESTMENTS, EXTRACTION_COST_PER_UNIT, IMPORT_SUPPLY_PER_UNIT,
    OVERSEAS_IMPORT_SUPPLY_PER_UNIT, REGIONAL_IMPORT_SUPPLY_PER_UNIT,
)


# ---- H-8 Assist mode ---------------------------------------------------------------------------------------------------
ASSIST_BUTTONS = {
    "repair": "repair-invest-button", "reuse": "reuse-invest-button", "recycle": "recycle-invest-button",
    "trade": "trade-link-invest-button", "regional": "regional-trade-invest-button",
    "overseas": "overseas-trade-invest-button",
}
ASSIST_LABELS = {"off": "Off", "hints": "Hints", "guided": "Guided"}


def assist_options():
    """One entry per kind of purchase: label, cost, the units it would add to a cycle's supply, and how many of
    those would actually be used (supply beyond what this cycle still needs only goes to export)."""
    need = runstate.chain.new_extraction_needed()
    mult = runstate.chain.supply_multiplier()
    out = []
    for kind in BUY_KINDS:
        if kind in CIRCULARITY_INVESTMENTS:
            units = CIRCULARITY_INVESTMENTS[kind]["supply_per_unit"] * runstate.chain.measure_multiplier(kind) * mult
        else:
            per_unit = {"trade": IMPORT_SUPPLY_PER_UNIT, "regional": REGIONAL_IMPORT_SUPPLY_PER_UNIT,
                        "overseas": OVERSEAS_IMPORT_SUPPLY_PER_UNIT}[kind]
            units = 0.0 if runstate.chain.blocked_partner() == kind else per_unit * mult
        cost = runstate.chain.unit_cost(kind)
        out.append({"kind": kind, "label": BUY_LABELS[kind], "cost": cost, "units": units, "used": min(units, need)})
    return out


def assist_best():
    """(best affordable, best overall): the purchase giving the most USED supply per fund, or None for each when the
    loop is already closed or nothing helps. Ties go to the earlier kind in BUY_KINDS."""
    options = [o for o in assist_options() if o["used"] > 0]
    if not options:
        return None, None
    value = lambda o: o["used"] / o["cost"]  # noqa: E731 -- a one-line key
    best_any = max(options, key=lambda o: (round(value(o), 9), -BUY_KINDS.index(o["kind"])))
    affordable = [o for o in options if o["cost"] <= runstate.chain.funds]
    best_now = max(affordable, key=lambda o: (round(value(o), 9), -BUY_KINDS.index(o["kind"]))) if affordable else None
    return best_now, best_any


def assist_hint_text():
    """The Hints line (and, in Guided mode, the reason too). '' when Assist is off."""
    if runstate.chain.assist == "off":
        return ""
    if runstate.chain.is_loop_closed():
        return "The loop is closed this cycle: nothing more is needed. Spare supply is sold or donated."
    best_now, best_any = assist_best()
    if best_any is None:
        return "No purchase would add supply right now (a port strike may have shut a partner)."
    pick = best_now or best_any
    per_fund = pick["cost"] / pick["used"]
    text = (
        f"Best value right now: {pick['label']} ({pick['cost']} funds, +{pick['units']:.0f} units a cycle, "
        f"{per_fund:.1f} funds per unit used)."
    )
    if best_now is None:
        text = f"You cannot afford anything yet. Best to save for: {best_any['label']} ({best_any['cost']} funds, +{best_any['units']:.0f} units a cycle)."
    elif best_any["kind"] != best_now["kind"]:
        text += f" {best_any['label']} is better value but costs {best_any['cost']}."
    if runstate.chain.assist == "guided":
        need = runstate.chain.new_extraction_needed()
        after = max(0.0, need - pick["units"])
        price = EXTRACTION_COST_PER_UNIT * runstate.chain.price_multiplier()
        text += (
            f" Why: it takes this cycle's new extraction from {need:.0f} to {after:.0f} units, which saves about "
            f"{(need - after) * price:.0f} funds on the extraction bill at today's {price:.2f} funds a unit, and again every cycle after."
        )
    return text


def assist_status_text():
    if runstate.chain.assist == "off":
        if runstate.chain.assist_used:
            return "Assist is off now, but this chain stays tagged as assisted."
        return "Off: no hints. Turning it on tags the chain as assisted and keeps it out of your records."
    return "Assist is on. This chain is tagged as assisted and will not count toward your records, speed flags or bests."


def render_assist():
    select = document.getElementById("assist-select")
    select.value = runstate.chain.assist
    document.getElementById("assist-status").innerText = assist_status_text()
    hint = assist_hint_text()
    hint_el = document.getElementById("assist-hint")
    hint_el.innerText = hint
    hint_el.hidden = hint == ""
    best_now, best_any = assist_best() if runstate.chain.assist != "off" else (None, None)
    pick = best_now or best_any
    for kind, button_id in ASSIST_BUTTONS.items():
        button = document.getElementById(button_id)
        if pick is not None and pick["kind"] == kind and runstate.chain.assist != "off":
            button.classList.add("assist-best")
        else:
            button.classList.remove("assist-best")
