"""The Observatory: survey chart, rival colonies, rumours, rogue comets, and its panel."""

from js import document

import sol_runstate as runstate
from sol_econ import _yield_multiplier, production_multiplier
from sol_rules import (
    PLANETS, PLANET_DISPLAY_NAMES, RUMORS, RUMOR_BY_ID, TERRAFORM_MAX, _sandbox_active, _specialization,
    planet_state,
)
from sol_story import render_story_log, story_line, story_log, story_note
from sol_util import _clean_ids, _display_toast, _make_button, _make_text, _overview_planets, _setting_on


# =============================================================================
# Round-5 batch (2026-10-11): A-9 / A-10 Observatory and comets, A-15 / A-16
# rival colonies, A-17 / A-18 Time Capsules. Every save key is optional,
# written only when non-default and cleaned on load.
# =============================================================================

# --- A-9 / A-10: the Observatory -------------------------------------------------
# Survey Data (earned by prestiging, finishing Charter missions and finding Codex
# clues) is spent to uncover the next hidden region of a star chart. The order of
# the chart is fixed, so nothing is random and the whole map is easy to finish:
# Lagrange Points are relays you can claim for a small permanent yield bonus, and
# rogue comets bring a windfall once per run, caught from a strip at the top.
SURVEY_PER_PRESTIGE = 2
SURVEY_PER_STAMP = 1
SURVEY_PER_CLUE = 1
RELAY_BONUS_YOURS = 0.01  # +1% yield everywhere per relay you hold
CLAIM_COST = 200  # of whichever resource pile is biggest right now
COMET_BRIGHT_TICKS = 900  # 90 s of game time bright, then fading, then faint (never gone)
COMET_FADING_TICKS = 1800
COMET_FLOOR = 150  # a windfall is at least this times the comet's rank ...
COMET_SECONDS_OF_OUTPUT = 60  # ... or a minute of that world's output, whichever is more
CHART = [
    {"id": "wanderer", "kind": "comet", "name": "Wanderer", "cost": 1, "rank": 1},
    {"id": "harbour_light", "kind": "point", "name": "Harbour Light", "cost": 1},
    {"id": "ember", "kind": "comet", "name": "Ember", "cost": 2, "rank": 2},
    {"id": "cairn", "kind": "point", "name": "Cairn", "cost": 2, "rival": "helios"},
    {"id": "long_tail", "kind": "comet", "name": "Long Tail", "cost": 3, "rank": 3},
    {"id": "meridian", "kind": "point", "name": "Meridian", "cost": 3, "rival": "ceres"},
    {"id": "quiet_one", "kind": "comet", "name": "The Quiet One", "cost": 4, "rank": 4},
    {"id": "far_anchor", "kind": "point", "name": "Far Anchor", "cost": 4, "rival": "outer"},
]
CHART_BY_ID = {entry["id"]: entry for entry in CHART}
COMETS_TO_CATCH = 4  # Comet Catcher: four catches over a lifetime
# --- A-15 / A-16: rival colonies -----------------------------------------------------
# Three named, non-hostile corporations already hold three of the four Lagrange Points the
# moment you uncover them. A point a rival holds adds RIVAL_PRESSURE_PER_POINT to a "market
# pressure" on trade (every trade route restores that much less ecology), but only on worlds
# with no Focus (Output or Stability, set from the Overview once a world is 75% terraformed),
# and never more than three points' worth. Nothing is timed and everything is recoverable:
# ignore them, pay to share a point (removes its pressure, half the relay bonus) or pay to
# take it over (full relay bonus). Off in Settings ("Rival colonies").
RIVALS_KEY = "sol-rivals"
RIVAL_PRESSURE_PER_POINT = 0.08
PARTNER_COST = 300
CONTEST_COST = 800
TAKEOVER_COST = 500  # buying out a partner you already share a point with
RELAY_BONUS_PARTNER = 0.005
RIVALS = [
    {"id": "helios", "name": "Helios Combine", "blurb": "inner-system haulers, fond of Mars and the Moon"},
    {"id": "ceres", "name": "Ceres Freight Guild", "blurb": "Belt miners who say everything is on schedule"},
    {"id": "outer", "name": "Outer Reach Syndicate", "blurb": "gas-giant cities with a long view"},
]
RIVAL_BY_ID = {entry["id"]: entry for entry in RIVALS}

