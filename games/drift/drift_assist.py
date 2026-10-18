"""The planner assist (off, suggest, explain): the plan suggestion and its summary line."""

from js import document

import drift_runstate as runstate
from drift_model_region import region
from drift_rules import (
    CALENDAR_KINDS, CAPACITY_LABEL, CAPACITY_PER_INVESTMENT, INTEGRATION_RATE_PER_SERVICES_UNIT,
    INVEST_COST, POLICIES, POLICY_BASE_COST, POLICY_MAX_LEVEL,
)


# ---- I-3: planner assist (Off / Suggest / Explain) ---------------------------------------------------
ASSIST_MODES = ("off", "suggest", "explain")
ASSIST_SERVICES_SHARE = 0.35  # services below this share of capacity: buy services before housing
ASSIST_MAX_BUYS = 12
ASSIST_RESERVE = 40.0  # funds left alone when suggesting a policy (economic health reads funds)


def plan_suggestion(rs=None):
    """Recommended purchases for this round as a list of {"kind", "key", "label", "count", "cost", "reason"}.
    Pure advice from the forecast and ROI numbers: nothing is bought. Capacity is sized to cover everyone
    arrived so far plus this round's arrivals (what strain is measured against over the next two advances)."""
    r = region if rs is None else rs
    funds = r.funds
    capacity = dict(r.capacity)
    items = []
    need = r.total_arrivals + r.arrivals_this_round() - r.coverage_bonus()
    have = sum(capacity.values())
    gap_start = max(0.0, need - have)
    bought = {"housing": 0, "services": 0}
    roi = r.investment_roi()
    guard = 0
    while have < need and guard < ASSIST_MAX_BUYS * 3:
        guard += 1
        share = capacity["services"] / have if have > 0 else 0.0
        kind = "services" if share < ASSIST_SERVICES_SHARE else "housing"
        if funds < INVEST_COST[kind]:
            other = "housing" if kind == "services" else "services"
            if funds < INVEST_COST[other]:
                break
            kind = other
        funds -= INVEST_COST[kind]
        capacity[kind] += CAPACITY_PER_INVESTMENT[kind]
        have += CAPACITY_PER_INVESTMENT[kind]
        bought[kind] += 1
    # a backlog that services throughput would take several rounds to clear
    pending = r.pending_population()
    extra_services = 0
    while (
        extra_services < 3 and funds >= INVEST_COST["services"]
        and pending > 0 and capacity["services"] * INTEGRATION_RATE_PER_SERVICES_UNIT * 3 < pending
    ):
        funds -= INVEST_COST["services"]
        capacity["services"] += CAPACITY_PER_INVESTMENT["services"]
        bought["services"] += 1
        extra_services += 1
    gap_text = f"{gap_start:.0f} more capacity covers everyone who has arrived plus this round's {r.arrivals_this_round():.0f}"
    if bought["housing"]:
        items.append({
            "kind": "capacity", "key": "housing", "label": CAPACITY_LABEL["housing"], "count": bought["housing"],
            "cost": bought["housing"] * INVEST_COST["housing"],
            "reason": f"Housing adds the most capacity per fund ({CAPACITY_PER_INVESTMENT['housing']:.0f} for "
                      f"{INVEST_COST['housing']:.0f}); {gap_text}." if gap_start > 0
            else "Housing adds the most capacity per fund, and the extra keeps strain down as arrivals climb.",
        })
    if bought["services"]:
        roi_text = f" Your return so far is {roi:.2f} funds back per fund invested." if roi is not None else ""
        items.append({
            "kind": "capacity", "key": "services", "label": CAPACITY_LABEL["services"], "count": bought["services"],
            "cost": bought["services"] * INVEST_COST["services"],
            "reason": "Integration Services is the only capacity that moves pending people to integrated, "
                      f"and services are {capacity['services'] / max(1.0, have) * 100:.0f}% of your capacity after this."
                      f"{roi_text}",
        })
    # one integration policy once capacity is covered (Community Sponsorship adds less capacity per fund than
    # Housing, so it is never the suggestion)
    if have >= need:
        choice = None
        if pending >= 30 and r.policy_level["language_access"] < POLICY_MAX_LEVEL:
            choice = ("language_access", "Language-Access Funding speeds integration, and "
                      f"{pending:.0f} people are waiting.")
        elif r.integrated_population >= 30 and r.policy_level["credentialing"] < POLICY_MAX_LEVEL:
            choice = ("credentialing", f"Streamlined Credentialing raises what the {r.integrated_population:.0f} "
                      "integrated people contribute back.")
        if choice is not None:
            key, why = choice
            cost = POLICY_BASE_COST * (r.policy_level[key] + 1)
            if funds - cost >= ASSIST_RESERVE:
                funds -= cost
                items.append({
                    "kind": "policy", "key": key, "label": POLICIES[key]["label"], "count": 1, "cost": cost,
                    "reason": why + f" You would still keep {funds:.0f} funds.",
                })
    target = r.brace_target()
    if target is not None:
        brace_cost = CALENDAR_KINDS[target["kind"]]["brace_cost"]
        if funds >= brace_cost:
            funds -= brace_cost
            items.append({
                "kind": "brace", "key": target["kind"], "label": f"Brace for {target['name']}", "count": 1,
                "cost": brace_cost,
                "reason": f"{target['name']} lands in round {target['round']}; bracing softens it for {brace_cost:.0f} funds.",
            })
    if not items:
        items.append({
            "kind": "hold", "key": "hold", "label": "Hold your funds", "count": 0, "cost": 0.0,
            "reason": "Capacity already covers everyone expected by the end of next round and services are keeping up with "
                      "the people waiting. Funds count toward economic health, so keeping them is fine.",
        })
    return items


