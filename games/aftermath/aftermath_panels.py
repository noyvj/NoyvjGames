"""The info page, the What's New changelog, export and import of progress, the skill-tree reset, skill unlock toasts, callouts, the epilogue and the real-world note."""

import json

import export_progress
import info_page
from js import document, setTimeout
from pyodide.ffi import create_proxy

import aftermath_runstate as runstate
from aftermath_achievements import (
    _default_achievement_progress, _seed_achievement_toast_baseline, achievement_ids_earned,
    save_achievement_progress,
)
from aftermath_persist import (
    _sanitize_meta, run_log_history, save_highest_awarded_run, save_legacy_event_counts, save_legacy_events,
    save_meta, save_run_history,
)
from aftermath_rules import EVENT_LABEL, SEVERITY_VARIATION_MAX, SKILLS
from aftermath_skilltree import SkillTreeState


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Adaptation — building resilience to climate impacts already "
        "locked in — is treated by climate science and policy as its own "
        "necessary response, not a fallback for failed mitigation. Real "
        "communities that invested early in resilient infrastructure have "
        "documented, measurable payoffs. Aftermath's resource-allocation "
        "choices and its \"how far you've come\" comparison are modeled "
        "on that same idea."
    ),
    "mechanic_tie_in": (
        "The skill tree's resilience/growth split mirrors a real, "
        "documented tradeoff facing infrastructure investment: pay up "
        "front for resilience, or grow capacity and risk being caught "
        "underprepared."
    ),
    "sources": [
        {
            "label": "IPCC AR6 Working Group II — Climate Change 2022: Impacts, Adaptation and Vulnerability",
            "url": "https://www.ipcc.ch/report/ar6/wg2/",
            "note": "The authoritative global reference on adaptation as a distinct climate response, backing Aftermath's core framing.",
        },
        {
            "label": "World Resources Institute — Accelerating Climate-resilient Infrastructure Investment in China",
            "url": "https://www.wri.org/research/accelerating-climate-resilient-infrastructure-investment-china",
            "note": "A real resilience-infrastructure investment case study, grounding Aftermath's resource-allocation mechanic.",
        },
        {
            "label": "World Resources Institute — Driving System Shifts for Climate Resilience (Bhutan, Ethiopia, Costa Rica)",
            "url": "https://www.wri.org/research/driving-system-shifts-climate-resilience-case-studies-transformative-adaptation-bhutan",
            "note": "Real communities' documented adaptation journeys — strong backing for the \"look how far you've come\" hope angle.",
        },
        {
            "label": "EU Mission on Adaptation to Climate Change — Success Stories",
            "url": "https://mission-adaptation-portal.ec.europa.eu/stories-0_en",
            "note": "A running collection of real municipal adaptation wins — concrete \"this actually worked\" examples.",
        },
    ],
}


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, runstate.info_page_open)


# ===========================================================================
# K16 (planning/TODO.md "What's New" changelog, site-wide goal): a small
# in-game "what's new" panel, same shape as SOL/Canopy/Grid's reference
# achievements integration -- a flat JSON catalog fetched into the Pyodide
# boot sequence and handed to Python as a window global (see index.html),
# rendered into a hidden-until-opened panel. Unlike achievements.json this
# catalog isn't a set of checkable conditions -- it's just curated highlight
# text -- so there's no earned/unearned state, only a newest-first list.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as _read_achievements_json(): the boot script
    fetches changelog.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off disk,
    keeping the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no changelog" rather than crashing this module's whole
# import -- same defensive shape as ACHIEVEMENTS below, since a "what's
# new" panel is additive, not core to Aftermath's gameplay.
try:
    CHANGELOG = sorted(json.loads(_read_changelog_json()), key=lambda entry: entry["date"], reverse=True)
except Exception:
    CHANGELOG = []


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if runstate.changelog_open else f"\U0001f4cb What's New ({len(CHANGELOG)})"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    if not CHANGELOG:
        empty = document.createElement("p")
        empty.innerText = "Nothing logged yet."
        panel.appendChild(empty)
        return

    for entry in CHANGELOG:
        row = document.createElement("div")
        row.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-entry-date"
        date.innerText = entry["date"]
        row.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-entry-text"
        text.innerText = entry["entry"]
        row.appendChild(text)

        panel.appendChild(row)


