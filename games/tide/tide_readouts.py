"""Storm forecast, plain labels, hard-lag toggle, acidity past, afford list, goals, quiet seasons, harbor names, the season forecast and the community coastline panel."""

import copy
import html
import math

from js import document

import tide_runstate as runstate
from tide_bridge import _read_local_storage_item
from tide_chrome import announce
from tide_rules import (
    ADAPTATION_TIERS, DIVERSIFY_COST, DIVERSIFY_MAX_LEVEL, HERITAGE_UPKEEP, INVEST_COST, INVEST_LABELS,
    OUTPUT_INCOME_PER_UNIT, OUTPUT_MIX,
)


# D-29 (2026-10-09): plain-language label mode (Settings). Longest phrases first so "damage dampening" wins over "dampening".
PLAIN_LABELS_KEY = "tide-plain-labels"
PLAIN_REPLACEMENTS = (
    ("Harder Lag", "Slower fish effects"),
    ("Acidity Reduction", "Cut acidity"),
    ("damage dampening", "damage protection"),
    ("dampening", "protection"),
    ("Adaptation", "Sea defences"),
    ("adaptation", "sea defences"),
    ("Output", "Income"),
    ("delay", "delay"),
    ("lag", "delay"),
)


def plain_labels_on():
    return _read_local_storage_item(PLAIN_LABELS_KEY) == "true"


def plain(text):
    """The text in everyday words when the setting is on, otherwise unchanged."""
    if not plain_labels_on() or not isinstance(text, str):
        return text
    for old, new in PLAIN_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def render_hard_lag_toggle():
    """D9: keeps the toggle button's label in sync with the live mode."""
    button = document.getElementById("hard-lag-toggle-button")
    if button is not None:
        button.innerText = plain(
            "Harder Lag: On (turn off)" if runstate.state.hard_lag_mode else "Harder Lag: Off (turn on)"
        )


# FY-2 (Tide D10): the acidity from three seasons ago, shown beside the
# current one so the delay between cause and effect is visible as numbers.
ACIDITY_PAST_SEASONS = 3


def acidity_past_text():
    """'Three seasons ago: acidity 2.3 (now 3.1, up 0.8)' once three seasons are banked."""
    history = runstate.state.acidity_history
    if len(history) < ACIDITY_PAST_SEASONS:
        return f"Three seasons ago: not yet played ({len(history)} of {ACIDITY_PAST_SEASONS} seasons banked)"
    past = history[-ACIDITY_PAST_SEASONS]
    change = runstate.state.acidity - past
    if abs(change) < 0.05:
        word = "unchanged"
    elif change > 0:
        word = f"up {change:.1f}"
    else:
        word = f"down {-change:.1f}"
    return f"Three seasons ago: acidity {past:.1f} (now {runstate.state.acidity:.1f}, {word})"


# ===========================================================================
# 2026-10-09 pass: D-19 affordability, D-20 net-funds chip, GD-19 pinned goal, GD-25 quiet seasons, GD-26 name dice
# ===========================================================================

AFFORD_PIN_KEY = "tide_afford_pin_v1"


def season_net_income():
    """Funds gained in one more season at today's numbers: output (fish-tied part included), diversification, less heritage upkeep."""
    mix = OUTPUT_MIX[runstate.state.output_mix]
    income = runstate.state.capacity["output"] * OUTPUT_INCOME_PER_UNIT * (
        mix["fishing_share"] * runstate.state.fish_yield_multiplier() + (1 - mix["fishing_share"])
    )
    if runstate.state.coast_weight("output") != 1.0:  # D-8
        income *= runstate.state.coast_weight("output")
    tourism, aquaculture = runstate.state.diversified_income()
    return income + tourism + aquaculture - HERITAGE_UPKEEP * runstate.state.protected_heritage_count()


def seasons_to_afford(cost, funds=None, income=None):
    """0 when affordable now, a whole number of seasons otherwise, None when income will never cover it."""
    funds = runstate.state.funds if funds is None else funds
    income = season_net_income() if income is None else income
    if funds >= cost:
        return 0
    if income <= 0:
        return None
    return int(math.ceil((cost - funds) / income))


