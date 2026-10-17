"""Screen-reader announcements (B-7), the round recap text and the achievement unlock toast.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import grid_runstate as runstate
from grid_rules import GRANTS, PLANT_LABEL
from grid_achievements import (
    ACHIEVEMENTS, _achievement_powerup_ids, achievement_ids_earned, renewable_capacity_share,
)
from grid_messages import event_message


# ---- B-7 screen-reader announcements ------------------------------------------------------------
# What a sighted player sees change after an action is also said, in plain short sentences, through the shared
# announcer (shared/announcer.js) when the page has it, otherwise through the game's own #sr-announcer region.
# Only player actions and round results announce; render() never does (the shared announcer joins one tick's
# messages, so a build that also unlocks an achievement is read as one announcement).
def _shared_announce(text):
    """Speak through shared/announcer.js when the page has it (returns True); otherwise the game's own live
    region is used. Never both, so a screen reader does not read a message twice."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    shared = getattr(window, "NoyvjAnnounce", None)
    if shared is None:
        return False
    try:
        shared.say(str(text))
    except Exception:  # noqa: BLE001 -- an announcement must never break the game
        return False
    return True


def announce(text):
    """Says text for a screen reader (shared announcer first, the game's own polite region otherwise)."""
    if not text:
        return
    if _shared_announce(text):
        return
    region = document.getElementById("sr-announcer")
    if region is not None:
        region.innerText = text


def _funds_phrase():
    return "Funds unlimited, sandbox" if runstate.sandbox_active else f"Funds {runstate.state.funds:.0f}"


def round_announcement_text(milestone_new=False):
    """What a player sees change after a round resolves, as short sentences built from the game's own readouts:
    the recap line, any disruption or breakdown, the new demand and capacity, the renewable and fossil shares,
    funds, and any policy lever or grant now on offer. Empty before the first round."""
    if runstate.state.last_round_recap is None:
        return ""
    summary, _details = round_recap_text()
    parts = [f"{summary}. Now round {runstate.state.round_number}"]
    if runstate.state.last_event is not None:
        parts.append(event_message(runstate.state.last_event))
    if runstate.state.last_aging_event is not None:
        plant_name = PLANT_LABEL[runstate.state.last_aging_event["plant"]]
        parts.append(
            f"Aging breakdown! A {plant_name} plant failed from wear "
            f"(repair cost {runstate.state.last_aging_event['repair_cost']:.0f})"
        )
    if runstate.state.last_round_recap.get("perfect"):
        parts.append("A Perfect Round: no disruption, no breakdown, demand fully met")
    parts.append(f"Demand is now {runstate.state.demand:g} against capacity {runstate.state.total_capacity():g}")
    parts.append(
        f"Renewables are {renewable_capacity_share() * 100:.0f}% of capacity, "
        f"fossil share {runstate.state.fossil_share() * 100:.0f}%"
    )
    parts.append(_funds_phrase())
    if runstate.state.policy_lever_available:
        parts.append("A policy lever is on offer")
    if runstate.state.grant_offer is not None:
        info = GRANTS[runstate.state.grant_offer["id"]]
        parts.append(f"Offer: {info['title']}. {info['text']}")
    if milestone_new:
        parts.append("More than half your grid's capacity is now renewable")
    return ". ".join(p.rstrip(". ") for p in parts if p) + "."


def _seed_achievement_toast_baseline():
    runstate._achievements_seen_ids = set(achievement_ids_earned())
    _achievement_powerup_ids.clear()  # C-31: a loaded save's achievements are old news, no flash
    _story_reach_all(runstate._achievements_seen_ids)  # W1: a loaded save's earned chapters come back too


def _display_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing."""
    if runstate.sandbox_active:  # Z-18: chapters belong to the real game
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    story = getattr(window, "NoyvjStory", None)
    if story is None:
        return
    story.reach("begin")
    for achievement_id in sorted(earned_ids):
        story.reach(achievement_id)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (build/retire/maintain/advance round) — never from render() itself,
    since load_state() also calls render() and a loaded save with several
    achievements already earned must not flood the player with toasts for
    all of them at once (see _seed_achievement_toast_baseline)."""
    if runstate.sandbox_active:  # Z-18: no toasts, no new chapters
        return
    earned_now = set(achievement_ids_earned())
    _story_reach_all(earned_now)
    newly = earned_now - runstate._achievements_seen_ids
    if newly:
        _achievement_powerup_ids.update(newly)
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
                announce(f"Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
                announce(f"{len(labels)} achievements unlocked: " + ", ".join(labels))
    runstate._achievements_seen_ids = earned_now


# C-8 -- round recap: one expandable entry collating where last round's
# funds went and came from (revenue, arbitrage, regional grid, scheduled
# maintenance, weather, disruption, aging, demand growth).
def round_recap_text():
    """Returns (summary, details) for the last round played."""
    r = runstate.state.last_round_recap
    if r is None:
        return "Round recap: no round played yet.", "Advance a round and its funds story appears here."
    lines = [f"Revenue earned: +{r['base_revenue']:.0f}"]
    if r.get("perfect_bonus", 0) > 0:
        lines.append(f"Perfect Round bonus: +{r['perfect_bonus']:.0f}")
    if r.get("immunity"):
        lines.append("Diplomatic Immunity: a disruption was called off")
    if r["arbitrage"] > 0:
        lines.append(f"Storage arbitrage sales: +{r['arbitrage']:.0f}")
    if runstate.state.regional_grid_connected:
        lines.append(f"Regional grid: +{r['regional']:.0f} earned, -{r['regional_shortfall']:.0f} bought in")
    if r["scheduled"]:
        spent = ", ".join(f"{PLANT_LABEL[a['plant']]} (-{a['cost']:.0f})" for a in r["scheduled"])
        lines.append(f"Scheduled maintenance: {spent}")
    if r["weather_pct"] is not None:
        direction = "above" if r["weather_pct"] >= 0 else "below"
        lines.append(f"Weather: renewable output {abs(r['weather_pct']):.0f}% {direction} nameplate")
    if r["disruption_loss"] > 0:
        lines.append(f"Disruption: -{r['disruption_loss']:.0f} revenue lost")
    elif r["disruption_type"] is not None:
        lines.append("Disruption: no revenue lost")
    if r["aging_plant"] in PLANT_LABEL:
        lines.append(f"Aging breakdown: {PLANT_LABEL[r['aging_plant']]} unit lost, repair -{r['repair_cost']:.0f}")
    growth_note = f"Demand grew by {r['demand_growth']:g}"
    if runstate.state.demand_response_level > 0:
        growth_note += f" (demand response level {runstate.state.demand_response_level})"
    lines.append(growth_note)
    if r.get("perfect"):
        lines.append("This was a Perfect Round: no disruption, no breakdown, demand fully met")
    sign = "+" if r["net"] >= 0 else "-"
    return f"Round {r['round']} recap: net {sign}{abs(r['net']):.0f} funds", "\n".join(lines)
