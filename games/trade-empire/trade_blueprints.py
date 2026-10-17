"""The Blueprint Lab: hull designs, their stat points and effects, saving and deleting designs, and the panel and ship-option renders."""

from js import document

import trade_runstate as runstate
from trade_research import MAX_SHIP_NAME_LENGTH
from trade_rules import PURCHASABLE_SHIP_IDS


# --- the Market Desk window (J-3, J-11, J-12, J-27, J-28): one panel, a section per feature ------


# ---------------------------------------------------------------------------
# J-19 / J-20 -- the Blueprint Lab (Fleet Lab window), open once Fast Ships I and the Hauler-Class
# Refit are researched. Spend a fixed budget of design points on three stats (hold, speed, efficiency,
# 1-6 each) to design, name and save custom hulls (up to four per charter), then pick one from the
# ship-type picker when buying ship 5 or 6. The "average hull" is 3/3/3 (exactly the Balanced type), so
# every stat is compared with it in a text bar chart with value labels (no colour needed). The effects
# are deliberately small: hold +-6% cargo per point from 3, speed 1-2 one tick slower and 5-6 one tick
# faster, efficiency +-2% on the ship's sales per point from 3; with a budget of 9 no design beats every
# trade-off, and the hull is stored on the ship, so deleting a design never changes a ship.
# ---------------------------------------------------------------------------
BLUEPRINT_POINTS = 9
BLUEPRINT_STAT_MIN = 1
BLUEPRINT_STAT_MAX = 6
BLUEPRINT_AVERAGE = 3
BLUEPRINT_MAX_DESIGNS = 4
BLUEPRINT_CARGO_PER_POINT = 0.06
BLUEPRINT_SALES_PER_POINT = 0.02
BLUEPRINT_STATS = (
    ("hold", "Hold"),
    ("speed", "Speed"),
    ("eff", "Efficiency"),
)
BLUEPRINT_STAT_KEYS = tuple(key for key, _label in BLUEPRINT_STATS)
blueprints = []  # saved designs: {"name", "hold", "speed", "eff"}
blueprint_draft = {"hold": 3, "speed": 3, "eff": 3, "name": ""}


def blueprint_lab_open():
    return "fast_ships" in runstate.unlocked_research and "hauler" in runstate.unlocked_research


def _hull_ok(hull):
    return (
        isinstance(hull, dict)
        and all(
            isinstance(hull.get(k), int) and not isinstance(hull.get(k), bool)
            and BLUEPRINT_STAT_MIN <= hull.get(k) <= BLUEPRINT_STAT_MAX
            for k in BLUEPRINT_STAT_KEYS
        )
        and sum(hull[k] for k in BLUEPRINT_STAT_KEYS) <= BLUEPRINT_POINTS
        and isinstance(hull.get("name"), str) and 0 < len(hull["name"].strip()) <= MAX_SHIP_NAME_LENGTH
    )


def hull_effects(hull):
    """The archetype-shaped effects (label, cargo multiplier, tick delta, sales multiplier) of a custom hull."""
    speed = hull["speed"]
    return {
        "label": hull["name"],
        "cargo": 1.0 + BLUEPRINT_CARGO_PER_POINT * (hull["hold"] - BLUEPRINT_AVERAGE),
        "ticks": 1 if speed <= 2 else (0 if speed <= 4 else -1),
        "proceeds": 1.0 + BLUEPRINT_SALES_PER_POINT * (hull["eff"] - BLUEPRINT_AVERAGE),
    }


def blueprint_points_left(draft=None):
    draft = blueprint_draft if draft is None else draft
    return BLUEPRINT_POINTS - sum(draft[k] for k in BLUEPRINT_STAT_KEYS)


def can_adjust_blueprint(stat, delta):
    if stat not in BLUEPRINT_STAT_KEYS or delta not in (-1, 1):
        return False
    value = blueprint_draft[stat] + delta
    if not BLUEPRINT_STAT_MIN <= value <= BLUEPRINT_STAT_MAX:
        return False
    return delta < 0 or blueprint_points_left() > 0


def adjust_blueprint(stat, delta):
    if not blueprint_lab_open() or not can_adjust_blueprint(stat, delta):
        return False
    blueprint_draft[stat] += delta
    return True


def reset_blueprint_draft():
    blueprint_draft.update({"hold": 3, "speed": 3, "eff": 3, "name": ""})


def can_save_blueprint():
    return blueprint_lab_open() and len(blueprints) < BLUEPRINT_MAX_DESIGNS


def save_blueprint(name=None):
    """Saves the draft as a named design. A blank name becomes 'Design N'. Returns the design or None."""
    if not can_save_blueprint():
        return None
    raw = blueprint_draft["name"] if name is None else name
    clean = " ".join(str(raw).split())[:MAX_SHIP_NAME_LENGTH]
    design = {"name": clean or f"Design {len(blueprints) + 1}"}
    design.update({k: blueprint_draft[k] for k in BLUEPRINT_STAT_KEYS})
    if not _hull_ok(design):
        return None
    blueprints.append(design)
    return design


