"""The What's New changelog panel, the real-world info page and its report button."""

import json
import os

from js import document

import info_content
import info_page

import continuum_runstate as runstate


# ===========================================================================
# Changelog panel (site-wide goal, planning/TODO.md, origin K16: "Per-game
# in-game changelog panel, for every game"). A quick highlights view, not a
# full duplicate of CLAUDE.md/BCM114-DEV-LOG.md -- same loading contract as
# ACHIEVEMENTS above: the boot script fetches changelog.json and hands it to
# Python as a window global before this file runs, with a filesystem
# fallback for the pytest harness (no real `js.CHANGELOG_JSON` there).
# Unlike ACHIEVEMENTS, this is a flat list (no wrapping key) -- see
# changelog.json itself.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as `_read_achievements_json()` above."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to an empty list rather than crashing this module's whole
# import -- the changelog panel is purely informational, not core to
# Continuum's gameplay.
try:
    CHANGELOG = json.loads(_read_changelog_json())
except (ValueError, OSError, NameError):
    CHANGELOG = []


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if runstate.changelog_open else "📋 What's New"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    # Newest first -- entries are authored newest-first in changelog.json
    # already, but sort defensively so a future out-of-order edit can't
    # silently invert the panel.
    for entry in sorted(CHANGELOG, key=lambda e: e["date"], reverse=True):
        card = document.createElement("div")
        card.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-date"
        date.innerText = entry["date"]
        card.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-text"
        text.innerText = entry["entry"]
        card.appendChild(text)

        panel.appendChild(card)


def render_info_page():
    """The collapsed-by-default real-world-sources panel (Milestone 5).

    Rendering itself is the same shared/info_page.py used by all 8 climate
    quartet games — Continuum's only addition is picking which era's
    content dict to hand it, via info_content.era_info_page(), so the
    panel always shows sources for whatever era the settlement is
    currently in (including while revisiting a completed one) without
    this function needing to change as later eras ship.
    """
    info_page.render(info_content.era_info_page(runstate.state.era), runstate.info_page_open)
    _render_info_page_report()
    render_real_world()


def render_real_world():
    """W2-continuum: the collapsible "In the real world" note. Purely
    presentational (reads only state.era, changes no game number)."""
    box = document.getElementById("real-world-note")
    example = info_content.real_world_example(runstate.state.era)
    box.hidden = example is None
    if example is None:
        return
    document.getElementById("real-world-text").innerText = f"In the real world: {example['title']}. {example['text']}"
    link = document.getElementById("real-world-source")
    link.innerText = f"Source: {example['source']} (read {info_content.REAL_WORLD_READ_DATE})"
    link.href = example["url"]


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()


# ---------------------------------------------------------------------
# Z16 audit (planning/TODO.md): a lightweight in-game "something here
# might be wrong" report, matching Le Champ de Mots' report-button
# mechanism (games/champ-de-mots/CLAUDE.md's Milestone 9/24 build notes)
# in spirit rather than byte-for-byte — Continuum has no typed-answer
# content to reuse that shape verbatim, but the Milestone 5 real-world
# info panel above states citable real-world facts a player could
# reasonably dispute, which is exactly the "content that could be
# objectively wrong" case the reference feature exists for. Reuses the
# exact same answer_reports backend table/endpoint with zero schema
# changes (see app/models.py's own AnswerReport docstring: "game_id...
# isn't hardcoded... in case another game ever wants the same reporting
# mechanism"): a fixed marker string stands in for submitted_answer, the
# era's own source labels satisfy marked_correct_answer's "at least one"
# requirement, and topic_type="info_panel" lets a human triaging the
# queue (GET /answer-reports?topic_type=info_panel) tell this apart from
# any other game's reports sharing the same table.
# ---------------------------------------------------------------------

INFO_PAGE_REPORT_TOPIC_TYPE = "info_panel"
INFO_PAGE_REPORT_MARKER = "[info panel concern]"
INFO_PAGE_REPORT_BUTTON_LABEL = "Report an issue with this info"
INFO_PAGE_REPORT_SENT_LABEL = "Reported — thanks"


def _info_page_report_payload():
    """The payload for the era currently shown in the info panel, or None
    if there's nothing worth reporting — an era with no real content yet
    (the _PENDING placeholder) has no sources, and flagging placeholder
    framing text as "wrong" would tell a human triager nothing useful."""
    content = info_content.era_info_page(runstate.state.era)
    sources = content.get("sources") or []
    if not sources:
        return None
    return {
        "game_id": "continuum",
        "item_id": f"info-{runstate.state.era}",
        "submitted_answer": INFO_PAGE_REPORT_MARKER,
        "marked_correct_answer": [source["label"] for source in sources],
        "topic_type": INFO_PAGE_REPORT_TOPIC_TYPE,
    }


def _dispatch_info_page_report(payload):
    """Same Python-computes/JS-sends split as champ-de-mots' report sender
    (see index.html's window.submitAnswerReport) — a no-op outside a real
    browser (missing js.window), so the pytest harness never touches the
    network."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    sender = getattr(window, "submitAnswerReport", None)
    if sender is not None:
        sender(json.dumps(payload))


def submit_info_page_report(event=None):
    """Send an info-panel report for the era currently shown, once per era.
    A second click for the same era (or a call with nothing to report) is a
    no-op; switching to a different era's content reopens the report."""

    if runstate.info_page_report_sent and runstate._info_page_report_era == runstate.state.era:
        return None
    payload = _info_page_report_payload()
    if payload is None:
        return None
    runstate.info_page_report_sent = True
    runstate._info_page_report_era = runstate.state.era
    _dispatch_info_page_report(payload)
    render_info_page()
    return payload


def _render_info_page_report():
    """Visibility/label for the report button — only shown while the panel
    is open and the current era actually has real sources to flag."""
    button = document.getElementById("info-page-report-button")
    if not runstate.info_page_open or _info_page_report_payload() is None:
        button.hidden = True
        return
    already_sent = runstate.info_page_report_sent and runstate._info_page_report_era == runstate.state.era
    button.hidden = False
    button.disabled = already_sent
    button.innerText = INFO_PAGE_REPORT_SENT_LABEL if already_sent else INFO_PAGE_REPORT_BUTTON_LABEL
