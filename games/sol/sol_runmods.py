"""Run-wide rule modifiers: prestige mutators and Eras, timed anomalies, and the megaproject yield factors."""

from js import document

import sol_runstate as runstate
from sol_rules import PLANETS, _sandbox_active
from sol_util import _make_button, _make_text, _mmss, _setting_on


# ===========================================================================
# Round-4 batch (2026-10-10). FY-53 goals queue first; the Charter, mutators,
# anomalies, megaprojects, codex, eras and doctrines are appended below it.
# ===========================================================================

# --- A-3 / A-4 / FY-49: prestige mutators -----------------------------------
# Before a New Game+ run the player may pick 0-3 opt-in rule twists. The picks
# (`mutators_next`) are locked in when the next run starts (`mutators_run`), and
# the points are paid when that run is prestiged out of, so a twist can never be
# switched off mid-run to keep the reward. Balance is the owner's "you write it"
# (FY-49): every twist is worth exactly 1 point, none stacks with itself, and
# none can lock a world (the worst case is a slower run; ecology and trade keep
# their usual floors). Nothing here is luck.
MUTATOR_MAX_PICKS = 3
MUTATOR_THIN_DECAY_FACTOR = 1.4  # ecology decays 40% faster
MUTATOR_ONE_WAY_FACTOR = 0.5  # trade routes restore half as much ecology
MUTATOR_BLIND_BUDGET_CAP = 25.0  # the Governor spends at most a quarter of a world's stock
MUTATOR_COSTLY_FACTOR = 1.15  # Auto-Miners and Recyclers cost 15% more
MUTATORS = [
    {"id": "thin_atmosphere", "label": "Thin Atmosphere", "glyph": "\u2601", "points": 1,
     "desc": "Ecology decays 40% faster on every world."},
    {"id": "one_way_trade", "label": "One-Way Trade", "glyph": "\u2192", "points": 1,
     "desc": "Trade routes restore only half as much ecology."},
    {"id": "blind_governor", "label": "Blind Governor", "glyph": "\u25d0", "points": 1,
     "desc": "The Governor ignores your priority and its personalities, alternates its buys and spends "
             "at most a quarter of a world's stock."},
    {"id": "costly_machinery", "label": "Costly Machinery", "glyph": "\u2699", "points": 1,
     "desc": "Auto-Miners and Recyclers cost 15% more."},
]
MUTATOR_BY_ID = {entry["id"]: entry for entry in MUTATORS}
mutators_next = []  # the picks for the run that starts at the next prestige


def mutator_active(mutator_id):
    return mutator_id in runstate.mutators_run


def mutator_points(ids):
    return sum(MUTATOR_BY_ID[m_id]["points"] for m_id in ids if m_id in MUTATOR_BY_ID)


def mutator_glyphs(ids):
    """A tiny glyph per rule, with a leading space, for the badge and the share card ("" when none)."""
    return "".join(" " + MUTATOR_BY_ID[m_id]["glyph"] for m_id in ids if m_id in MUTATOR_BY_ID)


def mutator_rules_text(ids):
    names = [MUTATOR_BY_ID[m_id]["label"] for m_id in ids if m_id in MUTATOR_BY_ID]
    return (". Run rules: " + ", ".join(names)) if names else ""


def _clean_mutators(raw):
    cleaned = []
    if isinstance(raw, list):
        for m_id in raw:
            if isinstance(m_id, str) and m_id in MUTATOR_BY_ID and m_id not in cleaned:
                cleaned.append(m_id)
    return cleaned[:MUTATOR_MAX_PICKS]


def _mutator_confirm_note():
    if not mutators_next:
        return ""
    return (f" and, for the new run, the rule twists you picked ({', '.join(MUTATOR_BY_ID[m]['label'] for m in mutators_next)}), "
            f"which pay {mutator_points(mutators_next)} extra point(s) when you prestige out of that run")


def _toggle_mutator_pick(mutator_id):
    if mutator_id not in MUTATOR_BY_ID:
        return
    if mutator_id in mutators_next:
        mutators_next.remove(mutator_id)
    elif len(mutators_next) < MUTATOR_MAX_PICKS:
        mutators_next.append(mutator_id)


