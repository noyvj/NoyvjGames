"""State shared by the practice panel and its helpers (the plot cells, the confidence tally, the per-row clean-run badge) and
close_practice().
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import random

import champ_runstate as runstate
from champ_model import state


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


plot_cells = {}
QUESTION_RNG = random.Random()


# L6 -- session-only running tally of [correct, total] per confidence tag,
# so the player can see whether "sure" really means right. Same posture as
# combo_count/current_confidence: not persisted, a fresh page starts empty.
confidence_tally = {"sure": [0, 0], "unsure": [0, 0]}


def confidence_stats_text():
    sure, unsure = confidence_tally["sure"], confidence_tally["unsure"]
    if sure[1] == 0 and unsure[1] == 0:
        return ""
    return f"Your confidence so far: sure {sure[0]}/{sure[1]} right · not sure {unsure[0]}/{unsure[1]} right"


# L28 -- a small badge for perfectly answering a full row's worth of plots
# in one sitting: every plot in that row answered correctly this session,
# with zero wrong answers anywhere in the row this session. "One sitting"
# is read literally as *this session*, not a permanent unlock, so -- same
# posture as combo_count/ACCENT_SENSITIVE above -- all three dicts here are
# pure session state and never reach get_state()/load_state(); a fresh
# page load always starts every row unspoiled and un-badged. A row that's
# already spoiled this session can never earn the badge later even if
# every subsequent answer in it is correct -- the point is a clean run
# through the whole row, not just "eventually got them all right".
row_session_correct = {}  # sequence -> set of plot_ids answered correctly this session
row_session_spoiled = set()  # sequences with at least one wrong answer this session
row_session_perfect_badge = set()  # sequences that have earned the badge this session


def _track_row_session_answer(plot, correct):
    sequence = plot.sequence
    if sequence in row_session_spoiled:
        return
    if not correct:
        row_session_spoiled.add(sequence)
        row_session_correct.pop(sequence, None)
        return
    row_session_correct.setdefault(sequence, set()).add(plot.plot_id)
    row_plots = state.row_plots(sequence)
    if row_plots and row_session_correct[sequence] >= {p.plot_id for p in row_plots}:
        row_session_perfect_badge.add(sequence)


# Choice-button click handlers created by the last render_practice() call.
# Unlike the grid's cell handlers and the panel's other fixed buttons (each
# wired once in build_farm()/setup()), these are rebuilt on every repaint —
# so, unlike those, they have to be explicitly destroyed each time or the
# proxies pile up unboundedly over a play session.
practice_choice_proxies = []


def _destroy_practice_choice_proxies():
    for proxy in practice_choice_proxies:
        proxy.destroy()
    practice_choice_proxies.clear()


def close_practice(event=None):
    runstate.current_question = None
    runstate.current_water_kind = None
    runstate.current_result = None
    runstate.current_submitted_answer = None
    runstate.current_confidence = None
    runstate.report_sent = False
    runstate.pronunciation_report_sent = False
    runstate.practice_open = False
    runstate.deepdive_open = False
    render()
