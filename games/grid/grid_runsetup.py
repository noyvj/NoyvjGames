"""Run setup: starting loadout, run seed, Ironman, undo, grants, peek and the setup panel render.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import CAREER_UNLOCKS, GRANTS, LOADOUT_NODES, PEEK_FEE, PLANT_LABEL, PLANT_TYPES


# --- run setup: starting loadout, run seed, Ironman -------------------------------------------------------
START_OPTION_NONE = "none"


def peek_text():
    """The peek forecast spelled out in words (and numbers), or the reason it is not showing."""
    if not runstate.state.peek_unlocked():
        return "Peek forecast: buy Weather station in the Career upgrade tree (Meteorology) to read next round's rolls."
    if not runstate.state.peek_active():
        return f"Peek forecast: pay {PEEK_FEE} funds to read next round's weather roll and whether a disruption hits."
    f = runstate.state.peek_forecast()
    outcome = {
        "hit": f"A disruption WILL hit next round (the chance was {f['probability'] * 100:.0f}%).",
        "waived": "A disruption would hit next round, but Diplomatic Immunity calls it off.",
        "none": f"No disruption next round (the chance was {f['probability'] * 100:.0f}%).",
    }[f["disruption"]]
    if f["weather"] is None:
        weather = "Weather variability is off, so renewable output stays at nameplate."
    else:
        weather = "Next round's renewable output: " + ", ".join(
            f"{PLANT_LABEL[t]} {(v - 1) * 100:+.0f}%" for t, v in f["weather"].items()
        ) + "."
    text = f"Peek forecast: {outcome} {weather}"
    if f["weather_next"] is not None:
        text += " The round after: " + ", ".join(
            f"{PLANT_LABEL[t]} {(v - 1) * 100:+.0f}%" for t, v in f["weather_next"].items()
        ) + "."
    return text


def render_run_setup_and_extras():
    """Everything the 2026-10-08 batch added to the main screen: run setup (loadout, seed, Ironman),
    the undo button, the Perfect Round streak, the grant offer, the peek forecast, plant nicknames."""
    owned_loadouts = list(LOADOUT_NODES) if runstate.sandbox_active else [n for n in LOADOUT_NODES if n in runstate.career["unlocked"]]
    select = document.getElementById("start-option-select")
    select.value = runstate.state.start_option if runstate.state.start_option in owned_loadouts else START_OPTION_NONE
    select.disabled = not runstate.state.unstarted() or not owned_loadouts
    options = getattr(select, "options", None)  # the fake DOM has none; the browser marks unowned loadouts unavailable
    if options is not None:
        for index in range(int(options.length)):
            option = options.item(index)
            option.disabled = option.value != START_OPTION_NONE and option.value not in owned_loadouts
    select.title = (
        "Buy a loadout in the Career upgrade tree (Starting loadout branch) to choose one here."
        if not owned_loadouts else "Choose one starting loadout per run, before you build or advance a round."
    )
    note = document.getElementById("start-option-note")
    if runstate.state.start_option in owned_loadouts:
        note.innerText = f"Loadout: {CAREER_UNLOCKS[runstate.state.start_option]['label']} -- {CAREER_UNLOCKS[runstate.state.start_option]['effect']}."
    elif owned_loadouts:
        note.innerText = "Loadout: none chosen."
    else:
        note.innerText = "No loadout bought yet (Career upgrade tree, Starting loadout)."
    document.getElementById("run-seed-display").innerText = f"Run seed: {runstate.state.seed}"
    document.getElementById("run-seed-apply-button").disabled = not runstate.state.unstarted()
    document.getElementById("run-seed-input").disabled = not runstate.state.unstarted()
    document.getElementById("run-seed-note").innerText = runstate.run_setup_message
    iron = document.getElementById("ironman-toggle-button")
    iron.innerText = "Ironman: ON (no undo)" if runstate.state.ironman else "Ironman: OFF"
    iron.disabled = not runstate.state.unstarted() and not runstate.state.ironman
    iron.title = "Opt-in challenge: every action is final and Undo last build is off. Fixed once the run starts."
    undo = document.getElementById("undo-build-button")
    undo.disabled = not runstate.state.can_undo_build()
    if runstate.state.ironman:
        undo.innerText = "Undo last build (off in Ironman)"
    elif runstate.state.can_undo_build():
        record = runstate.state.undo_record
        undo.innerText = f"Undo last build ({PLANT_LABEL[record['plant']]}, refunds {record['cost']:.0f})"
    else:
        undo.innerText = "Undo last build"
    bonus = runstate.state.perfect_bonus_fraction()
    document.getElementById("perfect-streak-display").innerText = (
        f"\U0001F525 Perfect Round streak: {runstate.state.perfect_streak} (revenue bonus +{bonus * 100:.0f}%, best {runstate.state.best_perfect_streak})"
        if runstate.state.perfect_streak > 0
        else f"Perfect Round streak: 0 (best {runstate.state.best_perfect_streak}). Rounds with no disruption and demand fully met build a revenue bonus."
    )
    offer = runstate.state.grant_offer
    banner = document.getElementById("grant-banner")
    banner.hidden = offer is None
    if offer is not None:
        info = GRANTS[offer["id"]]
        document.getElementById("grant-text").innerText = f"{info['title']}: {info['text']}"
        document.getElementById("grant-accept-button").innerText = info["accept"]
        document.getElementById("grant-decline-button").innerText = info["decline"]
    message = document.getElementById("grant-message-display")
    message.innerText = runstate.state.last_grant_message
    message.hidden = not runstate.state.last_grant_message
    peek = document.getElementById("peek-forecast-button")
    peek.hidden = not runstate.state.peek_unlocked()
    peek.innerText = f"Peek forecast ({PEEK_FEE} funds)"
    peek.disabled = runstate.state.peeked_round == runstate.state.round_number or runstate.state.funds < PEEK_FEE
    document.getElementById("peek-forecast-display").innerText = peek_text()
    for plant_type in PLANT_TYPES:
        names = runstate.state.plant_name_list(plant_type)
        document.getElementById(f"{plant_type}-names").innerText = ", ".join(names)
    eulogy = document.getElementById("eulogy-display")
    eulogy.hidden = runstate.state.last_eulogy is None
    eulogy.innerText = runstate.state.last_eulogy["text"] if runstate.state.last_eulogy else ""