def _build_mutator_cards(panel):
    panel.appendChild(_make_text("stats-panel-heading", "Mutators for your next run (optional)"))
    panel.appendChild(_make_text(
        "prestige-node-desc",
        f"Pick up to {MUTATOR_MAX_PICKS} rule twists. They apply from the moment your next New Game+ starts, "
        "and each pays 1 extra Prestige Point when you prestige out of that run. Nothing is luck, "
        "no world can be locked out, and you can change the picks any time before you prestige.",
    ))
    if runstate.mutators_run:
        panel.appendChild(_make_text(
            "prestige-node-status",
            "This run is being played with: " + ", ".join(MUTATOR_BY_ID[m]["label"] for m in runstate.mutators_run)
            + f" (worth {mutator_points(runstate.mutators_run)} point(s) when you prestige).",
        ))
    for entry in MUTATORS:
        picked = entry["id"] in mutators_next
        card = document.createElement("div")
        card.className = "prestige-node" + (" prestige-node--unlocked" if picked else "")
        card.appendChild(_make_text("prestige-node-name", f"{entry['glyph']} {entry['label']} (+{entry['points']} pt)"))
        card.appendChild(_make_text("prestige-node-desc", entry["desc"]))
        full = not picked and len(mutators_next) >= MUTATOR_MAX_PICKS
        card.appendChild(_make_button(
            "Picked for next run" if picked else ("Limit reached" if full else "Pick for next run"),
            {"data-action": "mutator", "data-mutator": entry["id"]}, None, selected=picked, disabled=full))
        panel.appendChild(card)


# --- A-21: prestige Eras --------------------------------------------------------
# The flat "Prestige N" counter gains a name by level: Pioneer (never prestiged),
# Steward (1-2), Architect (3-5), Custodian (6+). From Steward on, the shell
# shifts hue a little, the dimmer stars get a touch quieter and a one-line
# tagline appears under the title. All of it is static styling (nothing moves, so
# Reduce motion needs no special case) and Settings "Era look" turns the look
# off; the name stays in the badge either way. No rule or number changes.
ERA_LOOK_KEY = "sol-era-look"
ERAS = [
    {"min_level": 0, "id": "pioneer", "label": "Pioneer", "tagline": ""},
    {"min_level": 1, "id": "steward", "label": "Steward",
     "tagline": "Era of the Steward: you came back to tend what you built."},
    {"min_level": 3, "id": "architect", "label": "Architect",
     "tagline": "Era of the Architect: every world is a drawing you can redraw."},
    {"min_level": 6, "id": "custodian", "label": "Custodian",
     "tagline": "Era of the Custodian: nothing to prove, a great deal to keep."},
]


def era_for_level(level):
    chosen = ERAS[0]
    for era in ERAS:
        if level >= era["min_level"]:
            chosen = era
    return chosen


def _apply_era():
    """Sets `data-era` on <html> (read by style.css) and the tagline under the title."""
    era = era_for_level(runstate.prestige_level)
    themed = _setting_on(ERA_LOOK_KEY) and era["tagline"] != ""
    try:
        document.documentElement.setAttribute("data-era", era["id"])
    except AttributeError:
        pass  # the fake DOM of older tests has no <html> element
    tagline = document.getElementById("era-tagline")
    tagline.innerText = era["tagline"] if themed else ""
    tagline.hidden = not themed


# --- A-2 / FY-50: System Anomalies on a fixed schedule ------------------------
# Plain timed modifiers, never random and never blocking: the run clock
# (game ticks since this run began, so a pause or a hidden tab adds nothing)
# starts calm for ANOMALY_FIRST_AT ticks, then one anomaly of ANOMALY_LENGTH ticks
# opens every ANOMALY_PERIOD ticks, walking the same six in the same order
# (boon, strain, boon, strain, boon, strain). The forecast strip says what is
# next and for how long, in words, so nothing is a surprise. Off switch:
# Settings "Timed anomalies" (`localStorage["sol-anomalies"]`); not applied in the
# post-win sandbox.
ANOMALY_FIRST_AT = 3000  # 5 minutes of game time
ANOMALY_PERIOD = 3000  # one every 5 minutes
ANOMALY_LENGTH = 600  # lasting 1 minute
ANOMALY_KEY = "sol-anomalies"
ANOMALIES = [
    {"id": "comet_pass", "label": "Comet Pass", "kind": "boon", "effects": {"produce": 1.25},
     "text": "every Auto-Miner produces 25% more"},
    {"id": "solar_flare", "label": "Solar Flare", "kind": "strain", "effects": {"decay": 1.5},
     "text": "ecology decays 50% faster everywhere"},
    {"id": "meteor_shower", "label": "Meteor Shower", "kind": "boon", "effects": {"click": 2.0},
     "text": "every hand-mined click gives double"},
    {"id": "magnetic_storm", "label": "Magnetic Storm", "kind": "strain", "effects": {"trade": 0.5},
     "text": "trade routes restore half as much ecology"},
    {"id": "clear_skies", "label": "Clear Skies", "kind": "boon", "effects": {"recycle": 1.5},
     "text": "Recyclers restore 50% more ecology"},
    {"id": "dust_cloud", "label": "Dust Cloud", "kind": "strain", "effects": {"terraform": 0.5},
     "text": "terraforming advances at half speed (it never goes backwards)"},
]
ANOMALY_BY_ID = {entry["id"]: entry for entry in ANOMALIES}
anomalies_seen = set()  # lifetime collection; saved only when non-empty
_stress_factors = {}  # A-27: the cascade's multipliers while a headless Stress Test run is going