def plan_summary_line(items):
    if len(items) == 1 and items[0]["kind"] == "hold":
        return "Suggested this round: hold your funds."
    parts = []
    for item in items:
        if item["kind"] == "capacity":
            parts.append(f"{item['count']} {item['label']}")
        else:
            parts.append(item["label"])
    total = sum(item["cost"] for item in items)
    return f"Suggested this round: {', '.join(parts)} ({total:.0f} funds)."


def set_assist_mode(mode):
    """Off / Suggest / Explain. Turning it on tags the run as assisted for good (a rewind or switching it
    back off does not remove the tag); an assisted run never updates a personal best or a tier best."""
    if mode not in ASSIST_MODES:
        return False
    runstate.assist_mode = mode
    if mode != "off":
        runstate.assisted_run = True
    return True


def render_assist():
    for mode in ASSIST_MODES:
        button = document.getElementById(f"assist-{mode}-button")
        button.setAttribute("aria-pressed", "true" if mode == runstate.assist_mode else "false")
        if mode == runstate.assist_mode:
            button.classList.add("active")
        else:
            button.classList.remove("active")
    note = document.getElementById("assist-note")
    if runstate.assisted_run:
        note.innerText = (
            "This run is tagged assisted: personal bests and tier bests will not update for it, "
            "and the tag stays even if you switch assist off. Achievements still count."
        )
    else:
        note.innerText = (
            "Optional advice from the forecast and ROI numbers. Switching it on tags this run as assisted: "
            "it will not update personal bests or tier bests."
        )
    suggestion = document.getElementById("assist-suggestion")
    reasons = document.getElementById("assist-reasons")
    if runstate.assist_mode == "off":
        suggestion.hidden = True
        suggestion.innerText = ""
        reasons.hidden = True
        reasons.innerHTML = ""
        return
    items = plan_suggestion()
    suggestion.hidden = False
    suggestion.innerText = plan_summary_line(items)
    if runstate.assist_mode == "explain":
        reasons.hidden = False
        reasons.innerHTML = "".join(f"<li><strong>{item['label']}:</strong> {item['reason']}</li>" for item in items)
    else:
        reasons.hidden = True
        reasons.innerHTML = ""


def _assist_state_fields():
    return {"assist": {"mode": runstate.assist_mode, "assisted": True}} if runstate.assisted_run else {}


def _load_assist_state(data):
    """Saved only once a run was assisted; anything unreadable loads as a plain unassisted run."""
    runstate.assist_mode = "off"
    runstate.assisted_run = False
    saved = data.get("assist")
    if isinstance(saved, dict) and saved.get("assisted") is True:
        runstate.assisted_run = True
        if saved.get("mode") in ASSIST_MODES:
            runstate.assist_mode = saved["mode"]