def afford_targets():
    """(id, label, total cost) for each adaptation tier still ahead and each diversification level still open."""
    out = []
    for i, tier in enumerate(ADAPTATION_TIERS):
        if i > runstate.state.current_tier_index():
            missing = max(0, tier["threshold"] - runstate.state.capacity["adaptation"])
            out.append((f"tier{i}", f"{tier['name']} (tier {i})", missing * runstate.state.invest_cost("adaptation")))
    for kind, label in (("tourism", "Tourism"), ("aquaculture", "Aquaculture")):
        level = runstate.state.diversification[kind]
        if level < DIVERSIFY_MAX_LEVEL:
            out.append((f"div-{kind}", f"{label} level {level + 1}", DIVERSIFY_COST[kind]))
    return out


def afford_text_for(cost):
    n = seasons_to_afford(cost)
    if n == 0:
        return "affordable now"
    if n is None:
        return "not affordable at current income"
    return f"affordable in {n} season{'s' if n != 1 else ''} at current income"


def afford_lines():
    pinned = runstate.afford_pin
    lines = []
    for target_id, label, cost in afford_targets():
        mark = "\U0001F4CC " if target_id == pinned else ""
        lines.append(f"{mark}{label}: {cost} funds, {afford_text_for(cost)}.")
    return lines


def load_afford_pin():
    value = _read_local_storage_item(AFFORD_PIN_KEY)
    runstate.afford_pin = value if isinstance(value, str) else ""


def render_afford():
    box, select = document.getElementById("afford-list"), document.getElementById("afford-pin-select")
    targets = afford_targets()
    if box is not None:
        lines = afford_lines()
        box.innerText = "\n".join(lines) if lines else "Every adaptation tier and diversification level is already in place."
    if select is not None:
        select.innerHTML = ""
        none = document.createElement("option")
        none.value = ""
        none.innerText = "No pinned target"
        select.appendChild(none)
        for target_id, label, _cost in targets:
            option = document.createElement("option")
            option.value = target_id
            option.innerText = label
            select.appendChild(option)
        select.value = runstate.afford_pin if any(t[0] == runstate.afford_pin for t in targets) else ""
    pinned_el = document.getElementById("afford-pinned")
    if pinned_el is not None:
        pin = next((t for t in targets if t[0] == runstate.afford_pin), None)
        pinned_el.innerText = f"\U0001F4CC {pin[1]}: {afford_text_for(pin[2])}." if pin else ""


def net_funds_preview(category):
    cost = runstate.state.invest_cost(category)
    after = runstate.state.funds - cost
    upkeep = HERITAGE_UPKEEP * runstate.state.protected_heritage_count()
    return {"cost": cost, "after_purchase": after, "upkeep": upkeep, "after_upkeep": max(0, after - upkeep), "affordable": after >= 0}


def net_funds_text(category):
    if category not in INVEST_COST:
        return ""
    p = net_funds_preview(category)
    label = INVEST_LABELS[category]
    if not p["affordable"]:
        return f"{label} costs {p['cost']}: you have {runstate.state.funds:.0f}, so {-p['after_purchase']:.0f} more funds are needed."
    upkeep = f"{p['after_upkeep']:.0f} after this season's upkeep of {p['upkeep']}" if p["upkeep"] else "no upkeep due this season"
    return f"{label}: funds {runstate.state.funds:.0f}, then {p['after_purchase']:.0f} after buying, {upkeep}."


def _make_net_funds_handler(category):
    def handler(event=None):
        chip = document.getElementById("net-funds-chip")
        if chip is not None:
            chip.innerText = net_funds_text(category) if category else ""
    return handler


# GD-19: goals the player can pin. Each is (label, current value, target value); reached when current >= target.
GOALS = {
    "rows4": ("Keep 4 rows dry", lambda: runstate.state.rows_dry_count(), 4),
    "rows5": ("Keep 5 rows dry", lambda: runstate.state.rows_dry_count(), 5),
    "pop200": ("Reach 200 population", lambda: runstate.state.population, 200),
    "tier3": ("Reach the Reinforced seawalls tier", lambda: runstate.state.current_tier_index(), 3),
    "funds500": ("Hold 500 funds", lambda: runstate.state.funds, 500),
    "fish90": ("Bring fishing yield to 90%", lambda: runstate.state.fish_yield_multiplier() * 100, 90),
    "heritage2": ("Protect both heritage sites", lambda: runstate.state.protected_heritage_count(), 2),
    "quiet5": ("Five quiet seasons in a row", lambda: runstate.state.quiet_seasons(), 5),
}


