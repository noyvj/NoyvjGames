"""Trade Crises (J-10): the three scripted scenarios, goals, medals, progress text and panel."""

import copy

from js import document

import trade_runstate as runstate
from trade_colony import colony_states
from trade_market import good_profit_total
from trade_records import _fresh_records, records
from trade_rules import ALL_COLONIES
from trade_uikit import show_notice_toast


# ---------------------------------------------------------------------------
# J-9 / J-10 -- Trade Crises (Fleet Lab window): three handcrafted starting boards, each with a clear goal and
# par times for gold, silver and bronze. They run inside the practice sandbox machinery (the real corporation
# is set aside whole and put back unchanged, nothing in a crisis is saved except the best medal, nothing can be
# lost, there is no fail state and no timer: the clock only counts ticks to rank the medal). Restart any time
# (the R key, listed in the ? help, or the Restart button); each card shows the best medal so far as a shape
# plus a word. Medals live in records["crisis_best"], which survives renewals, and write straight into the set-
# aside real game so leaving the crisis keeps them.
# ---------------------------------------------------------------------------
CRISIS_MEDAL_RANK = {"done": 0, "bronze": 1, "silver": 2, "gold": 3}
CRISIS_MEDAL_MARK = {"gold": "★ Gold", "silver": "◆ Silver", "bronze": "▲ Bronze", "done": "● Solved"}
CRISES = {
    "grain_famine": {
        "name": "Grain Famine at Aurum",
        "blurb": "Aurum Station is starving for grain and Verdant Reach's fields are barely producing. Bring Aurum's grain need back above 90%.",
        "credits": 300, "research": (), "need": {"aurum": 0.0, "verdant": 0.0}, "market": {}, "ships": (), "automated": (),
        "goal": {"kind": "need", "colonies": ("aurum",), "value": 0.9}, "par": (40, 65, 100),
    },
    "isotope_glut": {
        "name": "Isotope Glut in Kepler",
        "blurb": "The Kepler Cluster is drowning in isotopes and the price has crashed. Earn 1,500 credits from Kepler goods without waiting for a miracle.",
        "credits": 400, "research": ("galaxy_expansion",), "need": {}, "market": {"isotopes": 0.35}, "ships": (), "automated": (),
        "goal": {"kind": "profit", "goods": ("rare_metals", "biomass", "isotopes"), "value": 1500}, "par": (65, 100, 160),
    },
    "broken_network": {
        "name": "Broken Automation Network",
        "blurb": "Two automated ships are running the wrong shuttles and three colonies are running dry. Get every home colony above 75% at once.",
        "credits": 500, "research": ("automation_slot",), "need": {"ferrum": 0.0, "cryo": 0.0, "helion": 0.05},
        "market": {}, "ships": (), "automated": ("1", "2"),
        "goal": {"kind": "need", "colonies": ("aurum", "verdant", "ferrum", "cryo", "helion"), "value": 0.75}, "par": (80, 120, 180),
    },
}
CRISIS_IDS = tuple(CRISES)


def crisis_goal_met(crisis_id=None):
    goal = CRISES[crisis_id or runstate.crisis_active]["goal"]
    if goal["kind"] == "need":
        return all(colony_states[c].need_satisfaction >= goal["value"] for c in goal["colonies"] if c in colony_states)
    return sum(good_profit_total.get(g, 0) for g in goal["goods"]) >= goal["value"]


def crisis_progress_text(crisis_id=None):
    crisis_id = crisis_id or runstate.crisis_active
    goal = CRISES[crisis_id]["goal"]
    if goal["kind"] == "need":
        parts = [f"{ALL_COLONIES[c]['name']} {colony_states[c].need_satisfaction * 100:.0f}%" for c in goal["colonies"] if c in colony_states]
        return f"Goal: every one of these at {goal['value'] * 100:.0f}% or more: " + ", ".join(parts) + "."
    earned = sum(good_profit_total.get(g, 0) for g in goal["goods"])
    return f"Goal: {goal['value']} credits from Kepler goods ({min(earned, goal['value'])}/{goal['value']} so far)."


def crisis_medal_for(crisis_id, ticks):
    gold, silver, bronze = CRISES[crisis_id]["par"]
    if ticks <= gold:
        return "gold"
    if ticks <= silver:
        return "silver"
    return "bronze" if ticks <= bronze else "done"