point_claims = {}  # Lagrange Point id -> "yours" (anything not listed is open), lifetime
comets_caught_run = []  # comet ids caught in this run (a prestige clears it so each run has its windfalls)

_observatory_refs = {}


def _award_survey(amount):
    runstate.survey_data = min(runstate.survey_data + amount, 10 ** 6)


def chart_next():
    """The next region to uncover, or None when the whole chart is open."""
    return CHART[runstate.chart_revealed] if runstate.chart_revealed < len(CHART) else None


def survey_region():
    """Spends Survey Data to uncover the next region. Returns the entry, or None when it cannot."""
    entry = chart_next()
    if entry is None or runstate.survey_data < entry["cost"]:
        return None
    runstate.survey_data -= entry["cost"]
    runstate.chart_revealed += 1
    what = "a Lagrange Point" if entry["kind"] == "point" else f"Comet {entry['name']}"
    _display_toast(f"Survey complete: {what} found ({entry['name']})")
    _on_region_revealed(entry)
    return entry


def _on_region_revealed(entry):
    if entry.get("rival"):
        _note_rumor("met:" + entry["rival"])


def point_state(point_id):
    """"open", "rival", "partner" or "yours" for an uncovered Lagrange Point, None while it is still hidden."""
    entry = CHART_BY_ID.get(point_id)
    if entry is None or entry["kind"] != "point" or CHART.index(entry) >= runstate.chart_revealed:
        return None
    return point_claims.get(point_id, "rival" if entry.get("rival") else "open")


def revealed_points():
    return [entry for entry in CHART[:runstate.chart_revealed] if entry["kind"] == "point"]


def relay_bonus():
    """The small yield bonus every claimed relay adds, everywhere (half for a shared point)."""
    states = [point_state(entry["id"]) for entry in revealed_points()]
    return RELAY_BONUS_YOURS * states.count("yours") + RELAY_BONUS_PARTNER * states.count("partner")


def _pile_source(cost):
    """(planet, amount) a payment of `cost` would come out of (the biggest pile), or None when none has enough."""
    best = max(_overview_planets(), key=lambda p: planet_state[p]["resource_count"])
    if planet_state[best]["resource_count"] >= cost:
        return best, cost
    return None


def _pile_text(cost):
    source = _pile_source(cost)
    return f"{cost} {PLANETS[source[0]]['resource_name']}" if source else f"{cost} of any resource"


def _pay(cost):
    source = _pile_source(cost)
    if source is None:
        return False
    planet_state[source[0]]["resource_count"] -= source[1]
    return True


def claim_point(point_id):
    """Claims an open Lagrange Point for the price of a pile. Returns True when it happened."""
    if point_state(point_id) != "open" or not _pay(CLAIM_COST):
        return False
    point_claims[point_id] = "yours"
    _on_point_changed(point_id, "yours")
    return True


def partner_point(point_id):
    """A-15: shares a rival's point (its pressure goes, half the relay bonus is yours). Returns True when it happened."""
    if point_state(point_id) != "rival" or not _pay(PARTNER_COST):
        return False
    point_claims[point_id] = "partner"
    _on_point_changed(point_id, "partner")
    return True


def contest_point(point_id):
    """A-15: takes a point over from a rival (or from a partner, for less). Returns True when it happened."""
    state = point_state(point_id)
    if state not in ("rival", "partner") or not _pay(CONTEST_COST if state == "rival" else TAKEOVER_COST):
        return False
    point_claims[point_id] = "yours"
    _on_point_changed(point_id, "yours")
    return True


def contest_cost(point_id):
    return TAKEOVER_COST if point_state(point_id) == "partner" else CONTEST_COST


def _rivals_on():
    return _setting_on(RIVALS_KEY) and not _sandbox_active()


def rival_points_held():
    """How many uncovered Lagrange Points a rival still holds."""
    return sum(1 for entry in revealed_points() if point_state(entry["id"]) == "rival")


def rival_pressure(planet=None):
    """The fraction trade routes restore less ecology while rivals hold points (0 when off, or on a world with a Focus)."""
    held = rival_points_held()
    if not held or not _rivals_on() or (planet is not None and _specialization(planet)):
        return 0.0
    return min(3, held) * RIVAL_PRESSURE_PER_POINT