def goal_progress():
    """(label, current, target, reached) for the pinned goal, or None."""
    entry = GOALS.get(runstate.state.pinned_goal)
    if entry is None:
        return None
    label, current_fn, target = entry
    current = current_fn()
    return label, current, target, current >= target


def pin_goal(goal_id):
    """Pins one goal (or clears with ''). Pinning a goal that is already met does not ping again."""
    if goal_id != "" and goal_id not in GOALS:
        return False
    runstate.state.pinned_goal = goal_id
    runstate.state.pinned_goal_reached = bool(goal_id) and goal_progress()[3]
    return True


def check_pinned_goal():
    """Fires the one ping when the pinned goal is first reached."""
    progress = goal_progress()
    if progress is None or runstate.state.pinned_goal_reached or not progress[3]:
        return False
    runstate.state.pinned_goal_reached = True
    message = f"Goal reached: {progress[0]}."
    runstate.state._log_ticker(message)
    runstate.state._chronicle_event(message)
    announce(message)
    return True


def render_goal():
    select, bar, text = document.getElementById("goal-select"), document.getElementById("goal-bar"), document.getElementById("goal-text")
    if select is not None:
        if select.innerHTML == "" or len(getattr(select, "children", [])) != len(GOALS) + 1:
            select.innerHTML = ""
            none = document.createElement("option")
            none.value = ""
            none.innerText = "No pinned goal"
            select.appendChild(none)
            for goal_id, (label, _fn, _target) in GOALS.items():
                option = document.createElement("option")
                option.value = goal_id
                option.innerText = label
                select.appendChild(option)
        select.value = runstate.state.pinned_goal
    progress = goal_progress()
    if bar is not None:
        bar.style.width = f"{min(100, 100 * progress[1] / progress[2]):.0f}%" if progress else "0%"
    if text is not None:
        text.innerText = (f"{progress[0]}: {progress[1]:.0f} of {progress[2]}" + (" (reached!)" if progress[3] else "")) if progress else "Pin one goal to track it here."


def quiet_seasons_text():
    n = runstate.state.quiet_seasons()
    stars = "\u2605\u2605" if n >= 10 else "\u2605" if n >= 5 else ""
    return f"Quiet seasons (acidity not rising): {n} {stars}".strip()


def render_quiet():
    el = document.getElementById("quiet-seasons-display")
    if el is None:
        return
    n = runstate.state.quiet_seasons()
    el.innerText = quiet_seasons_text()
    el.className = "meter-label quiet-seasons" + (" quiet-glow quiet-glow-10" if n >= 10 else " quiet-glow quiet-glow-5" if n >= 5 else "")


HARBOR_NAMES = [
    "Port Regret", "Kelp Junction", "Saltwick", "Mussel Landing", "Driftwood Cove", "Brine Bay", "Lantern Quay",
    "Tidewater", "Gull's Rest", "Pebble Harbour", "Samphire", "Anchor Hollow", "Low Tide Lane", "Barnacle Point",
    "Cormorant Wharf", "Eelgrass End", "Mooring Mile", "Sandbar Rise", "Haven Foam", "Windward Quay", "Oyster Row",
    "Seaglass Bay", "Rope Walk", "Halyard Hill",
]
_harbor_rolls = {"n": 0}


def roll_harbor_name():
    """The next fun harbour name: a fixed walk through the list from a start that depends on the season, so it is repeatable."""
    n = _harbor_rolls["n"]
    _harbor_rolls["n"] += 1
    index = (n * 7 + runstate.state.season * 5) % len(HARBOR_NAMES)
    if HARBOR_NAMES[index] == runstate.state.settlement_name:
        index = (index + 1) % len(HARBOR_NAMES)
    return HARBOR_NAMES[index]


def apply_rolled_name(name):
    first = not runstate.state.settlement_name
    runstate.state.set_settlement_name(name)
    if first:
        if not any("Founded" in e["text"] for e in runstate.state.chronicle):
            runstate.state.chronicle.insert(0, {"season": runstate.state.season, "text": f"Founded as {runstate.state.settlement_name}."})
    else:
        runstate.state._chronicle_event(f"The harbour came to be called {runstate.state.settlement_name}.")
    return runstate.state.settlement_name


# ===========================================================================
# 2026-10-11 pass: GN-9 "next season if you do nothing"
# ===========================================================================

FORECAST_KEY = "tide-season-forecast"  # "off" hides the line (Settings); absent means on


def forecast_on():
    return _read_local_storage_item(FORECAST_KEY) != "off"