def delete_blueprint(index):
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(blueprints):
        return False
    del blueprints[index]
    return True


def blueprint_effect_text(hull):
    fx = hull_effects(hull)
    trips = {1: "one tick slower", 0: "same trip time", -1: "one tick faster"}[fx["ticks"]]
    return (
        f"cargo {(fx['cargo'] - 1) * 100:+.0f}%, {trips}, sales {(fx['proceeds'] - 1) * 100:+.0f}% "
        "(compared with the average hull)"
    )


def blueprint_chart_html(hull):
    """J-20: each stat against the average hull, as a labelled bar with a marked average line."""
    rows = []
    for key, label in BLUEPRINT_STATS:
        value = hull[key]
        diff = value - BLUEPRINT_AVERAGE
        word = "same as average" if diff == 0 else f"{diff:+d} vs average"
        fill = value / BLUEPRINT_STAT_MAX * 100
        mark = BLUEPRINT_AVERAGE / BLUEPRINT_STAT_MAX * 100
        rows.append(
            f'<div class="bp-bar" role="img" aria-label="{label} {value} of {BLUEPRINT_STAT_MAX}, {word}">'
            f'<span class="bp-bar-label">{label} {value} ({word})</span>'
            f'<span class="bp-bar-track"><span class="bp-bar-fill" style="width:{fill:.0f}%"></span>'
            f'<span class="bp-bar-avg" style="left:{mark:.0f}%" title="average hull"></span></span></div>'
        )
    return "".join(rows)


def _blueprint_for_choice(choice):
    """The saved design a ship-type picker value like 'bp1' names, or None."""
    if isinstance(choice, str) and choice.startswith("bp") and choice[2:].isdigit():
        index = int(choice[2:])
        if 0 <= index < len(blueprints):
            return blueprints[index]
    return None


def render_blueprints():
    status = document.getElementById("bp-status")
    if status is None:
        return
    open_now = blueprint_lab_open()
    controls = document.getElementById("bp-controls")
    if controls is not None:
        controls.hidden = not open_now
    if not open_now:
        status.innerText = "Locked: research Fast Ships I and the Hauler-Class Refit to open the Blueprint Lab."
        chart = document.getElementById("bp-chart")
        if chart is not None:
            chart.innerHTML = ""
        for i in range(BLUEPRINT_MAX_DESIGNS):
            row = document.getElementById(f"bp-design-{i}-row")
            if row is not None:
                row.hidden = True
        return
    left = blueprint_points_left()
    status.innerText = (
        f"Design points left: {left} of {BLUEPRINT_POINTS}. Each stat runs {BLUEPRINT_STAT_MIN} to {BLUEPRINT_STAT_MAX}; "
        f"the average hull is {BLUEPRINT_AVERAGE}/{BLUEPRINT_AVERAGE}/{BLUEPRINT_AVERAGE}. "
        f"{blueprint_effect_text(blueprint_draft)}. Saved designs: {len(blueprints)}/{BLUEPRINT_MAX_DESIGNS}; "
        "pick one from the ship-type list when you buy ship 5 or 6."
    )
    for key, label in BLUEPRINT_STATS:
        value_el = document.getElementById(f"bp-{key}-value")
        if value_el is not None:
            value_el.innerText = f"{label}: {blueprint_draft[key]}"
        down = document.getElementById(f"bp-{key}-down-button")
        up = document.getElementById(f"bp-{key}-up-button")
        if down is not None:
            down.disabled = not can_adjust_blueprint(key, -1)
        if up is not None:
            up.disabled = not can_adjust_blueprint(key, 1)
    chart = document.getElementById("bp-chart")
    if chart is not None:
        chart.innerHTML = blueprint_chart_html(blueprint_draft)
    save = document.getElementById("bp-save-button")
    if save is not None:
        save.disabled = not can_save_blueprint()
    for i in range(BLUEPRINT_MAX_DESIGNS):
        row = document.getElementById(f"bp-design-{i}-row")
        text = document.getElementById(f"bp-design-{i}-text")
        if row is None or text is None:
            continue
        row.hidden = i >= len(blueprints)
        if i < len(blueprints):
            d = blueprints[i]
            text.innerText = f"{d['name']}: hold {d['hold']}, speed {d['speed']}, efficiency {d['eff']} ({blueprint_effect_text(d)})"


def render_blueprint_options():
    """The saved designs in the ship-5/6 type pickers (kept current even while the Fleet Lab is closed)."""
    for ship_id in PURCHASABLE_SHIP_IDS:
        for i in range(BLUEPRINT_MAX_DESIGNS):
            option = document.getElementById(f"ship-{ship_id}-bp{i}-option")
            if option is None:
                continue
            option.hidden = i >= len(blueprints)
            option.disabled = i >= len(blueprints)
            if i < len(blueprints):
                option.innerText = f"Custom: {blueprints[i]['name']}"