def _run_ticks():
    return max(0, runstate.total_ticks - runstate.run_start_tick)


def anomaly_schedule(run_ticks):
    """(active_id or None, ticks left in it, next_id, ticks until the next one starts)."""
    if run_ticks < ANOMALY_FIRST_AT:
        return None, 0, ANOMALIES[0]["id"], ANOMALY_FIRST_AT - run_ticks
    index, offset = divmod(run_ticks - ANOMALY_FIRST_AT, ANOMALY_PERIOD)
    if offset < ANOMALY_LENGTH:
        nxt = ANOMALIES[(index + 1) % len(ANOMALIES)]["id"]
        return ANOMALIES[index % len(ANOMALIES)]["id"], ANOMALY_LENGTH - offset, nxt, ANOMALY_PERIOD - offset
    return None, 0, ANOMALIES[(index + 1) % len(ANOMALIES)]["id"], ANOMALY_PERIOD - offset


def _anomalies_enabled():
    return _setting_on(ANOMALY_KEY) and not _sandbox_active()


def _update_anomaly():
    if not _anomalies_enabled():
        runstate._active_anomaly = None
        return
    runstate._active_anomaly = anomaly_schedule(_run_ticks())[0]
    if runstate._active_anomaly is not None:
        anomalies_seen.add(runstate._active_anomaly)


def anomaly_factor(key):
    factor = _stress_factors.get(key, 1.0)  # only ever non-empty inside a headless Stress Test run
    if runstate._active_anomaly is None:
        return factor
    return factor * ANOMALY_BY_ID[runstate._active_anomaly]["effects"].get(key, 1.0)


def anomaly_strip_text():
    """The one-line forecast ("" when anomalies are off)."""
    if not _anomalies_enabled():
        return ""
    active, left, nxt, until = anomaly_schedule(_run_ticks())
    next_entry = ANOMALY_BY_ID[nxt]
    if active is not None:
        entry = ANOMALY_BY_ID[active]
        mark = "\u25b2 Boon" if entry["kind"] == "boon" else "\u25bc Strain"
        return (f"{mark}: {entry['label']} for {_mmss(left)} more, {entry['text']}. "
                f"Next: {next_entry['label']} in {_mmss(until)}.")
    return (f"Next anomaly: {next_entry['label']} in {_mmss(until)} "
            f"({'a boon' if next_entry['kind'] == 'boon' else 'a strain'}: {next_entry['text']}, for {_mmss(ANOMALY_LENGTH)}).")


def update_anomaly_strip():
    strip = document.getElementById("anomaly-strip")
    text = anomaly_strip_text()
    if strip.innerText != text:
        strip.innerText = text
    strip.hidden = not text
    strip.className = "anomaly-strip" + (
        " anomaly-strip--boon" if runstate._active_anomaly and ANOMALY_BY_ID[runstate._active_anomaly]["kind"] == "boon"
        else " anomaly-strip--strain" if runstate._active_anomaly else ""
    )


megaprojects_built = []  # ids built in this run


def megaproject_factor(key):
    factor = 1.0
    if "orbital_mirror" in megaprojects_built and key == "terraform":
        factor *= 1.25
    if "dyson_sail" in megaprojects_built and key == "produce":
        factor *= 1.2
    if "deep_core_tap" in megaprojects_built and key == "recycle":
        factor *= 1.5
    return factor


def sky_city_bonus_per_city(planet):
    base = PLANETS[planet].get("sky_city_production_bonus_per_city", 0)
    return base * (2 if "ring_habitat" in megaprojects_built else 1)