def _note_rumor(rumor_id):
    """Adds a gossip line to the captain's log once (never when rivals are switched off). Returns True when added."""
    if not _rivals_on() or rumor_id not in RUMOR_BY_ID:
        return False
    if story_note("rumor:" + rumor_id):
        render_story_log()
        return True
    return False


def _note_world_rumors():
    """The 'a world finished' gossip, for rivals you have met. Returns True when a line was added."""
    changed = False
    for entry in RUMORS:
        planet = entry["id"][len("world:"):] if entry["id"].startswith("world:") else None
        if planet is None or planet not in planet_state or planet_state[planet]["terraform_progress"] < TERRAFORM_MAX:
            continue
        met = any(e.get("rival") == entry["rival"] for e in CHART[:runstate.chart_revealed])
        if met and _rivals_on():
            changed = story_note("rumor:" + entry["id"]) or changed
    return changed


def latest_rumor():
    for entry_id in reversed(story_log):
        if entry_id.startswith("rumor:"):
            return story_line(entry_id)
    return None


def _on_point_changed(point_id, new_state):
    rival = CHART_BY_ID[point_id].get("rival")
    if rival and new_state in ("yours", "partner"):
        _note_rumor(("contest:" if new_state == "yours" else "partner:") + rival)


# --- A-10: rogue comets ----------------------------------------------------------
def comet_ready():
    """The first uncovered comet not yet caught this run, or None."""
    for entry in CHART[:runstate.chart_revealed]:
        if entry["kind"] == "comet" and entry["id"] not in comets_caught_run:
            return entry
    return None


def comet_phase():
    """"bright", "fading" or "faint" while a comet is overhead, else None. It never goes away: waiting costs nothing."""
    if comet_ready() is None or runstate._comet_since is None:
        return None
    age = runstate.total_ticks - runstate._comet_since
    return "bright" if age < COMET_BRIGHT_TICKS else "fading" if age < COMET_FADING_TICKS else "faint"


def _update_comet():
    if comet_ready() is None:
        runstate._comet_since = None
    elif runstate._comet_since is None:
        runstate._comet_since = runstate.total_ticks


def _output_per_second(planet):
    state = planet_state[planet]
    return state["generator_count"] * PLANETS[planet]["generator_rate"] * production_multiplier(planet) * _yield_multiplier()


def comet_windfall(entry):
    """planet -> amount for every world you have, for the given comet."""
    return {
        planet: max(COMET_FLOOR * entry["rank"], round(COMET_SECONDS_OF_OUTPUT * _output_per_second(planet)))
        for planet in _overview_planets()
    }


def catch_comet():
    """Catches the comet overhead: a windfall on every world you have. Returns the amounts, or None."""
    entry = comet_ready()
    if entry is None:
        return None
    amounts = comet_windfall(entry)
    for planet, amount in amounts.items():
        planet_state[planet]["resource_count"] += amount
    comets_caught_run.append(entry["id"])
    runstate.comets_caught_total = min(runstate.comets_caught_total + 1, 10 ** 6)
    runstate._comet_since = None
    _display_toast(f"Comet {entry['name']} caught: a windfall on every world you have")
    return amounts


COMET_STRIP_TEXT = {
    "bright": "Comet {name} is overhead. Catch it for a windfall on every world you have.",
    "fading": "Comet {name} is fading. Catch it now, or later: it will still be here.",
    "faint": "Comet {name} is faint but still here. Catch it whenever you like; nothing is lost by waiting.",
}


def update_comet_strip():
    strip = document.getElementById("comet-strip")
    phase = comet_phase()
    entry = comet_ready()
    if phase is None or entry is None:
        strip.hidden = True
        return
    text = "☄ " + COMET_STRIP_TEXT[phase].format(name=entry["name"])
    if strip.innerText != text:
        strip.innerText = text
    strip.hidden = False
    strip.className = f"comet-strip comet-strip--{phase}"


# --- the Observatory panel ---------------------------------------------------------


def _observatory_structure_signature():
    return (runstate.survey_data, runstate.chart_revealed, tuple(sorted(point_claims.items())), tuple(comets_caught_run),
            _rivals_on(), _specialised_worlds(), latest_rumor())


def _specialised_worlds():
    return tuple(p for p in _overview_planets() if _specialization(p))