def _crisis_state(crisis_id):
    c = CRISES[crisis_id]
    data = copy.deepcopy(runstate._fresh_state)
    data["total_profit"] = data["max_profit_ever"] = c["credits"]
    data["unlocked_research"] = sorted(c["research"])
    for colony_id, need in c["need"].items():
        data["colony_states"][colony_id]["need_satisfaction"] = need
    for good, multiplier in c["market"].items():
        data["market_multiplier"][good] = multiplier
    for ship_id in c["ships"]:
        data["ships"][ship_id]["purchased"] = True
    for ship_id in c["automated"]:
        data["ships"][ship_id]["automated"] = True
    return data


def _crisis_real_best():
    """The best medals of the real game (while a crisis runs, the live records belong to the crisis board)."""
    if runstate._sandbox_real is None:
        return records["crisis_best"]
    return (runstate._sandbox_real["snapshot"].get("records") or {}).get("crisis_best") or {}


def _crisis_clear():
    runstate.crisis_active, runstate.crisis_ticks, runstate.crisis_done = None, 0, None


def crisis_tick():
    """Counts a tick of the crisis and checks its goal; the medal is written into the set-aside real game."""
    if runstate.crisis_active is None or runstate.crisis_done is not None:
        return
    runstate.crisis_ticks += 1
    if not crisis_goal_met():
        return
    medal = crisis_medal_for(runstate.crisis_active, runstate.crisis_ticks)
    runstate.crisis_done = {"medal": medal, "ticks": runstate.crisis_ticks}
    best = _crisis_real_best().get(runstate.crisis_active)
    better = best is None or (CRISIS_MEDAL_RANK[medal], -runstate.crisis_ticks) > (CRISIS_MEDAL_RANK[best["medal"]], -best["ticks"])
    first = not _crisis_real_best()
    if better:
        stored = runstate._sandbox_real["snapshot"].setdefault("records", _fresh_records())
        stored.setdefault("crisis_best", {})[runstate.crisis_active] = {"medal": medal, "ticks": runstate.crisis_ticks}
    extra = " The Crisis Averted achievement is yours once you leave." if first else ""
    show_notice_toast(f"\U0001F3C1 {CRISES[runstate.crisis_active]['name']} solved in {runstate.crisis_ticks} tick(s): {CRISIS_MEDAL_MARK[medal]}.{extra}")


def crisis_best_text(crisis_id):
    best = _crisis_real_best().get(crisis_id) if runstate.sandbox_active else records["crisis_best"].get(crisis_id)
    return "Best: not solved yet" if best is None else f"Best: {CRISIS_MEDAL_MARK[best['medal']]} in {best['ticks']} tick(s)"


def crisis_status_text():
    if runstate.crisis_active is None:
        return "Pick a crisis to play. Your real corporation is set aside and comes back unchanged; nothing in a crisis can be lost."
    c = CRISES[runstate.crisis_active]
    gold, silver, bronze = c["par"]
    line = f"{c['name']}: tick {runstate.crisis_ticks}. {crisis_progress_text()} Par: gold {gold}, silver {silver}, bronze {bronze} tick(s)."
    if runstate.crisis_done is not None:
        line += f" Solved in {runstate.crisis_done['ticks']} tick(s): {CRISIS_MEDAL_MARK[runstate.crisis_done['medal']]}. Restart to beat it, or leave."
    return line


def render_crises():
    status = document.getElementById("crisis-status")
    if status is None:
        return
    status.innerText = crisis_status_text()
    document.getElementById("crisis-restart-button").hidden = runstate.crisis_active is None
    document.getElementById("crisis-leave-button").hidden = runstate.crisis_active is None
    for crisis_id, c in CRISES.items():
        gold, silver, bronze = c["par"]
        document.getElementById(f"crisis-{crisis_id}-text").innerText = (
            f"{c['name']}: {c['blurb']} Par: gold {gold}, silver {silver}, bronze {bronze} tick(s). {crisis_best_text(crisis_id)}."
        )
        document.getElementById(f"crisis-{crisis_id}-start-button").innerText = (
            "Restart" if runstate.crisis_active == crisis_id else "Play"
        )
