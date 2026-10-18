"""Budget Autopilot (rules, log, run), the three budget templates, the run summary text and the civic-tools panel."""

import json

from js import document

import drift_runstate as runstate
from drift_calendar import perfect_fit_message, render_calendar, render_council
from drift_collection import run_stars_message, star_goals, stars_text
from drift_model_region import region
from drift_pages import _read_local_storage_item, _write_local_storage_item
from drift_rules import (
    ACCELERATED_SEVERITY_MULTIPLIER, AUTOPILOT_DEFAULT_RULES, AUTOPILOT_LOG_MAX,
    AUTOPILOT_MAX_BUYS_PER_ROUND, AUTOPILOT_RESERVES, AUTOPILOT_ROUND_CHOICES, AUTOPILOT_SERVICES_SHARES,
    AUTOPILOT_SURPLUS_CHOICES, CAPACITY_LABEL, CAPACITY_TYPES, COUNCIL_BY_ID, INVEST_COST,
)
from drift_tiers import current_tier_id, tier_name
from drift_trendgraph import wellbeing_band, wellbeing_curve
from drift_undo import _run_auto_rounds


autopilot_log = []


# -- GI-5: Budget Autopilot --
def _clean_autopilot(raw):
    """A valid rules dict from anything (unknown or bad values fall back to the defaults)."""
    out = dict(AUTOPILOT_DEFAULT_RULES)
    if not isinstance(raw, dict):
        return out
    if "services_share" in raw and raw["services_share"] in AUTOPILOT_SERVICES_SHARES:
        out["services_share"] = raw["services_share"]
    if "surplus" in raw and raw["surplus"] in AUTOPILOT_SURPLUS_CHOICES:
        out["surplus"] = raw["surplus"]
    reserve = raw.get("reserve")
    if isinstance(reserve, (int, float)) and not isinstance(reserve, bool) and reserve in AUTOPILOT_RESERVES:
        out["reserve"] = int(reserve)
    rounds = raw.get("rounds")
    if isinstance(rounds, int) and not isinstance(rounds, bool) and rounds in AUTOPILOT_ROUND_CHOICES:
        out["rounds"] = rounds
    return out


def _autopilot_log(line):
    autopilot_log.append(line)
    del autopilot_log[:-AUTOPILOT_LOG_MAX]


def _autopilot_pick():
    """The next purchase the rules call for, as (capacity type, reason), or (None, None)."""
    rules = region.autopilot
    spare = region.funds - rules["reserve"]
    target = rules["services_share"]
    if target is not None and spare >= INVEST_COST["services"]:
        total = region.total_capacity()
        share = region.capacity["services"] / total if total > 0 else 0.0
        if share < target:
            return "services", f"services were {share * 100:.0f}% of capacity, target {target * 100:.0f}%"
    surplus = rules["surplus"]
    if surplus is not None and spare >= INVEST_COST[surplus]:
        return surplus, "surplus above the reserve"
    return None, None


def _autopilot_buy_round():
    rules = region.autopilot
    bought = {}
    reasons = {}
    for _ in range(AUTOPILOT_MAX_BUYS_PER_ROUND):
        capacity_type, reason = _autopilot_pick()
        if capacity_type is None or not region.invest(capacity_type):
            break
        bought[capacity_type] = bought.get(capacity_type, 0) + 1
        reasons.setdefault(capacity_type, reason)
    if bought:
        parts = [f"{n} {CAPACITY_LABEL[t]} ({reasons[t]})" for t, n in bought.items()]
        _autopilot_log(f"Round {region.round_number}: bought " + "; ".join(parts) + ".")
    else:
        _autopilot_log(f"Round {region.round_number}: nothing to buy (funds {region.funds:.0f}, reserve {rules['reserve']}).")


def autopilot_run():
    """Run the Budget Autopilot for the set number of rounds. Returns (rounds, reason)."""
    rounds = region.autopilot["rounds"]
    advanced, reason = _run_auto_rounds(rounds, before_round=_autopilot_buy_round)
    unit = "round" if advanced == 1 else "rounds"
    _autopilot_log(f"Stopped after {advanced} {unit}: " + (reason if reason else "the run finished."))
    return advanced, reason


def autopilot_rules_text():
    rules = region.autopilot
    share = "no services-share rule" if rules["services_share"] is None else f"keep services at {rules['services_share'] * 100:.0f}% of capacity"
    surplus = "hold the surplus" if rules["surplus"] is None else f"spend surplus on {CAPACITY_LABEL[rules['surplus']].lower()}"
    return f"Rules: {share}; {surplus}; always keep {rules['reserve']} funds back; run {rules['rounds']} rounds."


def render_autopilot():
    rules = region.autopilot
    share = rules["services_share"]
    document.getElementById("autopilot-share-select").value = "off" if share is None else str(int(round(share * 100)))
    document.getElementById("autopilot-surplus-select").value = "hold" if rules["surplus"] is None else rules["surplus"]
    document.getElementById("autopilot-reserve-select").value = str(rules["reserve"])
    document.getElementById("autopilot-rounds-select").value = str(rules["rounds"])
    document.getElementById("autopilot-run-button").innerText = f"▶ Run Autopilot ({rules['rounds']} rounds)"
    document.getElementById("autopilot-note").innerText = autopilot_rules_text()
    log = document.getElementById("autopilot-log")
    log.innerHTML = "".join(f"<li>{line}</li>" for line in reversed(autopilot_log[-12:]))