# ===========================================================================
# E12: export/import code for the localStorage-based skill tree, run
# history, legacy system, and achievement progress -- everything this
# game persists *outside* the per-run save-widget round trip (see
# get_state()/load_state()'s own big comment below for why those two
# mechanisms are kept separate). A base64-wrapped JSON blob, the same
# shape as the shared save widget's own codes, but carrying this game's
# cross-run progress instead of one run's live state.
# ===========================================================================
PROGRESS_EXPORT_VERSION = 1


def export_progress_code():
    bundle = {
        "version": PROGRESS_EXPORT_VERSION,
        "skill_tree": runstate.skill_tree.to_dict(),
        "run_history": list(runstate.run_history),
        "legacy_events": sorted(runstate.legacy_events),
        "legacy_event_counts": dict(runstate.legacy_event_counts),
        "achievement_progress": dict(runstate.achievement_progress),
        "highest_awarded_run": runstate.highest_awarded_run,
        "meta": dict(runstate.meta),
    }
    # Z8: codec now lives in shared/export_progress.py (the "portable
    # progress-code" pattern shared with SOL's A17) -- no prefix, matching
    # this code's original plain-base64 shape (no existing player-held
    # code has a tag to check against, so adding one now would just be
    # decoration).
    return export_progress.encode_progress_code(bundle)


def import_progress_code(code):
    """Parses and applies a code from export_progress_code(). Returns True
    on success, False on any malformed input -- unlike load_state() below
    (which deliberately raises on a bad payload, since that one only ever
    receives this same site's own save codes), a progress code is
    hand-typed/pasted by a player and a bad paste is an expected, common
    failure mode that should fail soft with a status message, not crash
    the page."""

    ok, bundle = export_progress.decode_progress_code(code)
    if not ok or "skill_tree" not in bundle:
        return False

    try:
        st_data = bundle["skill_tree"]
        new_skill_tree = SkillTreeState()
        new_skill_tree.knowledge_points = st_data.get("knowledge_points", 0)
        new_skill_tree.unlocked = set(st_data.get("unlocked", []))
        new_skill_tree.lifetime_knowledge = st_data.get("lifetime_knowledge", new_skill_tree.knowledge_points)

        new_run_history = list(bundle.get("run_history", []))
        new_legacy_events = set(bundle.get("legacy_events", []))
        new_legacy_event_counts = {
            str(k): int(v) for k, v in dict(bundle.get("legacy_event_counts", {})).items()
        }
        new_achievement_progress = _default_achievement_progress()
        for key, value in dict(bundle.get("achievement_progress", {})).items():
            if key in new_achievement_progress:
                new_achievement_progress[key] = bool(value)
        new_highest_awarded_run = int(bundle.get("highest_awarded_run", 0))
    except (ValueError, TypeError, AttributeError):
        return False

    runstate.skill_tree = new_skill_tree
    runstate.run_history = new_run_history
    runstate.legacy_events = new_legacy_events
    runstate.legacy_event_counts = new_legacy_event_counts
    runstate.achievement_progress = new_achievement_progress
    runstate.highest_awarded_run = new_highest_awarded_run
    runstate.meta = _sanitize_meta(bundle.get("meta", {}))
    save_meta()

    runstate.skill_tree.save()
    save_run_history(runstate.run_history)
    save_legacy_events(runstate.legacy_events)
    save_legacy_event_counts(runstate.legacy_event_counts)
    save_achievement_progress()
    save_highest_awarded_run(runstate.highest_awarded_run)
    _seed_achievement_toast_baseline()
    return True


