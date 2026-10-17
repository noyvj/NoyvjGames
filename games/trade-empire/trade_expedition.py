"""The Fleet Lab: expeditions (odds, rolls, curios, outcomes) and the lab panel."""

from js import document

import trade_runstate as runstate
from trade_blueprints import render_blueprints
from trade_colony import galaxy_expansion_unlocked, outer_reaches_unlocked, umbral_reach_unlocked
from trade_crises import render_crises
from trade_hub import render_hub
from trade_records import RECORDS_COUNT_MAX, records
from trade_ships import ships
from trade_uikit import _html_escape, show_notice_toast


# ---------------------------------------------------------------------------
# J-23 / J-24 -- Expeditions: send one idle ship on a long exploratory run (12 ticks) away from
# the routes. The cost is that ship's income while it is away; the reward is a small table of
# outcomes. Nothing essential is ever luck-gated: the odds are shown in words next to the button
# (and in its tooltip), two empty trips in a row guarantee that the next one finds something, and
# every fifth trip without a curio guarantees a curio until all twelve are found. Curios are a
# collection (a sticker-book list that survives renewals) and the trips themselves are counted
# (Expeditions: N), so every send visibly counts. The roll is a hash of the lifetime trip number,
# so it is deterministic and testable.
# ---------------------------------------------------------------------------
EXPEDITION_TICKS = 12
EXPEDITION_WINDFALL = 150
EXPEDITION_WINDFALL_PER_SYSTEM = 0.5  # +50% per cluster beyond home
EXPEDITION_RESEARCH = 12
EXPEDITION_CURIO_GUARANTEE = 5  # every Nth trip without a curio finds one
EXPEDITION_NOTHING_GUARANTEE = 2  # this many empty trips in a row, then the next finds something
EXPEDITION_ODDS = (("windfall", 35), ("research", 25), ("curio", 20), ("nothing", 20))
EXPEDITION_OUTCOME_LABEL = {
    "windfall": "a windfall of credits", "research": "research points", "curio": "a curio for your cabinet",
    "nothing": "nothing but the view",
}
EXPEDITION_CURIOS = (
    ("glass_compass", "Glass compass that points at the nearest bargain"),
    ("tin_cup", "Tin cup from a station that no longer exists"),
    ("quiet_lane_chart", "Hand-drawn chart of a lane nobody uses"),
    ("polite_beacon", "A very polite navigation beacon"),
    ("salt_crystal", "Crystal that tastes faintly of salt"),
    ("spare_moon", "A spare moon, slightly chipped"),
    ("lost_manifest", "Manifest for cargo that never arrived"),
    ("brass_sextant", "Brass sextant, no stars required"),
    ("cold_lantern", "Lantern that gives off cold light"),
    ("sealed_letter", "Sealed letter addressed to the next captain"),
    ("old_ledger", "Ledger page with one very good month"),
    ("patient_clock", "Clock that is never in a hurry"),
)
CURIO_IDS = tuple(curio_id for curio_id, _label in EXPEDITION_CURIOS)
CURIO_LABEL = dict(EXPEDITION_CURIOS)


