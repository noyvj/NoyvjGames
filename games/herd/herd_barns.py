"""Barn skins (GF-17) and the golden cow (GF-21): what is unlocked, what is chosen and what the cards say.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_achievements import ACHIEVEMENTS, achievement_ids_earned


# ---- GF-17 cosmetic barns ----------------------------------------------------------------------
# Earning certain achievements unlocks a barn style (barn, fence and tractor tint together) for the
# pasture picture. Purely cosmetic: nothing here touches a number. Unlocks are kept for good, across
# generations (like breeds), and are recorded silently when a save loads.
DEFAULT_BARN = "red"
BARN_SKINS = [
    {"id": "red", "label": "Red Barn", "glyph": "\U0001F404", "unlock": None},
    {"id": "stone", "label": "Stone Barn", "glyph": "\U0001FAA8", "unlock": "growing_operation"},
    {"id": "green", "label": "Green-Roof Barn", "glyph": "\U0001F33F", "unlock": "sustainably_certified"},
    {"id": "sunflower", "label": "Sunflower Barn", "glyph": "\U0001F33B", "unlock": "plant_pioneer"},
    {"id": "moonlit", "label": "Moonlit Barn", "glyph": "\U0001F319", "unlock": "long_haul"},
    {"id": "gold", "label": "Golden Barn", "glyph": "⭐", "unlock": "decoupling_dividend"},
]
BARN_IDS = [skin["id"] for skin in BARN_SKINS]


def barn_by_id(barn_id):
    for skin in BARN_SKINS:
        if skin["id"] == barn_id:
            return skin
    return None


def barn_is_unlocked(barn_id):
    return barn_id == DEFAULT_BARN or barn_id in runstate.barns_unlocked


def _achievement_label(achievement_id):
    for entry in ACHIEVEMENTS:
        if entry["id"] == achievement_id:
            return entry["label"]
    return achievement_id


def _sync_barns():
    """Unlocks every barn whose achievement is earned right now. Returns labels of new ones."""
    new = []
    earned = None
    for skin in BARN_SKINS:
        if skin["unlock"] is None or skin["id"] in runstate.barns_unlocked:
            continue
        if earned is None:
            earned = set(achievement_ids_earned())
        if skin["unlock"] in earned:
            runstate.barns_unlocked.append(skin["id"])
            new.append(f"new barn {skin['label']}")
    return new


def _load_barns(data):
    runstate.barns_unlocked = [b for b in _valid_barn_ids(data.get("barns_unlocked")) if b != DEFAULT_BARN]
    chosen = data.get("barn_skin")
    runstate.barn_skin = chosen if isinstance(chosen, str) and chosen in BARN_IDS and barn_is_unlocked(chosen) else DEFAULT_BARN


def _valid_barn_ids(raw):
    if not isinstance(raw, list):
        return []
    result = []
    for value in raw:
        if isinstance(value, str) and value in BARN_IDS and value not in result:
            result.append(value)
    return result


def choose_barn(barn_id):
    """Picks an unlocked barn. Returns True when the choice changed."""
    if barn_id not in BARN_IDS or not barn_is_unlocked(barn_id) or barn_id == runstate.barn_skin:
        return False
    runstate.barn_skin = barn_id
    return True


def barn_card_state(skin):
    """(button text, disabled, note) for one barn row."""
    if skin["id"] == runstate.barn_skin:
        return "In use", True, "Your barn right now."
    if barn_is_unlocked(skin["id"]):
        return "Use this barn", False, "Unlocked." if skin["unlock"] else "The one every farm starts with."
    return "Locked", True, f"Earn the achievement {_achievement_label(skin['unlock'])}."


def barn_summary_message():
    return f"Barn styles unlocked: {1 + len(runstate.barns_unlocked)} of {len(BARN_SKINS)}. In use: {barn_by_id(runstate.barn_skin)['label']}."


def render_barns():
    visual = document.getElementById("pasture-visual")
    visual.setAttribute("data-barn", runstate.barn_skin)
    document.getElementById("barn-summary").innerText = barn_summary_message()
    for skin in BARN_SKINS:
        text, disabled, note = barn_card_state(skin)
        button = document.getElementById(f"barn-use-{skin['id']}")
        button.innerText = text
        button.disabled = disabled
        document.getElementById(f"barn-note-{skin['id']}").innerText = note
    document.getElementById("barn-status").innerText = runstate.barn_status_text


# ---- GF-21 golden cow --------------------------------------------------------------------------
# Every GOLDEN_COW_EVERY rounds a golden cow comes to the gate. It waits there until you welcome it
# (a button, always available; there is no timer and no luck), and a visit that was not collected is
# never lost: visits pile up. When motion is allowed a golden cow also glides across the pasture and
# clicking it does the same thing. The welcome pays a small one-off bonus to the real farm only.
GOLDEN_COW_EVERY = 8
GOLDEN_COW_MIN = 15
GOLDEN_COW_INCOME_SHARE = 0.15
GOLDEN_COW_MAX = 60


def golden_cows_due():
    """Visits that have come to the gate and not yet been welcomed."""
    return max(0, (runstate.farm.round_number - 1) // GOLDEN_COW_EVERY - runstate.farm.golden_claimed)


def golden_cow_bonus():
    """Funds for the next welcome: a share of this round's income, never below the minimum or above the cap."""
    share = runstate.farm.income_breakdown()["total"] * GOLDEN_COW_INCOME_SHARE
    return float(max(GOLDEN_COW_MIN, min(GOLDEN_COW_MAX, round(share))))


def welcome_golden_cow():
    """Takes one waiting visit. Returns the funds paid, or None when no cow is waiting."""
    if golden_cows_due() < 1:
        return None
    bonus = golden_cow_bonus()
    runstate.farm.funds += bonus
    if runstate.farm.funds_history:
        runstate.farm.funds_history[-1] = runstate.farm.funds_history[-1] + bonus if runstate.farm.funds_history[-1] is not None else None
    runstate.farm.golden_claimed += 1
    runstate.farm.golden_funds += bonus
    return bonus


def golden_cow_summary_message():
    if runstate.farm.golden_claimed:
        return f"Golden cows welcomed: {runstate.farm.golden_claimed} (+{runstate.farm.golden_funds:g} funds in all)."
    return "A golden cow visits every 8 rounds."


def render_golden_cow():
    due = golden_cows_due()
    panel = document.getElementById("golden-cow-panel")
    panel.hidden = due < 1 and runstate.farm.golden_claimed < 1
    document.getElementById("golden-cow-summary").innerText = golden_cow_summary_message()
    button = document.getElementById("golden-cow-claim-button")
    button.hidden = due < 1
    if due >= 1:
        waiting = f" ({due} waiting)" if due > 1 else ""
        button.innerText = f"\u2728 A golden cow is at the gate: welcome it, +{golden_cow_bonus():g} funds{waiting}"
    glider = document.getElementById("golden-cow-glider")
    glider.hidden = due < 1
    document.getElementById("golden-cow-status").innerText = runstate.golden_cow_status_text