def progress_summary_text():
    """E26: a short human-readable summary of what an exported progress
    code contains, shown before the player copies it."""
    best = f", best score {max(runstate.run_history):.0f}" if runstate.run_history else ""
    earned = len(achievement_ids_earned())
    name = f"Settlement \"{runstate.meta['settlement_name']}\": " if runstate.meta["settlement_name"] else ""
    return (
        f"{name}{len(runstate.run_history)} run{'s' if len(runstate.run_history) != 1 else ''} completed{best}, "
        f"{len(runstate.skill_tree.unlocked)}/{len(SKILLS)} skills unlocked, "
        f"{runstate.skill_tree.knowledge_points} knowledge in hand ({runstate.skill_tree.lifetime_knowledge} lifetime), "
        f"{earned} achievement{'s' if earned != 1 else ''}."
    )


# ===========================================================================
# E13: reset skill tree.
#
# Z22 cross-game audit: this used to be gated behind a lightweight in-UI
# two-click confirmation (click once to arm, click again to actually
# reset) rather than a browser confirm() dialog -- chosen at the time to
# stay self-contained in the fake-DOM test harness with no new `window`
# global needed, and any other skill-tree/run action cleared the pending
# confirmation so a stray click much later couldn't accidentally fire it.
# shared/confirm-dialog.js didn't exist yet when that was written; now
# that it does (and every other game's own reset/retire-style action
# already routes through it -- Grid's retire-last-plant, Herd's pivot
# investment, Loop's Start New Chain, Trade Empire's automate/research,
# SOL's reset-world/prestige), migrated to match: a real modal is a
# stronger affordance than a button whose label silently changes meaning
# after the first click, offers "don't ask me again," and doesn't block
# on some *other* button being clicked first to "escape" a still-armed
# reset the way the two-click version could. `_confirm_dialog_ask()` is
# the same helper shape as every other game's own copy.
# ===========================================================================
def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm, allow_skip=None):
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    options = {} if allow_skip is None else {"allowSkip": allow_skip}
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
        **options,
    )


def reset_refund_amount():
    """E22: knowledge points a reset would refund from *spent* skills --
    what the confirm dialog's message shows before you commit."""
    return sum(SKILLS[skill_id]["cost"] for skill_id in runstate.skill_tree.unlocked)


def reset_refund_total():
    return runstate.skill_tree.knowledge_points + reset_refund_amount()


def reset_skill_tree():
    """Refunds every spent-and-unspent knowledge point (so respeccing
    doesn't punish a player for having unlocked anything) and clears which
    skills are unlocked. lifetime_knowledge (the achievement-tracking
    total) is deliberately untouched -- it's a lifetime-earned counter,
    not a spendable balance, so a respec shouldn't roll it back."""
    total_refund = reset_refund_total()
    runstate.skill_tree.knowledge_points = total_refund
    runstate.skill_tree.unlocked = set()
    runstate.skill_tree.save()


# ===========================================================================
# E14: a dedicated toast surfacing a skill's real-world grounding text
# prominently at the moment it's unlocked -- the always-visible
# `skill-practice` paragraph in the skill tree already shows this text,
# but this makes it impossible to miss on the exact unlock that made it
# relevant.
# ===========================================================================
SKILL_TOAST_BASE_MS = 4000
SKILL_TOAST_MS_PER_CHAR = 35
SKILL_TOAST_MIN_MS = 6000
SKILL_TOAST_MAX_MS = 14000


def skill_toast_duration_ms(skill_id):
    """E2: longer grounding text stays up longer -- a fixed base plus a
    per-character reading allowance, clamped so no toast is ever gone
    faster than the old fixed 6s or lingers past 14s."""
    length = len(SKILLS[skill_id]["real_practice"])
    return max(SKILL_TOAST_MIN_MS, min(SKILL_TOAST_MAX_MS, SKILL_TOAST_BASE_MS + SKILL_TOAST_MS_PER_CHAR * length))


def _display_skill_unlock_toast(skill_id):
    skill = SKILLS[skill_id]
    toast = document.getElementById("skill-unlock-toast")
    text = document.getElementById("skill-unlock-toast-text")
    text.innerText = f"🔓 {skill['label']} unlocked — {skill['real_practice']}"
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, skill_toast_duration_ms(skill_id))