# -- GI-21: star ratings --
# ---- I-14: budget templates -------------------------------------------------------------------------
# Three named purchase plans: "Save this round's buys" stores how many Housing, Services and Infrastructure
# purchases you made since the round began; "Apply" buys the same again in one click, as many as the funds allow
# (services first, so the integration engine is never the part that gets cut). Kept per browser, like the
# collection, so a plan can be reused in the next region; never part of a save.
TEMPLATE_SLOTS = 3
TEMPLATE_STORAGE_KEY = "drift_budget_templates_v1"
TEMPLATE_NAME_MAX = 20
TEMPLATE_MAX_BUYS = 20
TEMPLATE_BUY_ORDER = ["services", "housing", "infrastructure"]


def _default_templates():
    return [{"name": f"Plan {i + 1}", "buys": {}} for i in range(TEMPLATE_SLOTS)]


def _clean_templates(raw):
    """Exactly TEMPLATE_SLOTS well-formed plans from anything: names trimmed and capped, buy counts 1..20."""
    out = _default_templates()
    if not isinstance(raw, list):
        return out
    for slot, entry in enumerate(raw[:TEMPLATE_SLOTS]):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if isinstance(name, str) and name.strip():
            out[slot]["name"] = name.strip()[:TEMPLATE_NAME_MAX]
        buys = entry.get("buys")
        if isinstance(buys, dict):
            for kind in CAPACITY_TYPES:
                count = buys.get(kind)
                if isinstance(count, int) and not isinstance(count, bool) and 1 <= count <= TEMPLATE_MAX_BUYS:
                    out[slot]["buys"][kind] = count
    return out


def _load_templates():
    raw = _read_local_storage_item(TEMPLATE_STORAGE_KEY)
    if not raw:
        return _default_templates()
    try:
        return _clean_templates(json.loads(raw))
    except (ValueError, TypeError):
        return _default_templates()


budget_templates = _load_templates()


def round_purchase_counts():
    """How many purchases of each capacity type were made since this round began (from the funds spent)."""
    return {
        kind: int(round(region.round_spend.get(kind, 0.0) / INVEST_COST[kind]))
        for kind in CAPACITY_TYPES
    }


def template_summary(template):
    parts = [f"{CAPACITY_LABEL[kind]} {template['buys'][kind]}" for kind in TEMPLATE_BUY_ORDER if kind in template["buys"]]
    return ", ".join(parts) if parts else "empty: buy something, then save it"


def save_template(slot, name):
    """Stores this round's purchases as plan `slot`; False when nothing was bought this round."""
    counts = {kind: min(TEMPLATE_MAX_BUYS, n) for kind, n in round_purchase_counts().items() if n > 0}
    if not counts or not 0 <= slot < TEMPLATE_SLOTS:
        return False
    clean = name.strip()[:TEMPLATE_NAME_MAX] if isinstance(name, str) and name.strip() else f"Plan {slot + 1}"
    budget_templates[slot] = {"name": clean, "buys": counts}
    _write_local_storage_item(TEMPLATE_STORAGE_KEY, json.dumps(budget_templates))
    return True


def rename_template(slot, name):
    if not 0 <= slot < TEMPLATE_SLOTS or not isinstance(name, str) or not name.strip():
        return False
    budget_templates[slot]["name"] = name.strip()[:TEMPLATE_NAME_MAX]
    _write_local_storage_item(TEMPLATE_STORAGE_KEY, json.dumps(budget_templates))
    return True


def apply_template(slot):
    """Buys plan `slot` with what the funds allow; returns (bought, short) as {type: count} dicts."""
    template = budget_templates[slot]
    bought, short = {}, {}
    for kind in TEMPLATE_BUY_ORDER:
        want = template["buys"].get(kind, 0)
        done = 0
        while done < want and region.invest(kind):
            done += 1
        if done:
            bought[kind] = done
        if done < want:
            short[kind] = want - done
    return bought, short


def _counts_text(counts):
    return ", ".join(f"{n} {CAPACITY_LABEL[kind]}" for kind, n in counts.items())


def render_templates():
    for slot, template in enumerate(budget_templates):
        number = slot + 1
        document.getElementById(f"template-{number}-name").value = template["name"]
        document.getElementById(f"template-{number}-summary").innerText = template_summary(template)
        document.getElementById(f"template-{number}-save").disabled = not any(round_purchase_counts().values())
        document.getElementById(f"template-{number}-apply").disabled = not template["buys"]
    document.getElementById("template-note").innerText = runstate.template_note


def run_summary_text():
    name = region.region_name or "Unnamed region"
    completed = max(0, region.round_number - 1)
    score = region.wellbeing_score()
    tags = [f"Tier {tier_name(current_tier_id())}"]
    if runstate.assisted_run:
        tags.append("Assisted run")
    if region.accelerated_severity_enabled:
        tags.append(f"Accelerated Severity ({ACCELERATED_SEVERITY_MULTIPLIER:.0f}x)")
    if region.crisis_start_enabled:
        tags.append("Crisis Start")
    if region.calendar_enabled:
        tags.append("Crisis Calendar")
    if region.council_picks:
        tags.append("Council: " + ", ".join(COUNCIL_BY_ID[pid]["name"] for pid in region.council_picks))
    goals = star_goals()
    lines = [
        f"Drift: {name}",
        f"After {completed} rounds: {wellbeing_band(score)}, wellbeing {score:.0f}, strain {region.strain_level()}",
        f"Wellbeing curve: {wellbeing_curve(region.wellbeing_log)}",
        "Setup: " + ("; ".join(tags) if tags else "standard"),
        f"Stars: wellbeing {stars_text(goals['wellbeing'])} speed {stars_text(goals['speed'])} efficiency {stars_text(goals['efficiency'])}",
    ]
    return "\n".join(lines)


def render_civic_tools():
    document.getElementById("perfect-fit-display").innerText = perfect_fit_message()
    render_calendar()
    render_council()
    render_autopilot()
    render_templates()
    document.getElementById("run-stars-display").innerText = run_stars_message()