def _mix(*values):
    x = 2166136261
    for value in values:
        x = ((x ^ (int(value) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
        x ^= x >> 13
        x = (x * 3266489917) & 0xFFFFFFFF
        x ^= x >> 16
    return x


def expedition_ship_ok(ship_id):
    ship = ships.get(ship_id)
    return (
        ship is not None and ship.purchased and ship.docked and not ship.loaded and not ship.automated
        and runstate.expedition is None
    )


def can_send_expedition(ship_id):
    return expedition_ship_ok(ship_id)


def expedition_systems_open():
    return 1 + sum(1 for check in (galaxy_expansion_unlocked, outer_reaches_unlocked, umbral_reach_unlocked) if check())


def expedition_windfall():
    return int(round(EXPEDITION_WINDFALL * (1 + EXPEDITION_WINDFALL_PER_SYSTEM * (expedition_systems_open() - 1))))


def expedition_odds_text():
    parts = ", ".join(f"{weight}% {EXPEDITION_OUTCOME_LABEL[outcome]}" for outcome, weight in EXPEDITION_ODDS)
    return (
        f"Odds: {parts}. Never unlucky twice running: after {EXPEDITION_NOTHING_GUARANTEE} empty trips in a row the "
        f"next one always finds something, and every {EXPEDITION_CURIO_GUARANTEE}th trip without a curio always finds "
        "one until you hold them all. The ship's income is the cost: it cannot trade for "
        f"{EXPEDITION_TICKS} ticks."
    )


def expedition_roll(n, nothing_streak, since_curio, found):
    """The outcome of trip number `n` (0-based) given the guarantees' counters and the curios already found."""
    unfound = [c for c in CURIO_IDS if c not in found]
    if unfound and since_curio >= EXPEDITION_CURIO_GUARANTEE - 1:
        return "curio"
    roll = _mix(n, 7) % 100
    outcome = "nothing"
    total = 0
    for name, weight in EXPEDITION_ODDS:
        total += weight
        if roll < total:
            outcome = name
            break
    if outcome == "curio" and not unfound:
        outcome = "windfall"
    if outcome == "nothing" and nothing_streak >= EXPEDITION_NOTHING_GUARANTEE:
        outcome = "windfall"
    return outcome


def send_expedition(ship_id):
    if not can_send_expedition(ship_id):
        return False
    runstate.expedition = {"ship": ship_id, "left": EXPEDITION_TICKS}
    return True


def _expedition_resolve():
    """The ship is back: pay out the outcome, count the trip, remember what it found."""
    ship = ships[runstate.expedition["ship"]]
    n = records["expeditions"]
    outcome = expedition_roll(n, records["expedition_nothing_streak"], records["expedition_since_curio"], records["curios"])
    if outcome == "windfall":
        gain = expedition_windfall()
        runstate.total_profit += gain
        text = f"{gain} credits from a forgotten cache"
    elif outcome == "research":
        runstate.research_points += EXPEDITION_RESEARCH
        text = f"{EXPEDITION_RESEARCH} research points of survey data"
    elif outcome == "curio":
        unfound = [c for c in CURIO_IDS if c not in records["curios"]]
        found = unfound[_mix(n, 13) % len(unfound)]
        records["curios"].append(found)
        text = f"a curio: {CURIO_LABEL[found]}"
    else:
        text = "nothing but the view (the crew enjoyed it)"
    records["expeditions"] = min(RECORDS_COUNT_MAX, n + 1)
    records["expedition_nothing_streak"] = records["expedition_nothing_streak"] + 1 if outcome == "nothing" else 0
    records["expedition_since_curio"] = 0 if outcome == "curio" else min(RECORDS_COUNT_MAX, records["expedition_since_curio"] + 1)
    runstate.expedition = None
    runstate.expedition_log = f"{ship.name} returned from expedition number {n + 1} with {text}."
    show_notice_toast(f"\U0001F9ED {runstate.expedition_log}")


def expedition_tick():
    if runstate.expedition is None:
        return
    runstate.expedition["left"] -= 1
    if runstate.expedition["left"] <= 0:
        _expedition_resolve()


def expedition_status_text():
    n = records["expeditions"]
    line = f"Expeditions: {n}. Curio cabinet: {len(records['curios'])}/{len(CURIO_IDS)}."
    if runstate.expedition is not None:
        ship = ships[runstate.expedition["ship"]]
        line += f" {ship.name} is away: {runstate.expedition['left']} tick(s) until it returns."
    elif runstate.expedition_log:
        line += " " + runstate.expedition_log
    return line


def expedition_curios_html():
    items = []
    for curio_id, label in EXPEDITION_CURIOS:
        if curio_id in records["curios"]:
            items.append(f'<li class="curio curio--found"><span aria-hidden="true">■</span> {_html_escape(label)}</li>')
        else:
            items.append('<li class="curio"><span aria-hidden="true">□</span> Not found yet</li>')
    return "".join(items)


def render_expedition():
    status = document.getElementById("expedition-status")
    if status is None:
        return
    status.innerText = expedition_status_text()
    odds = document.getElementById("expedition-odds")
    if odds is not None:
        odds.innerText = expedition_odds_text()
    cabinet = document.getElementById("expedition-curios")
    if cabinet is not None:
        cabinet.innerHTML = expedition_curios_html()
    for ship_id, ship in ships.items():
        button = document.getElementById(f"expedition-ship-{ship_id}-button")
        if button is None:
            continue
        ok = can_send_expedition(ship_id)
        button.hidden = not ship.purchased
        button.disabled = not ok
        button.innerText = f"Send {ship.name}"
        button.title = expedition_odds_text()


# --- the Fleet Lab window (J-19..J-24): one panel, sections added by each feature -----------------


def on_toggle_lab(event=None):
    runstate.lab_open = not runstate.lab_open
    render_lab()


def render_lab():
    toggle = document.getElementById("lab-toggle-button")
    panel = document.getElementById("lab-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Fleet Lab" if runstate.lab_open else "\U0001F6E0\ufe0f Fleet Lab"
    toggle.setAttribute("aria-expanded", "true" if runstate.lab_open else "false")
    panel.hidden = not runstate.lab_open
    if not runstate.lab_open:
        return
    render_crises()
    render_hub()
    render_blueprints()
    render_expedition()