# ===========================================================================
# E10: a brief, self-clearing visual flash on the resources readout when
# an investment is actually spent -- confirmation feedback beyond the
# number itself changing. Reuses the same create_proxy/setTimeout
# one-shot-timer pattern as the achievement/skill-unlock toasts above.
# ===========================================================================
def _flash_element(element_id, duration_ms=400, css_class="invest-flash"):
    element = document.getElementById(element_id)
    element.classList.add(css_class)

    def _remove(*args):
        element.classList.remove(css_class)
        proxy.destroy()

    proxy = create_proxy(_remove)
    setTimeout(proxy, duration_ms)


# ===========================================================================
# One-time callouts (E8 first-zero-score reassurance, E28 first harsher-than-
# base severity swing). A shared #callout-display line; the "already shown"
# flags persist in `meta` so each fires once per browser, ever. The message
# itself is transient (cleared when a new run starts).
# ===========================================================================

NEGATIVE_RUN_TIP = (
    "💡 That run ended with nothing left — but nothing is lost. Your skill tree persists "
    "regardless: you still earned at least 1 knowledge point, and every skill you've unlocked "
    "carries into the next run."
)
HARSH_SEVERITY_CALLOUT = (
    "💡 That event hit harder than a first-run event ever could. This isn't bad luck — the more skills "
    "you've unlocked (and the more runs you've completed), the wider the severity spread gets: a "
    "stronger settlement is asked bigger questions, on top of being better equipped to answer them."
)


def _maybe_trigger_callouts(run_state):
    if run_state.event_log:
        last = run_state.event_log[-1]
        if not runstate.meta["seen_harsh_callout"] and last["severity"] > SEVERITY_VARIATION_MAX:
            runstate.meta["seen_harsh_callout"] = True
            save_meta()
            runstate.callout_message = HARSH_SEVERITY_CALLOUT
    if run_state.is_complete() and run_state.resources <= 0 and not runstate.meta["seen_negative_tip"]:
        runstate.meta["seen_negative_tip"] = True
        save_meta()
        runstate.callout_message = NEGATIVE_RUN_TIP


# E5: "generational memory" -- occasionally the upcoming event's flavor
# references what the same slot cost a past run, deepening the legacy system.
def generational_memory_text(run_state):
    if run_state.is_complete() or not run_log_history:
        return ""
    if (run_state.run_number + run_state.event_index) % 2 != 0:
        return ""
    index = run_state.event_index
    for entry in reversed(run_log_history):
        if entry.get("run_number") == run_state.run_number:
            continue
        log = entry.get("event_log", [])
        if index < len(log) and log[index]["type"] == run_state.next_event_type():
            past = log[index]
            return (
                f"🕰️ Memory of Run #{entry['run_number']}: the last time this settlement faced "
                f"{EVENT_LABEL[past['type']]} at this point, it cost {past['damage']:.0f} damage."
            )
    return ""


# E13: a short narrative epilogue at the end of an extended run, in the
# spirit of Continuum's era-transition beats, scaled to Aftermath's format.
def extended_epilogue_text(run_state):
    if not run_state.extended or not run_state.is_complete():
        return ""
    if run_state.resources <= 0:
        return (
            "Epilogue — Two full cycles of shocks left the settlement with nothing in reserve. "
            "But the people are still here, and what they learned is written into every plan that follows."
        )
    if run_state.resources > run_state.starting_resources:
        return (
            "Epilogue — Fourteen shocks came and went, and the settlement ended richer than it began. "
            "What once felt like recovery has become routine: a community that expects the next storm and is ready for it."
        )
    return (
        "Epilogue — The settlement came through fourteen shocks bruised but standing. "
        "Endurance is its own kind of progress: the next generation inherits a place that has already been tested."
    )


