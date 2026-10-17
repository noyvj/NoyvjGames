"""The 'My Reports' panel: a small dated feed of every report the player has sent (built on shared/narrative_log.py).
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import narrative_log
from js import document

import champ_runstate as runstate
from champ_model import state
from champ_labels import (
    BONUS_SENTENCE_REPORT_TOPIC_TYPE, BONUS_TILE_REPORT_TOPIC_TYPE, PRONUNCIATION_REPORT_TOPIC_TYPE,
)
from champ_util import _element


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# "My Reports" (Z11, planning/TODO.md, site-wide goal) -- a small, dated feed
# confirming every report this player has actually sent, built on the shared
# shared/narrative_log.py component (Continuum's "Chronicle" is that
# component's reference integration; Thaw's scientist's log is the second;
# this is the third). Investigating this task's own L14 line ("let the
# report-button flow show a short 'thanks, noted' confirmation distinct from
# the normal question-feedback flow") found it was already fully satisfied
# by the pre-existing REPORT_SENT_LABEL/PRONUNCIATION_REPORT_SENT_LABEL
# button-label swap defined above (each report button already reads
# "Reported — thanks" and disables itself) -- a genuine cross-round label
# collision with a *different* feature, per planning/TODO.md's own L14 line
# under this game's section, not a narrative-log-shaped gap at all. This
# panel is the actual narrative-log-shaped feature the Z11 task asks to
# build instead: "a dated feed of 'you reported X on this date'
# confirmations from its existing answer-reports feature." "Dated" here
# means `state.current_day` (this game's own no-wall-clock day counter,
# Milestone 2) rather than a real calendar date -- `game.py` is forbidden
# from touching any clock API at all (Milestone 7's own tested constraint,
# `test_nothing_in_the_game_runs_on_a_timer`), the same reason §14.2.4's
# report payload itself never builds its own timestamp.
# ===========================================================================
REPORT_LOG_MAX = 20

# Every one of this game's 10 submit_*_report() functions sends a payload
# whose "topic_type" is either a plot's own topic_type (vocab/grammar/
# phrase/phonetic, from the main/Review/Proficiency "should count" reports)
# or one of these three fixed markers (pronunciation concerns, and Bonus's
# two non-plot-backed report kinds) -- this maps the fixed markers to a
# readable phrase; anything else falls back to a generic "a {topic_type}
# answer" phrase built from the raw value itself.
REPORT_LOG_TOPIC_LABEL = {
    PRONUNCIATION_REPORT_TOPIC_TYPE: "a pronunciation concern",
    BONUS_TILE_REPORT_TOPIC_TYPE: "a bonus-tile translation",
    BONUS_SENTENCE_REPORT_TOPIC_TYPE: "a bonus-sentence translation",
}


def _report_log_topic_label(topic_type):
    return REPORT_LOG_TOPIC_LABEL.get(topic_type, f"a {topic_type} answer")


def _record_report_log_entry(payload):
    """Called right after every submit_*_report() function marks its own
    one-shot "sent" flag -- a local confirmation that a report was actually
    sent this session, independent of whether _dispatch_report()'s own
    network call succeeds (the flag it rides alongside is already
    fire-and-forget the same way, and this game has no clock to timestamp
    a network round-trip with regardless)."""
    answers = payload.get("marked_correct_answer") or [""]
    text = f"Reported {_report_log_topic_label(payload['topic_type'])} for “{answers[0]}”."
    narrative_log.add_entry(
        runstate.report_log,
        {"day": state.current_day, "topic": payload["topic_type"], "text": text},
        cap=REPORT_LOG_MAX,
    )


def on_toggle_report_log(event=None):
    runstate.report_log_open = not runstate.report_log_open
    render()


def _build_report_log_row(entry):
    # Same one-<p>-per-row idiom render_changelog()/render_dashboard()
    # already use for this game's own panels, rather than the
    # row/row-top/row-name/row-blurb multi-element structure Continuum's
    # own build_row callback uses -- internals are free once you're inside
    # a game, and this keeps the new panel visually consistent with the
    # rest of this game's own dashboard-style panels.
    row = document.createElement("p")
    row.className = "report-log-row"
    row.innerText = f"Day {entry['day'] + 1} — {entry['text']}"
    return row


def render_report_log():
    panel = _element("report-log-panel")
    toggle = _element("report-log-toggle-button")
    count = len(runstate.report_log)
    toggle.innerText = f"Hide My Reports ({count})" if runstate.report_log_open else f"📨 My Reports ({count})"
    panel.hidden = not runstate.report_log_open
    if not runstate.report_log_open:
        return
    narrative_log.render(
        "report-log-panel",
        runstate.report_log,
        _build_report_log_row,
        empty_text="Nothing reported yet — reports you send from any practice mode will show up here.",
        max_visible=REPORT_LOG_MAX,
    )
