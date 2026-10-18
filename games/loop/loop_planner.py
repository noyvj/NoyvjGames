"""Multi-cycle planner (H-3): plan state, simulation on a copy of the chain, table and summary."""

import copy
import html

from js import document

import loop_runstate as runstate
from loop_model import ChainState
from loop_rules import BUY_KINDS, BUY_LABELS, EXTRACTION_COST_PER_UNIT


# ---- H-3 multi-cycle planner -------------------------------------------------------------------------------------------
PLANNER_SLOTS = 5
PLANNER_MAX_PER_SLOT = 20
PLANNER_SLOT_NAMES = ("This cycle", "Next cycle", "In 2 cycles", "In 3 cycles", "In 4 cycles")

plan = [dict() for _ in range(PLANNER_SLOTS)]  # per slot: {kind: count}; a what-if only, never saved
plan_added = []  # [(slot, kind)] in the order added, for Undo


def plan_total(slot):
    return sum(plan[slot].get(kind, 0) for kind in BUY_KINDS)


def plan_cost(slot):
    return sum(runstate.chain.unit_cost(kind) * plan[slot].get(kind, 0) for kind in BUY_KINDS)


def plan_add(kind, slot=None):
    """Adds one purchase of `kind` to a cycle's slot. False when the kind is unknown, the slot is outside the
    preview window or already holds PLANNER_MAX_PER_SLOT purchases."""
    slot = runstate.planner_slot if slot is None else slot
    if kind not in BUY_KINDS or not (isinstance(slot, int) and 0 <= slot < runstate.planner_horizon):
        return False
    if plan_total(slot) >= PLANNER_MAX_PER_SLOT:
        return False
    plan[slot][kind] = plan[slot].get(kind, 0) + 1
    plan_added.append((slot, kind))
    return True


def plan_undo():
    """Takes back the most recently added purchase."""
    while plan_added:
        slot, kind = plan_added.pop()
        if plan[slot].get(kind, 0) > 0:
            plan[slot][kind] -= 1
            if plan[slot][kind] == 0:
                del plan[slot][kind]
            return True
    return False


def plan_clear():
    for slot in plan:
        slot.clear()
    plan_added.clear()


def plan_shift():
    """One cycle has passed: the plan for the next cycle becomes the plan for this one."""
    plan.pop(0)
    plan.append({})
    plan_added[:] = [(slot - 1, kind) for slot, kind in plan_added if slot > 0]


def _clone_chain():
    twin = ChainState()
    twin.__dict__.update(copy.deepcopy({k: v for k, v in runstate.chain.__dict__.items() if k != "rewind_snapshot"}))
    return twin


def simulate_plan(slots=None, horizon=None):
    """Runs the plan on a COPY of the chain and returns one row per planned cycle: what was bought, what could
    not be afforded, the circular share and extraction going into the cycle, and the funds afterwards. The real
    chain is never touched."""
    slots = plan if slots is None else slots
    horizon = runstate.planner_horizon if horizon is None else horizon
    twin = _clone_chain()
    rows = []
    for i in range(horizon):
        cycle = twin.cycle_number
        bought, short = {}, {}
        for kind in BUY_KINDS:
            wanted = slots[i].get(kind, 0)
            if wanted:
                got = twin.invest_many(kind, wanted)
                bought[kind] = got
                if got < wanted:
                    short[kind] = wanted - got
        extraction = twin.new_extraction_needed()
        row = {
            "cycle": cycle,
            "bought": bought,
            "short": short,
            "fraction": twin.circular_fraction_this_cycle(),
            "extraction": extraction,
            "bill": extraction * EXTRACTION_COST_PER_UNIT * twin.price_multiplier(),
            "closed": extraction <= 0,
        }
        twin.advance_cycle()
        row["funds"] = twin.funds
        rows.append(row)
    return rows


def plan_buys_text(counts):
    parts = [f"{BUY_LABELS[kind]} x{counts[kind]}" for kind in BUY_KINDS if counts.get(kind)]
    return ", ".join(parts) if parts else "no purchases"


def planner_table_html(rows):
    out = [
        '<table class="planner-table"><thead><tr><th>Cycle</th><th>You buy</th><th>Circular</th>'
        "<th>New extraction</th><th class=\"planner-bill\">Extraction bill</th><th>Funds after</th></tr></thead><tbody>"
    ]
    for i, row in enumerate(rows):
        buys = plan_buys_text(row["bought"])
        if row["short"]:
            buys += " (cannot afford " + plan_buys_text(row["short"]) + ")"
        name = PLANNER_SLOT_NAMES[i] if i < len(PLANNER_SLOT_NAMES) else ""
        out.append(
            f"<tr><td>{row['cycle']} <span class=\"planner-when\">{html.escape(name)}</span></td>"
            f"<td>{html.escape(buys)}</td><td>{row['fraction'] * 100:.0f}%{' (closed)' if row['closed'] else ''}</td>"
            f"<td>{row['extraction']:.0f}</td><td class=\"planner-bill\">{row['bill']:.0f}</td><td>{row['funds']:.0f}</td></tr>"
        )
    out.append("</tbody></table>")
    return "".join(out)


def planner_summary_text(rows):
    """One sentence comparing the plan with doing nothing."""
    if not rows:
        return ""
    baseline = simulate_plan([dict() for _ in range(PLANNER_SLOTS)])
    planned_last, base_last = rows[-1], baseline[-1]
    if not any(plan_total(i) for i in range(runstate.planner_horizon)):
        return (
            f"Add some purchases and see where {runstate.planner_horizon} cycles of them lead. Doing nothing leaves you at "
            f"{base_last['fraction'] * 100:.0f}% circular with {base_last['funds']:.0f} funds by cycle {base_last['cycle']}."
        )
    return (
        f"By cycle {planned_last['cycle']} the plan reaches {planned_last['fraction'] * 100:.0f}% circular with "
        f"{planned_last['funds']:.0f} funds; doing nothing would leave {base_last['fraction'] * 100:.0f}% and "
        f"{base_last['funds']:.0f}. A preview only: nothing is bought until you commit this cycle's picks."
    )


def planner_slot_options():
    out = []
    for i in range(PLANNER_SLOTS):
        label = PLANNER_SLOT_NAMES[i]
        count = plan_total(i)
        note = f" ({count} planned)" if count else ""
        disabled = " disabled" if i >= runstate.planner_horizon else ""
        out.append(f'<option value="{i}"{disabled}>{html.escape(label)}{note}</option>')
    return "".join(out)


def render_planner():
    if runstate.planner_slot >= runstate.planner_horizon:
        runstate.planner_slot = runstate.planner_horizon - 1
    rows = simulate_plan()
    document.getElementById("planner-table").innerHTML = planner_table_html(rows)
    document.getElementById("planner-summary").innerText = planner_summary_text(rows)
    slot_select = document.getElementById("planner-slot-select")
    slot_select.innerHTML = planner_slot_options()
    slot_select.value = str(runstate.planner_slot)
    document.getElementById("planner-horizon-select").value = str(runstate.planner_horizon)
    now_total = plan_total(0)
    commit = document.getElementById("planner-commit-button")
    commit.disabled = now_total == 0
    commit.innerText = f"Commit this cycle's picks ({plan_cost(0)})" if now_total else "Commit this cycle's picks"
    document.getElementById("planner-undo-button").disabled = not plan_added
    document.getElementById("planner-clear-button").disabled = not plan_added
    document.getElementById("planner-message").innerText = runstate.planner_message