# ===========================================================================
# W2-aftermath -- "In the real world": for each kind of shock, one real
# recovery or response, with the source named and linked. Every figure was read
# from the linked page on 2026-09-26 (nothing recalled from memory); where a
# page did not give a number, none is quoted. The note follows the event you
# last faced, or the next one before the first event, and never changes any
# number in a run.
# ===========================================================================
REAL_WORLD_READ_DATE = "2026-09-26"
REAL_WORLD_EXAMPLES = {
    "flood": {
        "title": "Room for the River (Netherlands)",
        "text": "After floods in 1993 and 1995 forced the evacuation of over 200,000 people, the Netherlands ran a programme from 2006 to 2015 with a budget of 2.2 billion euros, about forty projects, to give its rivers more space rather than only raising dikes.",
        "source": "Wikipedia, Room for the River", "url": "https://en.wikipedia.org/wiki/Room_for_the_River",
    },
    "heatwave": {
        "title": "France's National Heat Wave Plan",
        "text": "The 2003 European heat wave is estimated to have killed more than 70,000 people, including 14,802 in France, mostly elderly. The following year France drew up a National Heat Wave Plan built on forecasting and alert systems.",
        "source": "Wikipedia, 2003 European heat wave", "url": "https://en.wikipedia.org/wiki/2003_European_heat_wave",
    },
    "storm": {
        "title": "Bangladesh's Cyclone Preparedness Programme",
        "text": "Set up in 1973 as an early-warning system for coastal Bangladesh, the programme now has 55 thousand volunteers who carry warnings to villages, and is credited with saving thousands of lives.",
        "source": "Wikipedia, Cyclone Preparedness Programme", "url": "https://en.wikipedia.org/wiki/Cyclone_Preparedness_Programme",
    },
    "supply_chain": {
        "title": "The 2021 Suez Canal blockage",
        "text": "One grounded ship blocked the canal for six days, 23 to 29 March 2021. By 28 March at least 369 ships were queuing, and Lloyd's List calculated about 9.6 billion dollars of goods a day was held up.",
        "source": "Wikipedia, 2021 Suez Canal obstruction", "url": "https://en.wikipedia.org/wiki/2021_Suez_Canal_obstruction",
    },
    "infrastructure_failure": {
        "title": "The 2003 Northeast blackout",
        "text": "On 14 August 2003 a software bug that stalled a control room's alarm system for over an hour let a local fault cascade, and 55 million people in Ontario and eight US states lost power, for between two hours and four days depending on where they lived.",
        "source": "Wikipedia, Northeast blackout of 2003", "url": "https://en.wikipedia.org/wiki/Northeast_blackout_of_2003",
    },
    "civil_unrest": {
        "title": "Christchurch's Student Volunteer Army",
        "text": "After the 2010 and 2011 Christchurch earthquakes strained the city, a student-started volunteer effort grew to 13,000 students a week at its peak and helped clear over 360,000 tonnes of silt, showing how community cooperation can be rebuilt fast.",
        "source": "Wikipedia, Student Volunteer Army", "url": "https://en.wikipedia.org/wiki/Student_Volunteer_Army",
    },
    # FY-3: read live on 2026-10-09 (a later read than the six above, so it carries its own date).
    "heat_mortality": {
        "title": "The 1995 Chicago heat wave",
        "text": "The heat wave caused 739 heat-related deaths in Chicago over five days, mostly elderly poor residents, some without air conditioning and others unable to afford to run it. City officials did not release a heat emergency warning until the last day, so the city's five cooling centres were not fully used.",
        "source": "Wikipedia, 1995 Chicago heat wave", "url": "https://en.wikipedia.org/wiki/1995_Chicago_heat_wave",
        "read": "2026-10-09",
    },
}


def real_world_event_type():
    """The event type the note is about: the last one faced, else the next."""
    if runstate.run.event_log:
        return runstate.run.event_log[-1]["type"]
    if runstate.run.event_index < len(runstate.run.schedule):
        return runstate.run.schedule[runstate.run.event_index]
    return None


def render_real_world():
    box = document.getElementById("real-world-note")
    example = REAL_WORLD_EXAMPLES.get(real_world_event_type())
    box.hidden = example is None
    if example is None:
        return
    document.getElementById("real-world-text").innerText = f"In the real world: {example['title']}. {example['text']}"
    link = document.getElementById("real-world-source")
    link.innerText = f"Source: {example['source']} (read {example.get('read', REAL_WORLD_READ_DATE)})"
    link.href = example["url"]