def _forecast_numbers(sim):
    return {
        "funds": sim.funds, "acidity": sim.acidity, "fish_yield": sim.fish_yield_multiplier(),
        "sea_level": sim.sea_level, "damage": sim.cumulative_damage, "rows_dry": sim.rows_dry_count(),
    }


def season_forecast():
    """What the next season would leave if you invested nothing more and just advanced: {"now": {...}, "next": {...}}.
    The game's own advance_season() runs on a deep COPY of the settlement (the same way the Season Planner projects), so
    income, upkeep, wages, the fish lag, the sea, storms and deals all follow the real rules and the real run is never touched."""
    real = runstate.state
    now = _forecast_numbers(real)
    simulated = copy.deepcopy(real)
    runstate.state = simulated
    try:
        simulated.advance_season()
        after = _forecast_numbers(simulated)
    finally:
        runstate.state = real
    return {"now": now, "next": after}


def _forecast_delta_text(delta, digits):
    text = f"{delta:+.{digits}f}"
    if float(text) == 0 and abs(delta) > 1e-9:
        text = f"{delta:+.{digits + 1}f}"
    return text.replace("-", "\u2212")


FORECAST_CHIPS = (
    ("funds", "\U0001F4B0", "Funds", 0, "Funds: this season's income from output, tourism and aquaculture, less heritage upkeep, crew wages and any storm repairs."),
    ("acidity", "\U0001F9EA", "Acidity", 1, "Ocean acidity: what output pushes up less what your reduction pulls down."),
    ("fish_yield", "\U0001F41F", "Fishing yield", 0, "Fishing yield: it follows the acidity from several seasons ago, so today's choices barely move it yet."),
    ("sea_level", "\U0001F30A", "Sea level", 0, "Sea level: it rises every season whatever you do; adaptation only cuts the damage it does."),
    ("damage", "\u26A0\uFE0F", "Damage", 0, "Cumulative damage from the rising sea, after your adaptation tier's dampening."),
)


def forecast_chips():
    """[(key, text, tooltip)] for the line beside the readouts. Arrows say up, down or no change in words as well as shape."""
    data = season_forecast()
    now, after = data["now"], data["next"]
    chips = []
    for key, icon, label, digits, tip in FORECAST_CHIPS:
        scale = 100.0 if key == "fish_yield" else 1.0
        unit = "%" if key == "fish_yield" else ""
        a, b = now[key] * scale, after[key] * scale
        delta = b - a
        arrow = "\u25B2" if round(delta, digits + 1) > 0 else "\u25BC" if round(delta, digits + 1) < 0 else "\u2022"
        change = _forecast_delta_text(delta, digits) + unit if arrow != "\u2022" else "no change"
        text = f"{icon} {label} {a:.{digits}f}{unit} \u2192 {b:.{digits}f}{unit} {arrow} {change}"
        chips.append((key, text, f"{tip} Worked out with the game's own rules on a copy of your settlement; nothing is spent or changed."))
    if now["rows_dry"] != after["rows_dry"]:
        lost = after["rows_dry"] - now["rows_dry"]
        chips.append(("rows_dry", f"\U0001F5FA\uFE0F Dry rows {now['rows_dry']} \u2192 {after['rows_dry']} \u25BC {_forecast_delta_text(lost, 0)}",
                      "Coastline rows still above water: the sea would take this many next season."))
    return chips


def render_forecast():
    line = document.getElementById("forecast-line")
    if line is None:
        return
    if not forecast_on():
        line.hidden = True
        line.innerHTML = ""
        return
    chips = forecast_chips()
    line.hidden = False
    line.setAttribute("aria-label", "Next season if you do nothing: " + "; ".join(text for _key, text, _tip in chips))
    line.innerHTML = (
        '<span class="forecast-lead" title="Advance now without investing anything more and this is what the readouts would show. '
        'It is a projection, not a promise: a deal, a storm or a crew change you make first can change it.">Next season if you do nothing:</span> '
        + " ".join(
            f'<span class="forecast-chip forecast-chip--{key}" title="{html.escape(tip, quote=True)}">{html.escape(text)}</span>'
            for key, text, tip in chips
        )
    )


def render_sister():
    button = document.getElementById("sister-enable-button")
    text = document.getElementById("sister-display")
    button.hidden = runstate.state.sister_enabled
    text.hidden = not runstate.state.sister_enabled
    text.innerText = runstate.state.sister_text()
