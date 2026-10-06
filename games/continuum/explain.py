"""Continuum -- K-16: the "why did that change" explainer.

Hovering (or focusing) a City Views dashboard stat shows the top three
things that moved it over the last completed season, as a small waterfall:
one signed line per factor, and the net change they add up to.

Everything is derived from numbers the game already has: the last two rows
of the per-season stat history (`statlog.py`) and the season report. Where
the season report names a flow (food gathered, eaten, spoiled, births...) it
is shown by name; whatever is left over between the two recorded seasons is
the player's own choices (a building raised, a discovery studied), which the
report cannot see, and is shown as "Your choices" or "Other changes", so the
factors always add up to the change. Stats with no honest breakdown
(equity, resource balance, resilience, ...) simply get no explainer rather
than an invented one.

Pure functions, no DOM. Nothing here changes the simulation.
"""

import math

import sim
import statlog
import sustainability

# Smaller than this is not worth a line (it would read as "+0.0").
MIN_FACTOR = 0.05
TOP_FACTORS = 3

# Stats this module can break down.
EXPLAINABLE = (
    "population",
    "food",
    "materials",
    "tools",
    "knowledge",
    "surplus",
    "land",
    "score",
    "livability",
)


def _flow(report, key):
    if not isinstance(report, dict):
        return 0.0
    value = report.get(key, 0.0)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return 0.0
    return float(value)


def delta(history, key):
    """The change in one column between the last two recorded seasons, or
    None when there are not two rows (or the column is unknown)."""
    if key not in statlog.COLUMN_KEYS or len(history) < 2:
        return None
    return statlog.value(history[-1], key) - statlog.value(history[-2], key)


def _season_matches(history, report):
    """True when the season report is the one the last history row recorded
    (a save from before the history existed, or a revisit, can differ)."""
    return (
        isinstance(report, dict)
        and history
        and int(statlog.value(history[-1], "season")) == int(_flow(report, "season"))
    )


def _stock_factors(key, history, report):
    """Known flows for one stock, as [(label, signed amount)]."""
    if key == "food":
        spilled = _flow(report, "spoiled") + _flow(report, "surplus_banked")
        return [
            ("Gathered", _flow(report, "food_gathered")),
            ("Eaten", -_flow(report, "food_consumed")),
            ("Over the storage limit", -spilled),
        ], "Other changes"
    if key == "population":
        return [("Born", _flow(report, "births")), ("Lost", -_flow(report, "deaths"))], "Other changes"
    if key == "materials":
        return [
            ("Gathered", _flow(report, "materials_gathered")),
            ("Made into tools", -_flow(report, "tools_made") * sim.MATERIALS_PER_TOOL),
        ], "Your choices (building)"
    if key == "tools":
        made = _flow(report, "tools_made")
        before = statlog.value(history[-2], "tools")
        wear = (before + made) * sim.TOOL_DECAY_RATE
        return [("Made", made), ("Wear", -wear)], "Your choices"
    if key == "knowledge":
        return [("Written down", _flow(report, "knowledge_made"))], "Your choices (studying)"
    if key == "surplus":
        return [
            ("Banked", _flow(report, "surplus_banked")),
            ("Sent to the holdings", -_flow(report, "relay_delivered")),
        ], "Your choices"
    return [], "Other changes"


def _land_factors(history, report, effects):
    taken = _flow(report, "extraction")
    allowed = _flow(report, "sustainable_yield")
    if taken > allowed:
        return [("Taken beyond what the land can give back", -(taken - allowed) * sim.LAND_DEGRADE_PER_UNIT * 100.0)]
    regen = sim.LAND_REGEN * sim.effects_or_neutral(effects).get("regen_mult", 1.0)
    return [("Recovering, because less was taken than it can give back", regen * 100.0)]


def _score_factors(history):
    """Each component's change, weighted into score points (they sum to the
    score change, apart from the 0..100 clamp)."""
    out = []
    for name in sustainability.COMPONENTS:
        change = statlog.value(history[-1], name) - statlog.value(history[-2], name)
        out.append((sustainability.COMPONENT_LABEL[name], change * sustainability.COMPONENT_WEIGHTS[name]))
    return out


def _livability_factors(history):
    eras = int(statlog.value(history[-1], "era"))
    columns = [("Food security", "fed_pct"), ("Shelter", "shelter_pct"), ("Gathering places", "social_pct")]
    if eras >= sim.era_index("space"):
        columns.append(("Habitat layout", "habitat_pct"))
    count = len(columns)
    return [
        (label, (statlog.value(history[-1], col) - statlog.value(history[-2], col)) / count)
        for label, col in columns
    ]


