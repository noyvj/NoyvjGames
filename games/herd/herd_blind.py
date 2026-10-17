"""Blind run (GF-28): the hard mode that hides the pure-growth baseline until you reveal it.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_rules import BASE_COUPLING_RATIO


# ---- GF-28 blind run ---------------------------------------------------------------------------
# An opt-in hard mode: the pure-growth baseline (its card, the "ahead of / behind" lines, the best-ever
# and baseline markers on the gauge, the report card's comparison and the planner's baseline line) stays
# hidden, so you steer by your own numbers. It can only be switched on before the first round is played
# and only ends by being revealed: the Reveal button, filing the farm in the Ranch Ledger, or a handover.
# The reveal then spells out the whole comparison. Nothing about the sim changes (a blind farm is still
# ranked); achievements keep working, so Outperforming Baseline can still unlock and hint at the result.
BLIND_HIDDEN_NOTE = "Blind run: the baseline comparison is hidden until you reveal it."
blind_status_text = ""


def blind_hidden():
    return runstate.farm.blind_run and not runstate.farm.blind_revealed


def can_start_blind_run():
    return runstate.farm.round_number == 1 and not runstate.farm.blind_revealed


def set_blind_run(on):
    """Switches the blind run on or off. Allowed only before the first round is played. True when changed."""
    on = bool(on)
    if on == runstate.farm.blind_run or not can_start_blind_run():
        return False
    runstate.farm.blind_run = on
    runstate.farm.blind_revealed = False
    return True


def reveal_blind_run():
    """Ends a blind run for good. True when something was revealed."""
    if not blind_hidden():
        return False
    runstate.farm.blind_revealed = True
    return True


def blind_reveal_message():
    gap = runstate.farm.score() - runstate.farm.counterfactual_score()
    avoided = max(0.0, runstate.farm.counterfactual_methane - runstate.farm.methane)
    baseline = runstate.farm.counterfactual_score()
    verdict = (
        f"You finished {gap:.0f} points ahead of the pure-growth baseline"
        if gap >= 0 else f"You finished {abs(gap):.0f} points behind the pure-growth baseline"
    )
    if abs(baseline) > 1e-9:
        verdict += f" ({(runstate.farm.score() - baseline) / abs(baseline) * 100:+.1f}%)"
    return (
        f"Blind run revealed at round {runstate.farm.round_number}. Your score was {runstate.farm.score():.0f} against {baseline:.0f}. "
        f"{verdict}. Your methane was {runstate.farm.methane:.0f} against the baseline's {runstate.farm.counterfactual_methane:.0f}, "
        f"so you avoided {avoided:.0f}, and your coupling ratio ended at {runstate.farm.coupling_ratio():.2f} "
        f"({runstate.farm.decoupled_fraction() * 100:.0f}% below the baseline's {BASE_COUPLING_RATIO:.2f})."
    )


def render_blind_run():
    box = document.getElementById("blind-run-checkbox")
    box.checked = runstate.farm.blind_run
    box.disabled = not can_start_blind_run()
    note = document.getElementById("blind-run-note")
    if runstate.farm.blind_run and runstate.farm.blind_revealed:
        note.innerText = "This farm's blind run has been revealed."
    elif runstate.farm.blind_run:
        note.innerText = "Blind run on: it ends when you reveal it, file this farm in the Ranch Ledger or hand the farm over."
    elif can_start_blind_run():
        note.innerText = "Optional hard mode. Only before the first round; it hides the baseline until you reveal it."
    else:
        note.innerText = "Blind run can only be switched on before the first round is played."
    panel = document.getElementById("blind-run-panel")
    panel.hidden = not runstate.farm.blind_run
    document.getElementById("blind-reveal-button").hidden = not blind_hidden()
    text = document.getElementById("blind-reveal-text")
    text.innerText = blind_reveal_message() if runstate.farm.blind_run and runstate.farm.blind_revealed else BLIND_HIDDEN_NOTE if blind_hidden() else ""
    document.getElementById("ledger-add-button").innerText = (
        "File this farm now (reveals the blind run)" if blind_hidden() else "File this farm now"
    )