def _chart_card(entry, index):
    card = document.createElement("div")
    if index >= runstate.chart_revealed:
        card.className = "chain-card"
        card.appendChild(_make_text("chain-card-name", f"Unmapped region {index + 1}"))
        card.appendChild(_make_text("chain-card-detail", "Something is out there. Survey it to find out what."))
        return card
    if entry["kind"] == "comet":
        caught = entry["id"] in comets_caught_run
        card.className = "chain-card chain-card--found" if caught else "chain-card"
        card.appendChild(_make_text("chain-card-name", f"☄ Comet {entry['name']}"))
        ready = comet_ready()
        card.appendChild(_make_text(
            "chain-card-detail",
            "Caught this run. It comes back round after your next prestige." if caught
            else "Overhead now: catch it from the strip at the top of the page for a windfall on every world you have."
            if ready is not None and ready["id"] == entry["id"]
            else "Next in line: it appears once the comet before it has been caught."))
        return card
    state = point_state(entry["id"])
    card.className = "chain-card chain-card--found" if state == "yours" else "chain-card"
    card.appendChild(_make_text("chain-card-name", f"◎ Lagrange Point {entry['name']}"))
    _fill_point_card(card, entry, state)
    return card


def _fill_point_card(card, entry, state):
    rival = RIVAL_BY_ID.get(entry.get("rival"))
    if state == "yours":
        card.appendChild(_make_text(
            "chain-card-detail", f"Your relay. +{round(RELAY_BONUS_YOURS * 100)}% yield on every world, for good."))
        return
    if state == "partner":
        card.appendChild(_make_text(
            "chain-card-detail",
            f"Shared with {rival['name']}. +{round(RELAY_BONUS_PARTNER * 100, 1):g}% yield on every world and no market pressure from this point."))
        _add_point_button(card, entry, "contest", "Take it over")
        return
    if state == "rival":
        card.appendChild(_make_text(
            "chain-card-detail",
            f"Held by {rival['name']} ({rival['blurb']}). While they hold it, trade routes restore "
            f"{round(RIVAL_PRESSURE_PER_POINT * 100)}% less ecology on worlds with no Focus. You can ignore them, share the point or take it over."))
        _add_point_button(card, entry, "partner", "Share it")
        _add_point_button(card, entry, "contest", "Take it over")
        return
    card.appendChild(_make_text("chain-card-detail", "Nobody holds this point. A relay here adds a small yield bonus to every world."))
    _add_point_button(card, entry, "claim", "Claim")


def _add_point_button(card, entry, action, label):
    button = _make_button(label, {"data-action": action, "data-point": entry["id"]}, None)
    card.appendChild(button)
    _observatory_refs[(action, entry["id"])] = (button, label)


def _build_observatory():
    panel = document.getElementById("observatory-panel")
    panel.innerHTML = ""
    _observatory_refs.clear()
    panel.appendChild(_make_text("stats-panel-heading", "Observatory"))
    panel.appendChild(_make_text(
        "chains-intro",
        "Survey Data comes from prestiging (2), finishing Charter missions (1 each) and finding Codex clues (1 each). "
        "Spend it to uncover the next region of the star chart. Nothing here is timed or random, and nothing is lost by waiting."))
    _observatory_refs["_survey"] = _make_text("chain-card-count", "")
    panel.appendChild(_observatory_refs["_survey"])
    button = _make_button("Survey the next region", {"data-action": "survey"}, None)
    _observatory_refs["_survey_button"] = button
    panel.appendChild(button)
    panel.appendChild(_make_text("stats-panel-heading", "Star chart"))
    for index, entry in enumerate(CHART):
        panel.appendChild(_chart_card(entry, index))
    _observatory_refs["_relays"] = _make_text("chain-card-count", "")
    panel.appendChild(_observatory_refs["_relays"])
    _build_observatory_extras(panel)


def _sentence(text):
    return text[:1].upper() + text[1:]