def _unit(key):
    kind = statlog.COLUMN_KIND.get(key, "num")
    return "pct" if kind == "pct" else "int" if kind == "int" else "num"


def explain(key, history, report, effects=None):
    """The waterfall for one stat, or None when there is nothing honest to say.

    Returns {"key", "label", "net", "factors": [(label, amount)], "other":
    float, "unit": "num"|"int"|"pct"}. `factors` holds at most the top three
    by size; `other` is whatever the rest add up to, so factors + other = net.
    """
    if key not in EXPLAINABLE:
        return None
    net = delta(history, key)
    if net is None:
        return None
    factors = []
    remainder_label = None
    if key in ("population", "food", "materials", "tools", "knowledge", "surplus"):
        if _season_matches(history, report):
            factors, remainder_label = _stock_factors(key, history, report)
        else:
            remainder_label = "Other changes"
    elif key == "land":
        if _season_matches(history, report):
            factors = _land_factors(history, report, effects)
        remainder_label = "Other changes"
    elif key == "score":
        factors = _score_factors(history)
    elif key == "livability":
        factors = _livability_factors(history)
    known = sum(amount for _, amount in factors)
    if remainder_label is not None:
        rest = net - known
        if abs(rest) >= MIN_FACTOR:
            factors.append((remainder_label, rest))
    factors = [(label, amount) for label, amount in factors if abs(amount) >= MIN_FACTOR]
    if not factors and abs(net) < MIN_FACTOR:
        return {"key": key, "label": statlog.COLUMN_LABEL[key], "net": 0.0, "factors": [], "other": 0.0, "unit": _unit(key)}
    factors.sort(key=lambda item: abs(item[1]), reverse=True)
    top = factors[:TOP_FACTORS]
    other = net - sum(amount for _, amount in top)
    if abs(other) < MIN_FACTOR:
        other = 0.0
    return {
        "key": key,
        "label": statlog.COLUMN_LABEL[key],
        "net": net,
        "factors": top,
        "other": other,
        "unit": _unit(key),
    }


def _amount_text(amount, unit):
    digits = 0 if unit == "int" else 1
    rounded = round(amount, digits)
    sign = "+" if rounded > 0 else "−" if rounded < 0 else ""
    suffix = " points" if unit == "pct" else ""
    return f"{sign}{abs(rounded):.{digits}f}{suffix}"


def amount_text(amount, unit):
    """A signed amount as text (the sign is always in the words, never only a colour)."""
    return _amount_text(amount, unit)


def waterfall_lines(explained):
    """Plain-text lines for a screen reader and for tests:
    ['Gathered +6.0', 'Eaten -4.0', ..., 'Net change +2.0']."""
    if explained is None:
        return []
    unit = explained["unit"]
    lines = [f"{label} {_amount_text(amount, unit)}" for label, amount in explained["factors"]]
    if explained["other"]:
        lines.append(f"Everything else {_amount_text(explained['other'], unit)}")
    lines.append(f"Net change {_amount_text(explained['net'], unit)}")
    return lines


def waterfall_geometry(explained):
    """The drawing data for the waterfall: one bar per factor, floating from
    the running total before it to the running total after it, then a final
    bar from zero to the net change.

    Returns [{"label", "amount", "left", "width", "kind"}] with `left` and
    `width` in percent of the bar track and `kind` one of "up", "down",
    "net". The first bar starts at zero.
    """
    if explained is None:
        return []
    steps = list(explained["factors"])
    if explained["other"]:
        steps.append(("Everything else", explained["other"]))
    running = 0.0
    spans = []
    for label, amount in steps:
        spans.append((label, amount, running, running + amount, "up" if amount >= 0 else "down"))
        running += amount
    spans.append(("Net change", explained["net"], 0.0, explained["net"], "net"))
    points = [0.0] + [s[2] for s in spans] + [s[3] for s in spans]
    low, high = min(points), max(points)
    extent = (high - low) or 1.0
    out = []
    for label, amount, start, end, kind in spans:
        left = (min(start, end) - low) / extent * 100.0
        width = max(abs(end - start) / extent * 100.0, 2.0)
        out.append(
            {
                "label": label,
                "amount": amount,
                "left": round(min(left, 100.0 - width), 1),
                "width": round(width, 1),
                "kind": kind,
            }
        )
    return out
