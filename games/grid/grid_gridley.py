"""Gridley, the one-line commentator (GC-19), the supply-against-demand needle gauge (GC-28) and operator ranks (C-17).
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import MAX_REVENUE_LOSS_FRACTION, RANK_THEMES
from grid_prefs import format_demand
from grid_achievements import renewable_capacity_share


# ---- GC-19 Gridley, the dry one-line commentator --------------------------------------------------------------
# A single wry line about how the last round went, in a fixed dry voice (never about the player, never a number, never
# a hint). Which line is picked comes from the run's seed and the round (a stateless stream), so the same run says the
# same things. Off with the Settings checkbox; it never touches a rule and nothing is saved.
GRIDLEY_LINES = {
    "welcome": (
        "Gridley here. Demand only goes up, so I would build something.",
        "Gridley, your grid's commentator. I comment, you build. We will see who has the harder job.",
        "Welcome to the control room. The coffee is cold and demand is rising, both on schedule.",
    ),
    "brownout": (
        "That was a brownout. The grid sends its regrets, and so does your balance sheet.",
        "The lights flickered out. Somewhere a kettle is going to need an explanation.",
        "A disruption. The emissions meter had been trying to tell you, politely.",
    ),
    "damage": (
        "A plant gave up on the spot. It had a decent run.",
        "Equipment damage. The insurance form is, as ever, longer than the repair.",
        "One unit lost to the storm of your own making. Dignified, in its way.",
    ),
    "aging": (
        "A tired old unit retired itself without paperwork.",
        "An aging breakdown. Maintenance was available, as I recall.",
        "Something rusty finally let go. We will miss it for about a round.",
    ),
    "perfect": (
        "Nothing broke and everyone had power. I am almost suspicious.",
        "A perfect round. Please write down what you did before it wears off.",
        "Smooth. Even the transformers are quietly pleased.",
    ),
    "short": (
        "Demand is ahead of you. It usually is.",
        "The gap between supply and demand is open for business again.",
        "More people want power than you have built. A fine problem, as problems go.",
    ),
    "clean": (
        "More than half renewable. The coal plant is pretending not to notice.",
        "A mostly clean grid. The sky has stopped filing complaints.",
        "Cheap clean power, as foretold by every learning curve ever drawn.",
    ),
    "quiet": (
        "A quiet round. Enjoy it, the demand curve does not take days off.",
        "Nothing happened. Grid operators call this a good day.",
        "The lights stayed on. It is an underrated achievement.",
    ),
}


def gridley_category():
    if not runstate.state.clean_fraction_log:
        return "welcome"
    event = runstate.state.last_event
    if event is not None:
        return "damage" if event.get("type") == "damage" else "brownout"
    if runstate.state.last_aging_event is not None:
        return "aging"
    recap = runstate.state.last_round_recap
    if recap and recap.get("perfect"):
        return "perfect"
    if runstate.state.total_capacity() < runstate.state.demand:
        return "short"
    if renewable_capacity_share() >= 0.5:
        return "clean"
    return "quiet"


def gridley_line():
    category = gridley_category()
    pool = GRIDLEY_LINES[category]
    return pool[int(runstate.state.stream("gridley", len(runstate.state.clean_fraction_log)).random() * len(pool)) % len(pool)]


def render_gridley():
    document.getElementById("pref-gridley").checked = runstate.prefs["gridley"]
    line = document.getElementById("gridley-line")
    line.hidden = not runstate.prefs["gridley"]
    line.innerText = f"Gridley: {gridley_line()}" if runstate.prefs["gridley"] else ""


# ---- GC-28 supply-against-demand needle gauge -------------------------------------------------------------------
# A half-dial for capacity against demand (0 to 1.5 times demand). The needle swings to its reading with an overshoot
# and settles (a CSS transition on a persistent element, so it animates between rounds); after a brownout round it sits
# in the short zone because delivery was cut; the dial reads "matched" with a tick and a brief glow when capacity covers
# demand without a large surplus. The zones are told apart by line style and word labels, not hue alone. The wobble,
# glow and shake switch off with the Settings checkbox, with reduce motion, and under prefers-reduced-motion.
GAUGE_MAX_RATIO = 1.5
GAUGE_MATCH_LOW = 1.0
GAUGE_MATCH_HIGH = 1.15


def gauge_reading():
    """Ratio of delivered supply to demand, the needle angle in degrees (-90 empty, +90 full) and a zone word."""
    capacity = runstate.state.total_capacity()
    ratio = 0.0 if runstate.state.demand <= 0 else capacity / runstate.state.demand
    event = runstate.state.last_event
    cut = False
    if event and event.get("type") in ("brownout", "damage"):
        ratio *= max(0.0, 1 - float(event.get("severity", 0.0)) * MAX_REVENUE_LOSS_FRACTION)
        cut = True
    shown = max(0.0, min(GAUGE_MAX_RATIO, ratio))
    angle = -90 + 180 * shown / GAUGE_MAX_RATIO
    if ratio < GAUGE_MATCH_LOW:
        zone = "short"
    elif ratio <= GAUGE_MATCH_HIGH:
        zone = "matched"
    else:
        zone = "spare"
    return {"ratio": ratio, "angle": angle, "zone": zone, "cut": cut}


def gauge_text(reading):
    percent = f"{reading['ratio'] * 100:.0f}%"
    capacity = runstate.state.total_capacity()
    base = f"Supply {format_demand(capacity)} against demand {format_demand(runstate.state.demand)}: "
    if reading["zone"] == "matched":
        return base + f"matched ({percent} of demand)."
    if reading["zone"] == "spare":
        return base + f"spare capacity ({percent} of demand)."
    if reading["cut"]:
        return base + f"a disruption cut delivery to {percent} of demand."
    return base + f"short ({percent} of demand), so revenue is capped."


def render_needle_gauge():
    reading = gauge_reading()
    gauge = document.getElementById("needle-gauge")
    document.getElementById("pref-gauge-effects").checked = runstate.prefs["gauge_effects"]
    needle = document.getElementById("needle-gauge-needle")
    needle.style.transform = f"rotate({reading['angle']:.1f}deg)"
    for name in ("short", "matched", "spare"):
        gauge.classList.remove(f"needle-gauge--{name}")
    gauge.classList.add(f"needle-gauge--{reading['zone']}")
    for name, on in (
        ("needle-gauge--still", not runstate.prefs["gauge_effects"]),
        ("needle-gauge--cut", reading["cut"]),
    ):
        if on:
            gauge.classList.add(name)
        else:
            gauge.classList.remove(name)
    text = gauge_text(reading)
    document.getElementById("needle-gauge-caption").innerText = ("\u2713 " if reading["zone"] == "matched" else "") + text
    document.getElementById("needle-gauge-graphic").title = text


# ---- C-17 operator ranks -------------------------------------------------------------------------------------------
# A long-term title earned from lifetime play: experience = rounds played across finished runs + 15 for every grade point
# (A is 4 ... F is 0) those runs earned. Ranks only change a header title and unlock cosmetic accent colours for the
# header and the Career panel. They give no advantage in play: nothing in the rules reads them, and they are
# derived from the career each time, never stored.
RANK_GRADE_WEIGHT = 15
OPERATOR_RANKS = (
    (0, "Junior Dispatcher"),
    (40, "Dispatcher"),
    (120, "Senior Dispatcher"),
    (260, "Shift Supervisor"),
    (450, "Control Room Lead"),
    (700, "Chief Engineer"),
)


def operator_experience():
    life = runstate.career["lifetime"]
    grade_points = sum(entry["points"] for entry in life["scenario_grades"].values())
    return int(life["rounds"] + RANK_GRADE_WEIGHT * grade_points)


def operator_rank_index(experience=None):
    xp = operator_experience() if experience is None else experience
    index = 0
    for i, (threshold, _name) in enumerate(OPERATOR_RANKS):
        if xp >= threshold:
            index = i
    return index


def operator_rank_name(experience=None):
    return OPERATOR_RANKS[operator_rank_index(experience)][1]


def unlocked_rank_themes(experience=None):
    """Themes unlocked so far: the default, then one more per rank above the first."""
    return RANK_THEMES[: operator_rank_index(experience) + 1]


def current_rank_theme():
    theme = runstate.prefs["rank_theme"]
    return theme if theme in unlocked_rank_themes() else "default"


def operator_rank_text():
    xp = operator_experience()
    index = operator_rank_index(xp)
    text = f"Operator rank: {OPERATOR_RANKS[index][1]} (experience {xp})."
    if index + 1 < len(OPERATOR_RANKS):
        threshold, name = OPERATOR_RANKS[index + 1]
        text += f" Next: {name} at {threshold} ({threshold - xp} to go)."
    else:
        text += " That is the highest rank."
    text += (
        " Experience is rounds played in finished runs plus "
        f"{RANK_GRADE_WEIGHT} for every grade point (A is 4). Ranks are for show: they change no rule."
    )
    return text


def render_rank():
    theme = current_rank_theme()
    header = document.getElementById("rank-display")
    header.innerText = f"Rank: {operator_rank_name()}"
    header.dataset.rankTheme = theme
    panel_note = document.getElementById("career-rank-display")
    panel_note.innerText = operator_rank_text()
    document.getElementById("career-panel").dataset.rankTheme = theme
    document.getElementById("rank-theme-select").value = theme
    document.getElementById("rank-theme-note").innerText = runstate.rank_theme_message or (
        f"{len(unlocked_rank_themes())} of {len(RANK_THEMES)} accent colours unlocked."
    )