def _build_observatory_extras(panel):
    panel.appendChild(_make_text("stats-panel-heading", "Rival colonies"))
    if not _rivals_on():
        panel.appendChild(_make_text(
            "chain-card-detail", "Rival colonies are switched off in Settings: no market pressure and no ticker."))
        return
    for rival in RIVALS:
        holds = [e["name"] for e in revealed_points() if e.get("rival") == rival["id"] and point_state(e["id"]) == "rival"]
        shares = [e["name"] for e in revealed_points() if e.get("rival") == rival["id"] and point_state(e["id"]) == "partner"]
        met = any(e.get("rival") == rival["id"] for e in CHART[:runstate.chart_revealed])
        if not met:
            line = "Not met yet. Something out there has a flag."
        elif holds:
            line = f"{_sentence(rival['blurb'])}. Holds {', '.join(holds)}."
        elif shares:
            line = f"{_sentence(rival['blurb'])}. Shares {', '.join(shares)} with you."
        else:
            line = f"{_sentence(rival['blurb'])}. Holds nothing now."
        card = document.createElement("div")
        card.className = "chain-card"
        card.appendChild(_make_text("chain-card-name", rival["name"] if met else "A rival"))
        card.appendChild(_make_text("chain-card-detail", line))
        panel.appendChild(card)
    _observatory_refs["_pressure"] = _make_text("chain-card-count", "")
    panel.appendChild(_observatory_refs["_pressure"])
    tip = latest_rumor()
    panel.appendChild(_make_text("chain-card-detail", tip if tip else "Ticker: quiet for now."))


def _refresh_observatory_values():
    nxt = chart_next()
    _observatory_refs["_survey"].innerText = (
        f"Survey Data: {runstate.survey_data}. " + (f"The next survey costs {nxt['cost']}." if nxt else "The whole chart is uncovered."))
    survey_button = _observatory_refs["_survey_button"]
    survey_button.disabled = nxt is None or runstate.survey_data < nxt["cost"]
    survey_button.innerText = (
        "Survey the next region" + (f" (costs {nxt['cost']} Survey Data)" if nxt else " (all done)"))
    costs = {"claim": lambda pid: CLAIM_COST, "partner": lambda pid: PARTNER_COST, "contest": contest_cost}
    for key, value in _observatory_refs.items():
        if isinstance(key, tuple):
            button, label = value
            cost = costs[key[0]](key[1])
            button.disabled = _pile_source(cost) is None
            button.innerText = f"{label} ({_pile_text(cost)})"
    held = sum(1 for entry in revealed_points() if point_state(entry["id"]) in ("yours", "partner"))
    _observatory_refs["_relays"].innerText = (
        f"Relays held: {held} of {sum(1 for e in CHART if e['kind'] == 'point')} "
        f"(+{round(relay_bonus() * 100, 1):g}% yield everywhere). Comets caught for life: {runstate.comets_caught_total}.")
    pressure = _observatory_refs.get("_pressure")
    if pressure is not None:
        n = rival_points_held()
        pressure.innerText = (
            "No rival holds a point: trade is at full strength everywhere." if not n
            else f"Rival pressure: trade routes restore {round(rival_pressure() * 100)}% less ecology on worlds with no Focus"
                 + (f" (worlds with a Focus are unaffected: {', '.join(PLANET_DISPLAY_NAMES.get(p, p) for p in _specialised_worlds())})."
                    if _specialised_worlds() else ". A Focus on a world (Overview, from 75% terraformed) shields it."))


def update_observatory_display():
    toggle = document.getElementById("observatory-toggle-button")
    panel = document.getElementById("observatory-panel")
    toggle.innerText = ("Hide Observatory" if runstate.observatory_open else "\U0001f52d Observatory") + f" ({runstate.chart_revealed}/{len(CHART)})"
    panel.hidden = not runstate.observatory_open
    if not runstate.observatory_open:
        runstate._observatory_signature = None
        return
    signature = _observatory_structure_signature()
    if signature != runstate._observatory_signature:
        _build_observatory()
        runstate._observatory_signature = signature
    _refresh_observatory_values()


def _load_observatory(data):

    def _count(value, top):
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= top else 0

    runstate.survey_data = _count(data.get("survey_data"), 10 ** 6)
    runstate.chart_revealed = _count(data.get("chart_revealed"), len(CHART))
    runstate.comets_caught_total = _count(data.get("comets_caught_total"), 10 ** 6)
    point_claims.clear()
    raw = data.get("point_claims")
    if isinstance(raw, dict):
        for point_id, state in raw.items():
            if point_state(point_id) is None:
                continue
            if state == "yours" or (state == "partner" and CHART_BY_ID[point_id].get("rival")):
                point_claims[point_id] = state
    comets_caught_run[:] = [
        c_id for c_id in _clean_ids(data.get("comets_caught_run"), CHART_BY_ID)
        if CHART_BY_ID[c_id]["kind"] == "comet" and CHART.index(CHART_BY_ID[c_id]) < runstate.chart_revealed
    ]
