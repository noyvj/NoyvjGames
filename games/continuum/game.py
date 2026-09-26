"""Continuum — a sustainable city across the ages.

Runs in-browser via Pyodide. This file is the browser layer only: it owns
the DOM, the event handlers, and the rendering. All of the actual thinking
lives in the engine modules that sit beside it —

    sim.py             city simulation core (population, resources, land)
    sustainability.py  the livability score (Milestone 2)
    research.py        the research tree engine (Milestone 3)
    save.py            the continuous-save / era-snapshot schema (Milestone 4)
    info_content.py    real-world info-panel content, keyed by era (Milestone 5)
    log.py             the ongoing log / diegetic feedback system (Milestone 6)
    visual.py          state -> visual data contract for the Three.js layer (Phase 5)

— which is the separation the design doc's tech notes ask for, so that six
more eras of content land in the engines rather than in one tangled file.
`info_page.py` (the render/toggle logic itself) is `shared/info_page.py`,
the same module the 8 climate-quartet games use — fetched into Pyodide's
virtual filesystem by index.html the same way canopy's boot script does.

Phase 1 complete: the Tribal-era season loop, the sustainability panel, the
research panel, the collapsed real-world info panel, and the shared save
widget's get_state()/load_state() contract. Phase 2's log and era-transition
systems land here too, since both are things the player reads.
"""

import json
import os
import sys
import time

# index.html writes the engine modules into Pyodide's virtual filesystem
# (the working directory) before running this file; make sure that
# directory is importable. Harmless under pytest, where conftest.py has
# already put the game directory on the path.
_HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import archive  # noqa: E402
import challenges  # noqa: E402
import consulting  # noqa: E402
import info_content  # noqa: E402
import info_page  # noqa: E402
import minutes  # noqa: E402
import narrative_log  # noqa: E402
import research  # noqa: E402
import save  # noqa: E402
import sim  # noqa: E402
import summary  # noqa: E402
import sustainability  # noqa: E402
import trajectory  # noqa: E402
import views  # noqa: E402
import transition  # noqa: E402
import visual  # noqa: E402

from js import document, setTimeout  # noqa: E402
from pyodide.ffi import create_proxy  # noqa: E402


campaign = save.Campaign(sim.CityState(), research.build_tree())
# Module-level aliases for the two live engine objects. The save system
# always restores *into* these objects rather than replacing them, so these
# names stay valid across a load.
state = campaign.state
tree = campaign.tree
chronicle = campaign.log

# Milestone 5 — collapsed by default, per the design doc's Core system 6.
# Not one of CITY_FIELDS/tree state, so it rides in campaign.ui instead
# (get_state()/load_state() below), exactly what that save field is for.
info_page_open = False

# Milestone 17 (K14) — the research tree search/filter query. Transient UI
# state, not saved: unlike info_page_open (which rides campaign.ui because
# a toggle's open/closed state is worth restoring on load), a text query
# has no reason to survive a reload, so it's a plain module-level string,
# always "" on a fresh module load. achievements_open (below) is the same
# category — also never saved.
research_search_query = ""

# K6 -- branch quick-filter chips. Transient like the search query.
research_branch_filter = set()


def current_effects():
    """The aggregate modifiers applied to the simulation this season.

    The single seam through which research reaches both the simulation and
    the sustainability score — nothing else in the game reads the tree.
    """
    return tree.effects()


# --- narration ---------------------------------------------------------
def season_report_message(report):
    """One plain-language line summarising the season that just passed.

    Read with `.get()` rather than `[]` because `last_report` is a saved
    field: a loaded save can carry a report written by an earlier build of
    the season loop, and narrating one line of flavour text is not worth
    taking the whole render down over a key that didn't exist yet.
    """
    if not isinstance(report, dict):
        return "The settlement is waiting on your word."

    fed = report.get("fed_fraction", 1.0)
    parts = []
    if fed >= 1.0:
        parts.append("Everyone ate.")
    elif fed <= 0.0:
        parts.append("Nobody ate.")
    else:
        parts.append(f"Only {fed * 100:.0f}% of the settlement ate.")

    if report.get("deaths"):
        parts.append(f"{report['deaths']} lost to hunger.")
    if report.get("births"):
        parts.append(f"{report['births']} born.")
    if report.get("spoiled", 0.0) > 0.5:
        parts.append(f"{report['spoiled']:.0f} food spoiled for want of storage.")
    if report.get("surplus_banked", 0.0) > 0.5:
        parts.append(f"{report['surplus_banked']:.0f} preserved as trade surplus.")
    if report.get("extraction", 0.0) > report.get("sustainable_yield", float("inf")):
        parts.append("The land is being taken from faster than it recovers.")
    # Classical+ (Milestone 9): a canal only delivers what it's built for if
    # Administrators actually staff it -- narrate the gap so an under-staffed
    # canal reads as a real, visible cost rather than a silent one.
    if report.get("canals", 0) > 0 and report.get("canal_staffing_ratio", 1.0) < 1.0:
        staffing_pct = report["canal_staffing_ratio"] * 100
        parts.append(f"Canals running at {staffing_pct:.0f}% coordination — more administrators needed.")
    # Medieval+ (Milestone 10): Public Works isn't staffed the way a canal
    # is, but it still has a visible gap worth narrating -- unlike the
    # canal line above (a production shortfall), this is a resilience
    # warning: the settlement hasn't paid ahead of a shock for everyone.
    if report.get("public_works", 0) > 0 and report.get("public_works_coverage_ratio", 1.0) < 1.0:
        coverage_pct = report["public_works_coverage_ratio"] * 100
        parts.append(
            f"Public works cover {coverage_pct:.0f}% of the settlement — "
            "the rest would be exposed if a bad season hit."
        )
    # Industrial+ (Milestone 11): unlike every earlier narration line above,
    # this one calls out a real GROWTH consequence, not only a resource or
    # resilience one -- pollution is directly slowing next season's growth,
    # per the Economic Journal source's "measurably reduced long-run city
    # growth" finding (see sim.py's pollution constants and
    # sustainability._industrial_pollution_penalty()).
    if report.get("pollution", 0.0) > 0.3:
        parts.append(
            f"Industrial smoke hangs over the settlement ({report['pollution'] * 100:.0f}% "
            "pollution) — growth is slower for it, and it isn't doing the sustainability "
            "score any favors either."
        )
    # Digital+ (Milestone 12): a second growth-adjacent narration line,
    # deliberately worded differently from pollution's above -- sprawl
    # doesn't slow growth directly, it makes the SAME extraction land
    # harder on the land (see sim.py's SPRAWL_EXTRACTION_PENALTY_WEIGHT),
    # which is what actually threatens growth if it pushes land health down
    # far enough.
    if report.get("sprawl", 0.0) > 0.3:
        parts.append(
            f"The settlement is spreading out faster than it's filling in ({report['sprawl'] * 100:.0f}% "
            "sprawl) — the same production is leaning harder on the land for it, and it isn't "
            "doing the sustainability score any favors either."
        )
    # Space Age+ (Milestone 13): unlike every narration line above,
    # habitat_layout_ratio isn't a lagged stock that builds up over time --
    # it's a coverage ratio recomputed fresh each season from current rings/
    # architects, the same shape Classical's canal-staffing line and
    # Medieval's public-works-coverage line already narrate. Only narrated
    # once there's at least one ring built to have an opinion about, the
    # same "only narrate a real gap" discipline those two lines follow.
    if report.get("habitat_rings", 0) > 0 and report.get("habitat_layout_ratio", 1.0) < 1.0:
        layout_pct = report["habitat_layout_ratio"] * 100
        parts.append(
            f"Off-world habitat layout is only serving {layout_pct:.0f}% of the settlement well — "
            "the rest live somewhere the design doesn't really work for them."
        )

    return " ".join(parts)


def land_health_message(land_health):
    if land_health >= 0.9:
        return "The land around the settlement is untouched."
    if land_health >= 0.65:
        return "The land shows some wear."
    if land_health >= 0.4:
        return "The land is thinning — the foraging is worse than it was."
    return "The land is stripped. Little grows back."


# --- render ------------------------------------------------------------
def render():
    effects = current_effects()
    render_clock()

    document.getElementById("era-display").innerText = f"{sim.ERA_LABEL[state.era]} era"
    document.getElementById("season-display").innerText = f"Season {state.season}"

    housing = state.housing_capacity(effects)
    document.getElementById("population-display").innerText = f"People: {state.population}"
    document.getElementById("housing-display").innerText = (
        f"Shelter for {housing:.0f}"
        + (" — overcrowded" if state.population > housing else "")
    )
    document.getElementById("idle-display").innerText = f"Unassigned: {state.idle_workers()}"

    storage = state.food_storage_capacity(effects)
    document.getElementById("food-display").innerText = (
        f"Food: {state.resources['food']:.0f} / {storage:.0f}"
    )
    document.getElementById("materials-display").innerText = (
        f"Materials: {state.resources['materials']:.0f}"
    )
    document.getElementById("tools-display").innerText = f"Tools: {state.resources['tools']:.1f}"
    document.getElementById("knowledge-display").innerText = (
        f"Knowledge: {state.resources['knowledge']:.1f}"
    )
    # Surplus (Milestone 8, Agrarian+): shown once there's a nonzero amount
    # or the settlement has actually reached an era that can bank it, so a
    # Tribal-only playthrough never sees a "Surplus: 0.0" line that means
    # nothing yet.
    surplus_line = document.getElementById("surplus-display")
    if sim.era_index(state.era) >= sim.era_index("agrarian") or state.resources["surplus"] > 0:
        surplus_line.hidden = False
        surplus_line.innerText = f"Surplus: {state.resources['surplus']:.1f}"
    else:
        surplus_line.hidden = True

    document.getElementById("land-health-display").innerText = (
        f"Land health: {state.land_health * 100:.0f}% — {land_health_message(state.land_health)}"
    )
    document.getElementById("land-health-bar").style.width = f"{state.land_health * 100:.0f}%"

    document.getElementById("season-report-display").innerText = season_report_message(
        state.last_report
    )

    render_work()
    render_buildings()
    render_sustainability(effects)
    render_research()
    render_info_page()
    render_log()
    render_era_progress(effects)
    render_revisit()
    update_achievements_display()
    update_scenario_display()
    update_hard_mode_display()
    update_summary_panel()
    update_views_panel(effects)
    update_consulting_display()
    render_insights(effects)
    _notify_visual_layer()


def get_visual_state():
    """Phase 5's data contract for the Three.js render layer — see
    visual.py. Exposed as a plain module-level function (same shape as
    get_state()/load_state() below) so render3d.js can call it through
    Pyodide's globals the same way the shared save widget calls those two.
    Returns a plain dict; pyodide's toJs() (called from JS) turns it into
    a plain JS object, mirroring the save widget's own contract.
    """
    return visual.visual_state(state, current_effects())


def _notify_visual_layer():
    """Tells render3d.js the 2D state just moved, so it can redraw the 3D
    scene to match — called at the end of every render(), i.e. after any
    assignment, build, research, season-advance, era-transition, or
    save/load.

    Deliberately lazy and defensive, the same `getattr(window, name, None)`
    pattern champ-de-mots' own `_dispatch_report()` uses for its network
    call: `js.window` doesn't exist under the pytest fake-DOM harness (only
    `js.document` is faked — see tests/conftest.py), so this is a silent
    no-op there, and it's equally a silent no-op in a real browser whenever
    render3d.js hasn't installed the hook — Three.js failed to load, WebGL
    isn't available, or the player has switched to the 2D fallback view.
    The 2D UI's own render() must never depend on this call succeeding,
    which is exactly why this function swallows both failure modes instead
    of asserting either dependency exists.
    """
    try:
        from js import window
    except ImportError:
        return
    hook = getattr(window, "continuumOnRender", None)
    if hook is not None:
        hook()


# ===========================================================================
# K12/K18 (planning/TODO.md): starting scenario select + opt-in hard mode.
# Built together since K18 is explicitly "likely alongside K12's scenario
# select" in the task's own wording, and both are opt-in starting-
# condition/difficulty controls in the same "toggle set, not a full menu
# system" shape Grid's own steeper-demand-growth/weather-variability
# toggles established (see games/grid/CLAUDE.md's settings-panel section).
# ===========================================================================
#
# Scenario is locked once the settlement has taken its first real action.
# `state.season > 1` is a clean, already-existing "has a season ever been
# advanced" signal — CityState.__init__ always starts at 1, and
# advance_season() is the only thing that ever increments it — so
# re-picking a scenario mid-playthrough can't retroactively rewrite a
# settlement that has already grown past its starting numbers. Hard mode
# has no such lock: like Grid's own toggles, it can be flipped at any
# time; see sustainability.py's own K18 note for exactly what it tightens.
def _scenario_locked():
    # K22: a consulting case replaces the opening conditions wholesale, so the
    # normal scenario picker stays locked while one is on the table.
    return state.season > 1 or consulting.get(campaign.ui) is not None


def _make_select_scenario_handler(scenario_id):
    def handler(event=None):
        if _scenario_locked() or scenario_id not in sim.SCENARIOS:
            return
        config = sim.scenario_config(scenario_id)
        # Mutated in place, the same "restore into the existing object"
        # discipline save.restore_city() already uses, rather than
        # constructing and swapping in a whole new CityState — state is
        # aliased by campaign.state and this module's own `state` name
        # alike, and mutating in place keeps both valid with no
        # reassignment needed.
        state.scenario = scenario_id
        state.population = config["population"]
        state.resources["food"] = config["food"]
        state.resources["materials"] = config["materials"]
        state.resources["tools"] = config["tools"]
        state.land_health = config["land_health"]
        state.clamp_allocation()
        # Re-baseline the log's own "have we already reported this" state
        # against the newly-chosen starting numbers -- the settlement is
        # still at season 1 with nothing researched, the same precondition
        # bootstrap() itself documents needing, so this is safe to call
        # again here exactly as it was at Campaign construction.
        chronicle.bootstrap(state, tree, current_effects())
        render()
    return handler


def on_toggle_hard_mode(event=None):
    state.hard_mode = not state.hard_mode
    render()


# --- K22 consulting mode --------------------------------------------------
def _make_consulting_start_handler(case_id):
    def handler(event=None):
        if consulting.apply(campaign, case_id, chronicle):
            chronicle.log_challenge(
                state.season, state.era, f"Called in to advise: {consulting.CASES[case_id]['label']}."
            )
            render()
            _seed_achievement_toast_baseline()
    return handler


def on_consulting_abandon(event=None):
    if consulting.abandon(campaign, chronicle):
        render()
        _seed_achievement_toast_baseline()


def update_consulting_display():
    entry = consulting.get(campaign.ui)
    pristine = consulting.is_pristine(campaign)
    for case_id in consulting.CASES:
        button = document.getElementById(f"consulting-case-{case_id}-button")
        button.disabled = not pristine
        button.classList.toggle("selected", entry is not None and entry["case"] == case_id)
    document.getElementById("consulting-status-display").innerText = (
        consulting.status_text(entry, state)
        or (
            "Take over a struggling, pre-built city. Only offered before you play a season."
            if pristine
            else "Consulting cases are only offered on a fresh, untouched start."
        )
    )
    document.getElementById("consulting-abandon-button").hidden = entry is None


def update_scenario_display():
    locked = _scenario_locked()
    note = document.getElementById("scenario-select-note")
    note.innerText = (
        "Locked in for this settlement now that play has begun."
        if locked
        else "Pick before advancing your first season — this can't be changed afterward."
    )
    for scenario_id in sim.SCENARIOS:
        button = document.getElementById(f"scenario-{scenario_id}-button")
        button.disabled = locked
        button.classList.toggle("selected", state.scenario == scenario_id)


def update_hard_mode_display():
    button = document.getElementById("hard-mode-toggle-button")
    button.innerText = f"☠️ Hard Mode: {'ON' if state.hard_mode else 'OFF'}"
    button.classList.toggle("active", state.hard_mode)


# ===========================================================================
# K5 (planning/TODO.md): the civilization summary report. An on-demand
# panel, not a forced end screen -- see summary.py's own module docstring
# for why (Continuum has no forced end state to hook, the same "no hard
# fail/win state" shape Grid's own Run Summary panel documents). Same
# hidden-until-opened idiom as the achievements/changelog panels above,
# and (unlike them) purely a this-session display preference -- never
# persisted to the save, matching changelog_open/achievements_open.
# ===========================================================================
summary_panel_open = False


# ===========================================================================
# K18 settlement archive + K20 shareable infographic card. Records live in
# the browser's localStorage (a per-device keepsake, not part of the save
# code), validated through archive.py on every read. The thumbnail and the
# card image come from the 3D canvas via window.ContinuumVisual.capture and
# window.ContinuumCard.download (plain JS); both are absent in the 2D
# fallback and under the test harness, and everything degrades to no image.
# ===========================================================================
_archive_proxies = []
_archive_confirm_clear = False


def _js_window():
    try:
        from js import window
    except ImportError:
        return None
    return window


def archive_load():
    window = _js_window()
    if window is None:
        return []
    try:
        raw = window.localStorage.getItem(archive.STORAGE_KEY)
    except Exception:
        return []
    return archive.clean_records(raw) if isinstance(raw, str) else []


def archive_store(records):
    window = _js_window()
    if window is None:
        return False
    try:
        window.localStorage.setItem(archive.STORAGE_KEY, archive.serialize(records))
        return True
    except Exception:
        return False


def _capture_image(width, quality):
    """A JPEG data URL of the live 3D scene, or '' when there is none."""
    window = _js_window()
    visual_layer = getattr(window, "ContinuumVisual", None) if window is not None else None
    capture = getattr(visual_layer, "capture", None)
    if capture is None:
        return ""
    try:
        result = capture(width, quality)
    except Exception:
        return ""
    return result if isinstance(result, str) else ""


def _today():
    return time.strftime("%Y-%m-%d")


def current_record(thumbnail=""):
    return archive.make_record(campaign, len(achievement_ids_earned()), _today(), thumbnail)


def on_archive_current(event=None):
    global _archive_confirm_clear
    _archive_confirm_clear = False
    record = current_record(archive.clean_thumbnail(_capture_image(320, 0.7)))
    if record is not None:
        archive_store(archive.add_record(archive_load(), record))
    update_summary_panel()


def _make_archive_delete_handler(index):
    def handler(event=None):
        archive_store(archive.remove_record(archive_load(), index))
        update_summary_panel()
    return handler


def on_archive_clear(event=None):
    global _archive_confirm_clear
    if not _archive_confirm_clear:
        _archive_confirm_clear = True
    else:
        _archive_confirm_clear = False
        archive_store([])
    update_summary_panel()


def _download_card(record, thumbnail):
    window = _js_window()
    card = getattr(window, "ContinuumCard", None) if window is not None else None
    download = getattr(card, "download", None)
    if download is None:
        return False
    payload = {
        "title": "Continuum",
        "lines": archive.card_lines(record),
        "thumb": thumbnail,
        "filename": f"continuum-card-{record['era']}-{record['saved_on']}.png",
    }
    try:
        download(json.dumps(payload))
    except Exception:
        return False
    return True


def on_card_current(event=None):
    _download_card(current_record(), _capture_image(720, 0.85))


def _make_card_handler(index):
    def handler(event=None):
        records = archive_load()
        if 0 <= index < len(records):
            _download_card(records[index], records[index]["thumb"])
    return handler


def _archive_button(parent, button_id, text, handler):
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.innerText = text
    proxy = create_proxy(handler)
    _archive_proxies.append(proxy)
    button.addEventListener("click", proxy)
    parent.appendChild(button)
    return button


def _render_archive_section(panel):
    """Appends the archive gallery + card buttons to the summary panel."""
    for proxy in _archive_proxies:
        proxy.destroy()
    del _archive_proxies[:]
    records = archive_load()

    heading = document.createElement("h3")
    heading.className = "summary-eras-heading"
    heading.innerText = f"Settlement archive ({len(records)} of {archive.MAX_RECORDS})"
    panel.appendChild(heading)
    note = document.createElement("p")
    note.className = "row-blurb"
    note.innerText = (
        "File this settlement's stats and a picture of its 3D view in a gallery kept on this device only. "
        "The oldest entry is dropped once the archive is full."
    )
    panel.appendChild(note)
    actions = document.createElement("div")
    actions.className = "archive-actions"
    _archive_button(actions, "archive-add-button", "Add this settlement to the archive", on_archive_current)
    _archive_button(actions, "archive-card-current-button", "Download a shareable card", on_card_current)
    panel.appendChild(actions)

    gallery = document.createElement("div")
    gallery.className = "archive-gallery"
    for index in range(len(records) - 1, -1, -1):
        record = records[index]
        card = document.createElement("div")
        card.className = "archive-entry"
        if record["thumb"]:
            image = document.createElement("img")
            image.className = "archive-thumb"
            image.src = record["thumb"]
            image.alt = f"{sim.ERA_LABEL[record['era']]} era settlement"
            card.appendChild(image)
        text = document.createElement("div")
        text.className = "archive-text"
        for i, line in enumerate(archive.card_lines(record)):
            row = document.createElement("p")
            row.className = "archive-line archive-line--head" if i == 0 else "archive-line"
            row.innerText = line
            text.appendChild(row)
        stamp = document.createElement("p")
        stamp.className = "archive-line archive-date"
        stamp.innerText = f"Filed {record['saved_on']}"
        text.appendChild(stamp)
        card.appendChild(text)
        buttons = document.createElement("div")
        buttons.className = "archive-actions"
        _archive_button(buttons, f"archive-card-{index}-button", "Card", _make_card_handler(index))
        _archive_button(buttons, f"archive-delete-{index}-button", "Delete", _make_archive_delete_handler(index))
        card.appendChild(buttons)
        gallery.appendChild(card)
    panel.appendChild(gallery)
    if records:
        clear_wrap = document.createElement("div")
        clear_wrap.className = "archive-actions"
        _archive_button(
            clear_wrap,
            "archive-clear-button",
            "Really clear the whole archive?" if _archive_confirm_clear else "Clear archive",
            on_archive_clear,
        )
        panel.appendChild(clear_wrap)


# --- K15 founder's log + K29 time played --------------------------------
# Both ride in campaign.ui (already saved as a plain dict) and are
# validated/defaulted on every read, so an old or hand-edited save can
# never break the panel: bad shapes read as empty / zero.
FOUNDERS_NOTE_MAX = 200
FOUNDERS_LOG_MAX = 60
PLAY_GAP_CAP_SECONDS = 300.0
founders_log_open = False
_last_tick = time.time()


def founders_entries():
    raw = campaign.ui.get("founders_log")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[-FOUNDERS_LOG_MAX:]:
        if not isinstance(item, dict):
            continue
        note = item.get("note")
        era = item.get("era")
        season = item.get("season")
        if not isinstance(note, str) or not note.strip():
            continue
        if era not in sim.ERA_LABEL or isinstance(season, bool) or not isinstance(season, int) or season < 1:
            continue
        out.append({"era": era, "season": season, "note": note[:FOUNDERS_NOTE_MAX]})
    return out


def add_founders_note(text):
    """Append a personal annotation stamped with the current era/season."""
    if not isinstance(text, str) or not text.strip():
        return False
    entries = founders_entries()
    entries.append({"era": state.era, "season": int(state.season), "note": text.strip()[:FOUNDERS_NOTE_MAX]})
    campaign.ui["founders_log"] = entries[-FOUNDERS_LOG_MAX:]
    return True


def play_seconds():
    value = campaign.ui.get("play_seconds")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or value < 0:
        return 0.0
    return min(float(value), 1e9)


def _tick_play_time():
    """Accumulate active time between actions; long idle gaps are capped."""
    global _last_tick
    now = time.time()
    campaign.ui["play_seconds"] = play_seconds() + max(0.0, min(now - _last_tick, PLAY_GAP_CAP_SECONDS))
    _last_tick = now


def format_play_time(seconds):
    mins = int(seconds // 60)
    if mins < 60:
        return f"{mins} min"
    return f"{mins // 60} h {mins % 60} min"


def update_founders_panel():
    toggle = document.getElementById("founders-toggle-button")
    panel = document.getElementById("founders-panel")
    toggle.innerText = "Hide Founder's Log" if founders_log_open else "📓 Founder's Log"
    panel.hidden = not founders_log_open
    if not founders_log_open:
        return
    container = document.getElementById("founders-list")
    container.innerHTML = ""
    entries = founders_entries()
    if not entries:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "No entries yet. Note what you decided and why, as the founder."
        container.appendChild(empty)
    for entry in reversed(entries):
        year, season_name = year_and_season(entry["season"])
        row = document.createElement("p")
        row.className = "status-line founders-entry"
        row.innerText = f"Year {year}, {season_name} ({sim.ERA_LABEL[entry['era']]}): {entry['note']}"
        container.appendChild(row)


def on_toggle_founders(event=None):
    global founders_log_open
    founders_log_open = not founders_log_open
    update_founders_panel()


def on_add_founders_note(event=None):
    field = document.getElementById("founders-input")
    if add_founders_note(field.value):
        field.value = ""
        update_founders_panel()


# --- K5 council minutes -------------------------------------------------
minutes_open = False


def record_motion(kind, subject):
    minutes.record(campaign.ui, kind, subject, state.era, int(state.season))


def update_minutes_panel():
    toggle = document.getElementById("minutes-toggle-button")
    panel = document.getElementById("minutes-panel")
    toggle.innerText = "Hide Council Minutes" if minutes_open else "🏛️ Council Minutes"
    panel.hidden = not minutes_open
    if not minutes_open:
        return
    container = document.getElementById("minutes-list")
    container.innerHTML = ""
    entries = minutes.entries(campaign.ui)
    if not entries:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "No motions recorded yet. Research a discovery or raise a building and it will be minuted here."
        container.appendChild(empty)
    for entry in reversed(entries):
        year, season_name = year_and_season(entry["season"])
        row = document.createElement("p")
        row.className = "status-line minutes-entry"
        row.innerText = f"Year {year}, {season_name} ({sim.ERA_LABEL[entry['era']]}): {entry['text']}"
        container.appendChild(row)


def on_toggle_minutes(event=None):
    global minutes_open
    minutes_open = not minutes_open
    update_minutes_panel()


def on_toggle_summary_panel(event=None):
    global summary_panel_open
    summary_panel_open = not summary_panel_open
    update_summary_panel()


def _summary_stat_row(container, text):
    row = document.createElement("p")
    row.className = "status-line summary-line"
    row.innerText = text
    container.appendChild(row)


def update_summary_panel():
    toggle = document.getElementById("summary-toggle-button")
    panel = document.getElementById("summary-panel")
    toggle.innerText = "Hide Civilization Summary" if summary_panel_open else "📜 Civilization Summary"
    panel.hidden = not summary_panel_open
    if not summary_panel_open:
        return

    panel.innerHTML = ""
    data = summary.summary(campaign)

    # K7: in-character stakeholder-report framing, K17: efficiency rank.
    statement = document.createElement("p")
    statement.className = "row-blurb summary-statement"
    statement.innerText = summary.stakeholder_statement(data, data["rank"])
    panel.appendChild(statement)
    if data["rank"]:
        _summary_stat_row(panel, f"Efficiency rank: {data['rank']} city.")
    _summary_stat_row(
        panel,
        f"Furthest era reached: {data['furthest_era_label']} "
        f"({data['eras_completed']} of {data['eras_total']} eras completed).",
    )
    _summary_stat_row(panel, f"Total seasons played: {data['total_seasons']}.")
    _summary_stat_row(panel, f"Peak population ever reached: {data['peak_population']}.")
    if data["peak_score"] is not None:
        # Labeled against the settlement's *current* hard-mode setting --
        # score_history is just raw numbers with no per-entry hard-mode
        # flag of its own, so "what band was this historically" isn't a
        # question this data can answer; using the live setting is what
        # keeps this line consistent with every other score_label() call
        # on this same render (the sustainability panel, the era-by-era
        # rows below).
        _summary_stat_row(
            panel,
            f"Peak sustainability score: {data['peak_score']:.0f} / 100 "
            f"({sustainability.score_label(data['peak_score'], sustainability.is_hard_mode(state))}).",
        )
    if data["journey_complete"]:
        _summary_stat_row(panel, "This settlement has carried its story all the way to the Space Age.")
    if data["has_revisited"]:
        _summary_stat_row(panel, "You've looked back at least once during this playthrough.")
    _summary_stat_row(panel, f"Achievements earned: {len(achievement_ids_earned())} of {len(ACHIEVEMENTS)}.")

    heading = document.createElement("h3")
    heading.className = "summary-eras-heading"
    heading.innerText = "Era by era"
    panel.appendChild(heading)

    for row in data["eras"]:
        entry = document.createElement("div")
        entry.className = "summary-era-row" if row["completed"] else "summary-era-row summary-era-row--current"

        name = document.createElement("p")
        name.className = "summary-era-name"
        status_word = "completed" if row["completed"] else "in progress"
        name.innerText = f"{row['label']} — {status_word}"
        entry.appendChild(name)

        detail = document.createElement("p")
        detail.className = "summary-era-detail"
        score_text = f"{row['score']:.0f}/100 ({row['score_label']})" if row["score"] is not None else "—"
        detail.innerText = (
            f"Season {row['season_reached']} · Population {row['population']} · "
            f"Sustainability {score_text}"
        )
        entry.appendChild(detail)

        panel.appendChild(entry)

    _render_archive_section(panel)



# ===========================================================================
# K2/K8/K10/K21a small readouts, K11 civic challenges, K19/K13/K25 charts.
# All read-only views of state (challenge start/abandon aside), all inside
# collapsed panels or single status lines -- nothing here adds a screen.
# ===========================================================================
SEASONS_PER_YEAR = 4
SEASON_NAMES = ["Spring", "Summer", "Autumn", "Winter"]


def year_and_season(season):
    index = max(1, int(season)) - 1
    return index // SEASONS_PER_YEAR + 1, SEASON_NAMES[index % SEASONS_PER_YEAR]


# ===========================================================================
# K1/K24/K28: the optional City Views panel (dashboard, civic map, flow
# diagram). Session-only display state, never saved; built by views.py.
# ===========================================================================
views_panel_open = False
views_tab = "dashboard"
VIEW_TABS = ("dashboard", "map", "flow")


def on_toggle_views(event=None):
    global views_panel_open
    views_panel_open = not views_panel_open
    update_views_panel(current_effects())


def _make_views_tab_handler(tab):
    def handler(event=None):
        global views_tab
        views_tab = tab
        update_views_panel(current_effects())
    return handler


def update_views_panel(effects=None):
    toggle = document.getElementById("views-toggle-button")
    panel = document.getElementById("views-panel")
    toggle.innerText = "Hide City Views" if views_panel_open else "📊 City Views"
    panel.hidden = not views_panel_open
    if not views_panel_open:
        return
    effects = current_effects() if effects is None else effects
    for tab in VIEW_TABS:
        document.getElementById(f"views-tab-{tab}-button").setAttribute(
            "aria-pressed", "true" if tab == views_tab else "false"
        )
        document.getElementById(f"views-{tab}").hidden = tab != views_tab
    if views_tab == "dashboard":
        container = document.getElementById("views-dashboard")
        container.innerHTML = ""
        done, total, _percent = tree_completion()
        for section in views.dashboard(state, effects, (done, total)):
            block = document.createElement("div")
            block.className = "views-dash-section"
            heading = document.createElement("h3")
            heading.className = "summary-eras-heading"
            heading.innerText = section["title"]
            block.appendChild(heading)
            for label, value in section["rows"]:
                row = document.createElement("p")
                row.className = "views-dash-row"
                name = document.createElement("span")
                name.innerText = label
                number = document.createElement("span")
                number.className = "views-dash-value"
                number.innerText = value
                row.appendChild(name)
                row.appendChild(number)
                block.appendChild(row)
            container.appendChild(block)
    elif views_tab == "map":
        document.getElementById("views-map-svg").innerHTML = views.civic_map_svg(state)
        document.getElementById("views-map-caption").innerText = views.map_caption(state)
    else:
        document.getElementById("views-flow-svg").innerHTML = views.flow_svg(state, state.last_report)
        document.getElementById("views-flow-caption").innerText = views.flow_caption(state.last_report)


def tree_completion():
    """K21a: (researched, total, percent) over the whole tree."""
    total = len(tree.nodes)
    done = len(tree.researched)
    return done, total, (100 * done // total if total else 0)


_challenge_button_proxies = {}


def _make_start_challenge_handler(cid):
    def handler(event=None):
        if campaign.revisiting is not None:
            return
        if challenges.start(state, current_effects(), cid):
            render()
    return handler


def on_abandon_challenge(event=None):
    if challenges.abandon(state):
        render()


def render_insights(effects):
    year, season_name = year_and_season(state.season)
    document.getElementById("founded-display").innerText = (
        f"Founded Year 1 · now Year {year}, {season_name}"
    )
    index = trajectory.current_output_index(state)
    document.getElementById("efficiency-display").innerText = (
        "Output per person: -" if index is None else f"Output per person: {index:.1f}x subsistence"
    )
    document.getElementById("calm-streak-display").innerText = (
        f"Calm seasons in a row: {state.calm_streak}"
    )
    document.getElementById("play-time-display").innerText = f"Time played: {format_play_time(play_seconds())}"
    done, total, percent = tree_completion()
    document.getElementById("research-completion-display").innerText = (
        f"Tree: {done} of {total} discoveries ({percent}%)"
    )

    # --- K11 civic challenges -------------------------------------------
    active_line = challenges.status_text(state)
    document.getElementById("challenges-summary").innerText = (
        "Civic Challenges (1 active)" if active_line else "Civic Challenges (optional)"
    )
    status = document.getElementById("challenge-status-display")
    status.innerText = active_line or f"Challenges met: {challenges.total_completed(state)}"
    container = document.getElementById("challenge-list")
    container.innerHTML = ""
    live = set()
    if active_line:
        row = document.createElement("div")
        row.className = "row challenge-row"
        button = document.createElement("button")
        button.id = "challenge-abandon-button"
        button.className = "secondary"
        button.innerText = "Abandon challenge"
        proxy = create_proxy(on_abandon_challenge)
        stale = _challenge_button_proxies.get("abandon")
        if stale is not None:
            stale.destroy()
        _challenge_button_proxies["abandon"] = proxy
        live.add("abandon")
        button.addEventListener("click", proxy)
        row.appendChild(button)
        container.appendChild(row)
    elif campaign.revisiting is None:
        for cid in challenges.offered(state, effects):
            spec = challenges.CHALLENGES[cid]
            row = document.createElement("div")
            row.className = "row challenge-row"
            top = document.createElement("div")
            top.className = "row-top"
            name = document.createElement("span")
            name.className = "row-name"
            name.innerText = f"{spec['label']} ({spec['seasons']} seasons)"
            top.appendChild(name)
            row.appendChild(top)
            blurb = document.createElement("p")
            blurb.className = "row-blurb"
            blurb.innerText = (
                f"{spec['blurb']} Reward: +{challenges.reward_for(state.era):.0f} knowledge."
            )
            row.appendChild(blurb)
            actions = document.createElement("div")
            actions.className = "row-actions"
            button = document.createElement("button")
            button.id = f"challenge-start-{cid}-button"
            button.className = "secondary"
            button.innerText = "Accept"
            proxy = create_proxy(_make_start_challenge_handler(cid))
            stale = _challenge_button_proxies.get(cid)
            if stale is not None:
                stale.destroy()
            _challenge_button_proxies[cid] = proxy
            live.add(cid)
            button.addEventListener("click", proxy)
            actions.appendChild(button)
            row.appendChild(actions)
            container.appendChild(row)
    for key in list(_challenge_button_proxies):
        if key not in live:
            _challenge_button_proxies.pop(key).destroy()

    # --- K19/K13/K25 charts ---------------------------------------------
    points = state.trajectory
    document.getElementById("trajectory-graph").innerHTML = trajectory.trajectory_svg(points)
    document.getElementById("livability-scatter").innerHTML = trajectory.scatter_svg(points)
    document.getElementById("trajectory-summary").innerText = trajectory.summary_line(points)
    document.getElementById("trajectory-source").innerText = trajectory.SOURCE_NOTE


# Work/Build row buttons, keyed by (role-or-building, "add"/"remove"/
# "build"). Milestone 8 made these panels dynamic (built from
# sim.roles_for_era()/buildings_for_era() every render, same reason
# render_research() already is: a second era's roster can't be static
# markup) — which means they need the exact same "destroy the proxy this
# render is replacing" discipline render_research() already established,
# or Farmers/Farmland's buttons would leak a Pyodide proxy every render
# the same way an un-destroyed research proxy would.
_work_button_proxies = {}
_building_button_proxies = {}


def render_work():
    """The Work panel, rebuilt from `sim.roles_for_era(state.era)` every
    render — Tribal's four roles never disappear, a later era's roles are
    simply appended once reached (see sim.py's ERA_ROLES)."""
    idle = state.idle_workers()
    document.getElementById("idle-display").innerText = f"Unassigned: {idle}"

    container = document.getElementById("work-list")
    container.innerHTML = ""

    roles = sim.roles_for_era(state.era)
    live_roles = set(roles)
    for role in roles:
        row = document.createElement("div")
        row.className = "row"

        top = document.createElement("div")
        top.className = "row-top"
        # Emoji stays decoration, not data (matches the original static
        # markup's structure): a plain-text prefix on the outer span, with
        # the `{role}-name` id on an inner span holding just the label, so
        # anything reading that id's innerText (rendering, tests) still
        # gets the label alone.
        name = document.createElement("span")
        name.className = "row-name"
        name.innerText = f"{sim.ROLE_EMOJI[role]} "
        name_label = document.createElement("span")
        name_label.id = f"{role}-name"
        name_label.innerText = sim.ROLE_LABEL[role]
        name.appendChild(name_label)
        count = document.createElement("span")
        count.className = "row-count"
        count.id = f"{role}-count"
        count.innerText = str(state.allocation[role])
        top.appendChild(name)
        top.appendChild(count)
        row.appendChild(top)

        blurb = document.createElement("p")
        blurb.className = "row-blurb"
        blurb.id = f"{role}-blurb"
        blurb.innerText = sim.ROLE_BLURB[role]
        row.appendChild(blurb)

        actions = document.createElement("div")
        actions.className = "row-actions"

        remove_button = document.createElement("button")
        remove_button.id = f"{role}-remove-button"
        remove_button.className = "secondary"
        remove_button.innerText = "−"
        remove_button.disabled = state.allocation[role] <= 0
        remove_proxy = create_proxy(_make_unassign_handler(role))
        stale = _work_button_proxies.get((role, "remove"))
        if stale is not None:
            stale.destroy()
        _work_button_proxies[(role, "remove")] = remove_proxy
        remove_button.addEventListener("click", remove_proxy)
        actions.appendChild(remove_button)

        add_button = document.createElement("button")
        add_button.id = f"{role}-add-button"
        add_button.className = "secondary"
        add_button.innerText = "+"
        add_button.disabled = idle <= 0
        add_proxy = create_proxy(_make_assign_handler(role))
        stale = _work_button_proxies.get((role, "add"))
        if stale is not None:
            stale.destroy()
        _work_button_proxies[(role, "add")] = add_proxy
        add_button.addEventListener("click", add_proxy)
        actions.appendChild(add_button)

        row.appendChild(actions)
        container.appendChild(row)

    for key in list(_work_button_proxies):
        if key[0] not in live_roles:
            _work_button_proxies.pop(key).destroy()


def render_buildings():
    """The Build panel, rebuilt from `sim.buildings_for_era(state.era)`
    every render — same reasoning as render_work() above."""
    container = document.getElementById("buildings-list")
    container.innerHTML = ""

    buildings = sim.buildings_for_era(state.era)
    live_buildings = set(buildings)
    for building in buildings:
        row = document.createElement("div")
        row.className = "row"

        top = document.createElement("div")
        top.className = "row-top"
        name = document.createElement("span")
        name.className = "row-name"
        name.innerText = f"{sim.BUILDING_EMOJI[building]} "
        name_label = document.createElement("span")
        name_label.id = f"{building}-name"
        name_label.innerText = sim.BUILDING_LABEL[building]
        name.appendChild(name_label)
        count = document.createElement("span")
        count.className = "row-count"
        count.id = f"{building}-count"
        count.innerText = str(state.buildings[building])
        top.appendChild(name)
        top.appendChild(count)
        row.appendChild(top)

        blurb = document.createElement("p")
        blurb.className = "row-blurb"
        blurb.id = f"{building}-blurb"
        blurb.innerText = sim.BUILDING_BLURB[building]
        row.appendChild(blurb)

        actions = document.createElement("div")
        actions.className = "row-actions"
        button = document.createElement("button")
        button.id = f"{building}-build-button"
        button.className = "secondary"
        button.innerText = f"Build ({sim.BUILDING_COST[building]:.0f})"
        button.disabled = not state.can_build(building)
        proxy = create_proxy(_make_build_handler(building))
        stale = _building_button_proxies.get(building)
        if stale is not None:
            stale.destroy()
        _building_button_proxies[building] = proxy
        button.addEventListener("click", proxy)
        actions.appendChild(button)
        row.appendChild(actions)

        container.appendChild(row)

    for building in list(_building_button_proxies):
        if building not in live_buildings:
            _building_button_proxies.pop(building).destroy()


def render_era_progress(effects):
    """Milestone 7/8: shows whether the settlement is ready to leave its
    current era, and why not if it isn't — the same "doubles as the UI
    explanation and what tests assert against" pattern research.py's own
    locked-node reasons already use. The button only ever calls
    transition.attempt_transition(), which itself refuses cleanly if
    anything has changed between render and click (e.g. a revisit started
    in another tab of the same session)."""
    next_era = transition.next_era_for(state.era)
    button = document.getElementById("advance-era-button")
    status = document.getElementById("era-progress-status-display")
    reasons_el = document.getElementById("era-progress-reasons-display")

    if next_era is None:
        status.innerText = "Nothing more to reach from here yet."
        reasons_el.innerText = ""
        button.innerText = "—"
        button.disabled = True
        return

    ready = transition.transition_ready(state, tree, effects)
    status.innerText = (
        f"Ready to move into the {sim.ERA_LABEL[next_era]} era."
        if ready
        else f"Working toward the {sim.ERA_LABEL[next_era]} era."
    )
    reasons_el.innerText = " ".join(transition.missing_requirements(state, tree, effects))
    button.innerText = f"Advance to {sim.ERA_LABEL[next_era]}"
    button.disabled = not ready


def on_advance_era(event=None):
    if transition.attempt_transition(campaign):
        record_motion("era", sim.ERA_LABEL[state.era] + " era")
        update_minutes_panel()
        render()
        _check_new_achievements_for_toast()


# --- "look back" at a completed era (Milestone 15 / K7) -----------------
# The save schema (save.py's Campaign.enter_revisit()/exit_revisit()) has
# supported this since Milestone 4, and it has been fully tested since —
# but no button anywhere ever called it: there was no revisit UI at all
# before this milestone. This section is that missing UI. It needs no new
# state-to-visual plumbing: get_visual_state() already reads directly off
# `state`, and enter_revisit()/exit_revisit() mutate `state` in place (the
# same object game.py's module-level `state` name points at), so the
# moment a revisit is entered here, the existing Three.js render layer
# (render3d.js, via _notify_visual_layer() at the end of render()) redraws
# the revisited era's own scene automatically — the K7 ask was really "the
# UI to reach this", not a rendering gap.
_revisit_button_proxies = {}


def render_revisit():
    """The Look Back panel — rebuilt every render(), the same reason every
    other dynamic panel in this file is: the list of revisitable eras grows
    over a playthrough and can't be static markup."""
    status = document.getElementById("revisit-status-display")
    container = document.getElementById("revisit-era-list")
    exit_button = document.getElementById("exit-revisit-button")
    banner = document.getElementById("revisit-active-banner")

    if campaign.revisiting is not None:
        era_label = sim.ERA_LABEL[campaign.revisiting]
        status.innerText = f"Looking back at the {era_label} era, exactly as it stood when you left it."
        banner.innerText = (
            f"You're looking back at the {era_label} era — nothing you do here "
            "affects your forward progress."
        )
        banner.hidden = False
        exit_button.hidden = False
    else:
        banner.hidden = True
        exit_button.hidden = True
        revisitable = campaign.revisitable_eras()
        status.innerText = (
            "No completed eras to look back on yet — finish your first era transition."
            if not revisitable
            else "Completed eras you can look back on:"
        )

    container.innerHTML = ""
    live_eras = set()
    if campaign.revisiting is None:
        for era in campaign.revisitable_eras():
            live_eras.add(era)
            row = document.createElement("div")
            row.className = "row"

            top = document.createElement("div")
            top.className = "row-top"
            name = document.createElement("span")
            name.className = "row-name"
            name.innerText = sim.ERA_LABEL[era]
            top.appendChild(name)
            row.appendChild(top)

            actions = document.createElement("div")
            actions.className = "row-actions"
            button = document.createElement("button")
            button.id = f"revisit-{era}-button"
            button.className = "secondary"
            button.innerText = "View"
            proxy = create_proxy(_make_enter_revisit_handler(era))
            stale = _revisit_button_proxies.get(era)
            if stale is not None:
                stale.destroy()
            _revisit_button_proxies[era] = proxy
            button.addEventListener("click", proxy)
            actions.appendChild(button)
            row.appendChild(actions)

            container.appendChild(row)

    for era in list(_revisit_button_proxies):
        if era not in live_eras:
            _revisit_button_proxies.pop(era).destroy()


def _make_enter_revisit_handler(era):
    def handler(event=None):
        if campaign.enter_revisit(era):
            render()
            _check_new_achievements_for_toast()
    return handler


def on_exit_revisit(event=None):
    if campaign.exit_revisit():
        render()


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration exactly. See CLAUDE.md's Milestone 15 build notes for the
# full catalog-design reasoning.
# ===========================================================================
#
# "Derive, don't track" holds for every entry here: every achievement is a
# pure function of state this game already persists (era progress via
# campaign.furthest_era, the full score_history, the research tree's own
# researched list, and the season loop's own last_report ratios) — no new
# tracked state was needed except `campaign.has_revisited` (save.py), added
# via the same five-step defensive pattern SOL's own visited_bodies used
# (safe default, mutated only at the real event, saved, defensive fallback
# on load, no backfill needed here since no pre-existing save could already
# be "mid-revisit but the flag says no").
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()`/Le Champ
    de Mots' `_read_json_asset()`: the boot script fetches achievements.json
    and hands it to Python as a window global before this file runs; the
    pytest harness's fake `js` module has no such attribute, so this falls
    through to reading the file straight off disk."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per SOL's own note: achievements are additive, not core
# gameplay, so a boot-script regression here degrades to "no achievements
# catalog" rather than taking down the whole module import.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

# Branch-depth threshold for the three "Tradition" achievements — roughly
# half of any one branch's ~14-16 nodes (see CLAUDE.md), deep enough to
# mean real, sustained investment in one branch rather than a few early
# freebies.
BRANCH_SPECIALIST_THRESHOLD = 8
EQUITY_CHAMPION_MIN_POPULATION = 25
A_REAL_CITY_POPULATION = 100
# sustainability.components() returns each component on a 0..1 scale, NOT
# the 0..100 scale evaluate()/the UI display (evaluate() multiplies by 100
# for the headline readout) -- a real bug caught by this milestone's own
# test suite before it shipped (both thresholds below were first written as
# 90/85, which no settlement could ever satisfy). Named here, once, so a
# future edit can't reintroduce the same off-by-100 mistake by hand.
EQUITY_CHAMPION_MIN_EQUITY = 0.90
BUILT_TO_LAST_MIN_RESILIENCE = 0.85


def _ever_thriving():
    if state.peak_score is not None and state.peak_score >= 85:
        return True
    return sustainability.score(state, current_effects()) >= 85


def _ever_recovered_from_collapse():
    """True if the score ever fell into Collapsing (<30) and later, at some
    later point in the same history, recovered to Steady or better (>=70).

    Reads state.ever_recovered_from_collapse, a sticky flag CityState.
    record_score() maintains incrementally as each season's score comes in
    — not a scan over score_history itself, which is now capped (Z25) and
    so is no longer guaranteed to hold the whole lifetime history."""
    return state.ever_recovered_from_collapse


def _era_reached(era):
    # K22: eras a consulting case starts in (or before) were inherited, not
    # reached, so they do not count towards the "reached era" achievements.
    case = consulting.get(campaign.ui)
    if case is not None and sim.era_index(era) <= sim.era_index(consulting.CASES[case["case"]]["era"]):
        return False
    return sim.era_index(campaign.furthest_era) >= sim.era_index(era)


def _earned_affinity(branch):
    """Researched nodes in a branch, not counting any a consulting case inherited (K22)."""
    inherited = set(consulting.inherited_for(campaign))
    return sum(1 for n in tree.researched if n not in inherited and tree.nodes[n].branch == branch)


def _full_coordination():
    report = state.last_report or {}
    return report.get("canals", 0) > 0 and report.get("canal_staffing_ratio", 0.0) >= 1.0


def _nobody_exposed():
    report = state.last_report or {}
    return report.get("public_works", 0) > 0 and report.get("public_works_coverage_ratio", 0.0) >= 1.0


def _well_designed_rings():
    report = state.last_report or {}
    return report.get("habitat_rings", 0) > 0 and report.get("habitat_layout_ratio", 0.0) >= 1.0


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is cached or hand-flagged, matching SOL's own discipline.
ACHIEVEMENT_CHECKS = {
    "reached_agrarian": lambda: _era_reached("agrarian"),
    "reached_classical": lambda: _era_reached("classical"),
    "reached_medieval": lambda: _era_reached("medieval"),
    "reached_industrial": lambda: _era_reached("industrial"),
    "reached_digital": lambda: _era_reached("digital"),
    "reached_space": lambda: _era_reached("space"),
    "thriving_once": _ever_thriving,
    "phoenix_settlement": _ever_recovered_from_collapse,
    "provision_specialist": lambda: _earned_affinity("provision") >= BRANCH_SPECIALIST_THRESHOLD,
    "community_specialist": lambda: _earned_affinity("community") >= BRANCH_SPECIALIST_THRESHOLD,
    "craft_specialist": lambda: _earned_affinity("craft") >= BRANCH_SPECIALIST_THRESHOLD,
    "root_and_branch": lambda: len(tree.researched) >= len(tree.nodes),
    "equity_champion": lambda: (
        state.population >= EQUITY_CHAMPION_MIN_POPULATION
        and sustainability.components(state, current_effects())["equity"] >= EQUITY_CHAMPION_MIN_EQUITY
    ),
    "built_to_last": lambda: (
        sustainability.components(state, current_effects())["resilience"] >= BUILT_TO_LAST_MIN_RESILIENCE
    ),
    "full_coordination": _full_coordination,
    "nobody_exposed": _nobody_exposed,
    "well_designed_rings": _well_designed_rings,
    "a_real_city": lambda: state.population >= A_REAL_CITY_POPULATION,
    "looking_back": lambda: campaign.has_revisited,
}

# Progress readouts, only for achievements with a natural numeric scale-up —
# a plain earned/not-yet is the honest shape for the rest (era-reached,
# phoenix, the coordination/coverage achievements are all one-shot).
ACHIEVEMENT_PROGRESS = {
    "provision_specialist": lambda: (_earned_affinity("provision"), BRANCH_SPECIALIST_THRESHOLD),
    "community_specialist": lambda: (_earned_affinity("community"), BRANCH_SPECIALIST_THRESHOLD),
    "craft_specialist": lambda: (_earned_affinity("craft"), BRANCH_SPECIALIST_THRESHOLD),
    "root_and_branch": lambda: (len(tree.researched), len(tree.nodes)),
    "a_real_city": lambda: (state.population, A_REAL_CITY_POPULATION),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input (see get_state() below)."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each annotated with earned status and
    (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        card.dataset.achievementId = entry["id"]

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # Hub-dashboard link (ACHIEVEMENTS-SYSTEM-DESIGN.md §5) — signed-in
    # players can see Continuum's progress alongside every other game's
    # there. Relative path, no leading "/" (site-level milestone 7's
    # GitHub Pages subpath fix), rebuilt each open since the panel is
    # cleared first.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


# --- unlock toast ---------------------------------------------------------
# A snapshot of which achievement ids were already earned as of the last
# seed point, so an action handler's post-render check can tell "newly
# earned by that action" apart from "already earned before this page/save
# load" and only toast for the former. Seeded (never diffed against empty)
# by setup() and load_state() — never by render() itself, since render() is
# also what setup()/load_state() call before seeding — so a save that
# already has several achievements earned never floods the player with a
# toast per achievement the instant it loads.
_achievements_seen_ids = set()


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


def _display_toast(message):
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


def _check_new_achievements_for_toast():
    """Called after render() from every action handler that could plausibly
    newly earn an achievement (assign/unassign/build/research/season
    advance/era transition/enter revisit) — never from render() itself, for
    the same reason _seed_achievement_toast_baseline() above exists."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


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

changelog_open = False


def on_toggle_changelog(event=None):
    global changelog_open
    changelog_open = not changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if changelog_open else "📋 What's New"
    panel.hidden = not changelog_open
    if not changelog_open:
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
    info_page.render(info_content.era_info_page(state.era), info_page_open)
    _render_info_page_report()


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
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

# Session-only, like every report_sent flag in champ-de-mots — never rides
# get_state()/load_state(). _info_page_report_era tracks which era the
# "already sent" state applies to, so switching eras (or revisiting an
# earlier one via Look Back) reopens the report rather than permanently
# disabling the button after the first-ever report of a session.
info_page_report_sent = False
_info_page_report_era = None


def _info_page_report_payload():
    """The payload for the era currently shown in the info panel, or None
    if there's nothing worth reporting — an era with no real content yet
    (the _PENDING placeholder) has no sources, and flagging placeholder
    framing text as "wrong" would tell a human triager nothing useful."""
    content = info_content.era_info_page(state.era)
    sources = content.get("sources") or []
    if not sources:
        return None
    return {
        "game_id": "continuum",
        "item_id": f"info-{state.era}",
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
    global info_page_report_sent, _info_page_report_era

    if info_page_report_sent and _info_page_report_era == state.era:
        return None
    payload = _info_page_report_payload()
    if payload is None:
        return None
    info_page_report_sent = True
    _info_page_report_era = state.era
    _dispatch_info_page_report(payload)
    render_info_page()
    return payload


def _render_info_page_report():
    """Visibility/label for the report button — only shown while the panel
    is open and the current era actually has real sources to flag."""
    button = document.getElementById("info-page-report-button")
    if not info_page_open or _info_page_report_payload() is None:
        button.hidden = True
        return
    already_sent = info_page_report_sent and _info_page_report_era == state.era
    button.hidden = False
    button.disabled = already_sent
    button.innerText = INFO_PAGE_REPORT_SENT_LABEL if already_sent else INFO_PAGE_REPORT_BUTTON_LABEL


# Rendered entries, newest first, capped independently of how many
# Chronicle keeps for the save file (`log.MAX_ENTRIES`) so a long session
# doesn't grow the DOM without bound.
LOG_VISIBLE_ENTRIES = 20

# Phase 5 colorblind-safety audit: log.py's "livability-up"/"livability-
# down" kinds used to be told apart only by their .log-row--* border color
# (see style.css) — a plain green/red pair, which is exactly the hue
# distinction deuteranopia/protanopia can't reliably make. This icon
# prefix is a second, color-independent signal for the same distinction,
# the same "decoration, not data" role sim.ROLE_EMOJI already plays for
# the Work panel. Every other kind is left unprefixed (research/population/
# transition already read unambiguously from their own text).
LOG_KIND_ICON = {
    "livability-up": "▲ ",
    "livability-down": "▼ ",
}


def _build_log_row(entry):
    """One log row's DOM, handed to `narrative_log.render()` as its
    `build_row` callback (Z11) — byte-identical markup to what render_log()
    used to build inline, just factored out so the shared module can own
    the surrounding cap/empty-state/count loop instead of this game
    repeating it."""
    row = document.createElement("div")
    row.className = f"row log-row log-row--{entry.kind}"

    top = document.createElement("div")
    top.className = "row-top"
    tag = document.createElement("span")
    tag.className = "row-name"
    icon = LOG_KIND_ICON.get(entry.kind, "")
    tag.innerText = f"{icon}{sim.ERA_LABEL.get(entry.era, entry.era)} · Season {entry.season}"
    top.appendChild(tag)
    row.appendChild(top)

    text = document.createElement("p")
    text.className = "row-blurb"
    text.innerText = entry.text
    row.appendChild(text)

    return row


def render_log():
    """The ongoing log (Milestone 6) — lightweight, skippable flavor text
    triggered by research unlocks, population thresholds, and livability
    shifts (which double as this game's diegetic feedback, per the design
    doc's Core system 4 — see log.py). Always visible, never a popup;
    rebuilt from `chronicle.entries` the same way render_research() rebuilds
    the research panel from the tree, for the same reason: a session's
    worth of rows can't be static markup.

    Z11: delegates the cap/empty-state/count-label loop to
    `narrative_log.render()` — this game's own reference integration for
    that shared component. Same player-visible behavior as before the
    migration (same 20-row cap, same newest-first order, same markup).
    """
    narrative_log.render(
        "log-list",
        chronicle.entries,
        _build_log_row,
        empty_text="Nothing to report yet.",
        max_visible=LOG_VISIBLE_ENTRIES,
        count_element_id="log-status-display",
        count_text=f"{len(chronicle.entries)} entries",
    )


def render_sustainability(effects):
    """The score panel — visible from season 1 of the first era, by design."""
    reading = sustainability.evaluate(state, effects)
    value = reading["score"]

    document.getElementById("score-display").innerText = (
        f"Sustainability: {value:.0f} / 100 — "
        f"{sustainability.score_label(value, sustainability.is_hard_mode(state))}"
    )
    document.getElementById("score-bar").style.width = f"{value:.0f}%"

    weakest = sustainability.weakest_component(state, effects)
    for component in sustainability.COMPONENTS:
        element = document.getElementById(f"{component}-display")
        element.innerText = (
            f"{sustainability.COMPONENT_LABEL[component]}: "
            f"{reading['components'][component]:.0f}"
        )
        element.className = (
            "component-line component-line--weakest"
            if component == weakest
            else "component-line"
        )

    document.getElementById("score-note-display").innerText = sustainability.score_note(
        state, effects
    )


# Study-button click handlers, keyed by node_id. render_research() rebuilds
# every row (and mints a fresh create_proxy() for every unresearched node)
# on every render; a Pyodide proxy isn't garbage-collected on its own, so
# without tracking the previous render's proxy here and destroying it before
# its replacement is created, they'd accumulate unboundedly for the life of
# the page — a real, slow memory leak over a play session.
_research_button_proxies = {}


def render_research():
    """The research panel, rebuilt from the tree each render.

    Node rows are built in code rather than written into index.html: the
    tree runs to fourteen tiers across seven eras, so static markup for it
    would be unmaintainable long before the Space Age. Locked nodes are
    listed too, with the reason they're locked — a tree the player can't
    see the shape of isn't a tree.
    """
    document.getElementById("research-status-display").innerText = (
        f"Knowledge: {state.resources['knowledge']:.1f} — "
        f"{len(tree.researched)} discoveries made"
    )

    # UI decluttering: only nodes the player can act on right now live in
    # the always-visible list; locked and already-known nodes sit in two
    # collapsed disclosures below it, which stay rebuilt every render.
    open_container = document.getElementById("research-list")
    locked_container = document.getElementById("research-locked-list")
    known_container = document.getElementById("research-known-list")
    open_container.innerHTML = ""
    locked_container.innerHTML = ""
    known_container.innerHTML = ""
    n_locked = n_known = 0

    query = research_search_query.strip().lower()
    live_node_ids = set()
    any_rendered = False
    for node in tree.visible_nodes():
        if query and not _research_node_matches(node, query):
            continue
        if research_branch_filter and node.branch not in research_branch_filter:
            continue
        any_rendered = True
        researched = tree.is_researched(node.node_id)
        available = tree.is_available(node.node_id)

        row = document.createElement("div")
        row.className = "row research-row"
        if researched:
            row.className = "row research-row research-row--done"
        elif not available:
            row.className = "row research-row research-row--locked"

        top = document.createElement("div")
        top.className = "row-top"
        name = document.createElement("span")
        name.className = "row-name"
        name.innerText = ("✓ " if researched else "") + node.name
        cost = document.createElement("span")
        cost.className = "row-count"
        cost.innerText = "—" if researched else f"{node.cost:.0f}"
        top.appendChild(name)
        top.appendChild(cost)
        row.appendChild(top)

        meta = document.createElement("p")
        meta.className = "research-meta"
        meta.innerText = f"{research.BRANCH_LABEL[node.branch]} · Tier {node.tier}"
        row.appendChild(meta)

        blurb = document.createElement("p")
        blurb.className = "row-blurb"
        blurb.innerText = node.blurb
        row.appendChild(blurb)

        # K12: the exact numeric effect, on the row and as a tooltip.
        effect_text = research.describe_effects(node)
        row.title = f"Effect: {effect_text}"
        effect_line = document.createElement("p")
        effect_line.className = "research-effect"
        effect_line.innerText = f"Effect: {effect_text}"
        row.appendChild(effect_line)

        if not researched and not available:
            reasons = document.createElement("p")
            reasons.className = "research-locked-reason"
            reasons.innerText = " ".join(tree.missing_requirements(node.node_id))
            row.appendChild(reasons)
            # K23: a rough knowledge estimate when the tier gate is the blocker.
            estimate = research.unlock_estimate(tree, node.node_id)
            if estimate is not None:
                reasons.innerText += f" Roughly {estimate:.0f} knowledge to open and study this."

        actions = document.createElement("div")
        actions.className = "row-actions"
        button = document.createElement("button")
        button.id = f"research-{node.node_id}"
        button.className = "secondary"
        if researched:
            button.innerText = "Known"
            button.disabled = True
        else:
            button.innerText = f"Study ({node.cost:.0f})"
            button.disabled = not (available and tree.can_afford(node.node_id, state.resources))
            live_node_ids.add(node.node_id)
            proxy = create_proxy(_make_research_handler(node.node_id))
            stale = _research_button_proxies.get(node.node_id)
            if stale is not None:
                stale.destroy()
            _research_button_proxies[node.node_id] = proxy
            button.addEventListener("click", proxy)
        actions.appendChild(button)
        row.appendChild(actions)

        if researched:
            known_container.appendChild(row)
            n_known += 1
        elif not available:
            locked_container.appendChild(row)
            n_locked += 1
        else:
            open_container.appendChild(row)

    _update_research_disclosures(query, n_locked, n_known)

    container = open_container
    if query and not any_rendered:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = f'No research nodes match "{research_search_query.strip()}".'
        container.appendChild(empty)

    # Nodes that no longer need a Study button this render (just researched,
    # no longer visible, or filtered out by the search box) still have
    # their old proxy sitting in the tracking dict — destroy and drop it
    # rather than leaking it forever. A filtered-out node is deliberately
    # never given a fresh proxy in the loop above, so it can't leak a live
    # listener behind an invisible row either.
    for node_id in list(_research_button_proxies):
        if node_id not in live_node_ids:
            _research_button_proxies.pop(node_id).destroy()


def _update_research_disclosures(query, n_locked, n_known):
    """Labels the two collapsed research disclosures with live counts, and
    (only while a search is active) opens any that hold a match so a
    search result is never hidden behind a closed toggle."""
    for prefix, count, noun in (
        ("research-locked", n_locked, "Locked"),
        ("research-known", n_known, "Known discoveries"),
    ):
        details = document.getElementById(f"{prefix}-details")
        document.getElementById(f"{prefix}-summary").innerText = f"{noun} ({count})"
        details.hidden = count == 0
        if query and count:
            details.open = True


def _research_node_matches(node, query):
    """K14 — the research tree search/filter. Matches against the node's
    name, blurb, and branch label, case-insensitively; `query` is already
    lower-cased and stripped by the caller."""
    haystack = f"{node.name} {node.blurb} {research.BRANCH_LABEL[node.branch]}".lower()
    return query in haystack


# --- handlers ----------------------------------------------------------
def _make_assign_handler(role):
    def handler(event=None):
        state.assign_worker(role)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_unassign_handler(role):
    def handler(event=None):
        state.unassign_worker(role)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_build_handler(building):
    def handler(event=None):
        if state.build(building):
            record_motion("build", sim.BUILDING_LABEL[building])
        update_minutes_panel()
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_research_handler(node_id):
    def handler(event=None):
        if tree.research(node_id, state.resources):
            record_motion("research", tree.nodes[node_id].name)
        update_minutes_panel()
        chronicle.check_research(state, tree)
        render()
        _check_new_achievements_for_toast()
    return handler


# ===========================================================================
# U1: tick-based play. Seasons now pass on their own instead of waiting for an
# Advance Season button (which is gone). The pace is real time: a season takes
# SEASON_SECONDS[era] seconds at 1x (slower in later eras, which have more to
# weigh), divided by the chosen speed. Deliberately conservative:
#   - a settlement (and every load) starts PAUSED, so nothing happens before
#     you have read anything; speed is never saved;
#   - the clock only runs while the page is open and visible (index.html's
#     ticker skips hidden tabs and clamps each step), so nothing piles up
#     while you are away, matching the hub's no-idle-timer stance;
#   - it never runs during a Look Back (a revisit is a frozen view).
# `on_advance_season()` remains the one place a season actually happens.
# ===========================================================================
SEASON_SECONDS = {
    "tribal": 10.0, "agrarian": 10.0, "classical": 12.0, "medieval": 12.0,
    "industrial": 14.0, "digital": 16.0, "space": 18.0,
}
SPEEDS = (0, 1, 2, 4)
MAX_SEASONS_PER_TICK = 2  # a stalled frame must never fire a burst of seasons

sim_speed = 0
season_progress = 0.0  # real seconds banked toward the next season, at 1x


def season_length():
    return SEASON_SECONDS.get(state.era, 10.0)


def set_speed(speed):
    global sim_speed
    if speed not in SPEEDS:
        return False
    sim_speed = speed
    render_clock()
    return True


def tick_clock(dt):
    """Advances the clock by `dt` real seconds. Returns how many seasons
    passed (0 while paused, in a Look Back, or for a bad `dt`)."""
    global season_progress
    if sim_speed == 0 or campaign.revisiting:
        return 0
    if not isinstance(dt, (int, float)) or isinstance(dt, bool) or dt != dt or dt <= 0:
        return 0
    season_progress += min(float(dt), 1.0) * sim_speed
    passed = 0
    while season_progress >= season_length() and passed < MAX_SEASONS_PER_TICK:
        season_progress -= season_length()
        on_advance_season()
        passed += 1
    if passed == MAX_SEASONS_PER_TICK and season_progress >= season_length():
        season_progress = 0.0
    render_clock()
    return passed


def render_clock():
    labels = {0: "pause", 1: "1x", 2: "2x", 4: "4x"}
    for speed, key in labels.items():
        button = document.getElementById(f"speed-{key}-button")
        active = speed == sim_speed
        if active:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")
        button.setAttribute("aria-pressed", "true" if active else "false")
    fraction = min(1.0, season_progress / season_length())
    document.getElementById("season-progress-fill").style.width = f"{fraction * 100:.0f}%"
    if campaign.revisiting:
        text = "Looking back \u2014 time is held while you view a past era."
    elif sim_speed == 0:
        text = "Paused \u2014 choose 1x, 2x or 4x to let seasons pass."
    else:
        remaining = max(0.0, (season_length() - season_progress) / sim_speed)
        text = f"Running at {sim_speed}x \u2014 next season in {remaining:.0f}s."
    document.getElementById("season-clock-display").innerText = text


def _make_speed_handler(speed):
    def handler(event=None):
        set_speed(speed)
    return handler


def on_advance_season(event=None):
    effects = current_effects()
    report = state.advance_season(effects)
    state.record_score(sustainability.score(state, effects))
    trajectory.record(state, report, sustainability.livability(state, effects) * 100.0)
    before = consulting.get(campaign.ui)
    after = consulting.step(campaign, effects)
    if after is not None and after["result"] and (before is None or before["result"] is None):
        chronicle.log_challenge(state.season, state.era, consulting.status_text(after, state))
    event = challenges.after_season(state, report, effects)
    if event is not None:
        chronicle.log_challenge(state.season, state.era, event["text"])
    chronicle.check_population(state)
    chronicle.check_livability(state, effects)
    _tick_play_time()
    render()
    _check_new_achievements_for_toast()


# --- the shared save widget's contract ---------------------------------
# SAVE-BUTTON-INTEGRATION.md: shared/save-widget.js drives every game in the
# hub through exactly these two functions and never looks inside the dict,
# so Continuum's era-snapshot/revisit structure needs no widget changes —
# see save.py for the schema itself.
def get_state():
    campaign.ui["info_page_open"] = info_page_open
    data = campaign.to_dict()
    # Milestone 15 (ACHIEVEMENTS-SYSTEM-DESIGN.md): a write-only projection,
    # not part of Campaign's own save schema — always recomputed fresh here,
    # never read back in load_state() below.
    data["achievements_earned"] = achievement_ids_earned()
    return data


def load_state(data):
    global info_page_open
    if not campaign.load_dict(data):
        return False
    info_page_open = bool(campaign.ui.get("info_page_open", False))
    render()
    _seed_achievement_toast_baseline()
    return True


def _make_branch_chip_handler(branch):
    def handler(event=None):
        if branch in research_branch_filter:
            research_branch_filter.discard(branch)
        else:
            research_branch_filter.add(branch)
        for b in research.BRANCHES:
            chip = document.getElementById(f"research-branch-{b}-button")
            on = b in research_branch_filter
            chip.classList.toggle("active", on)
            chip.setAttribute("aria-pressed", "true" if on else "false")
        render_research()
    return handler


def on_research_search_input(event=None):
    global research_search_query
    research_search_query = document.getElementById("research-search-input").value
    render_research()


def setup():
    # Work/Build row buttons are wired inside render_work()/render_buildings()
    # themselves now (Milestone 8) — those rows are rebuilt every render, the
    # same as the research panel's Study buttons already were, so wiring them
    # here would just be wiring buttons that don't exist yet.
    for speed, key in ((0, "pause"), (1, "1x"), (2, "2x"), (4, "4x")):
        document.getElementById(f"speed-{key}-button").addEventListener(
            "click", create_proxy(_make_speed_handler(speed))
        )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("info-page-report-button").addEventListener(
        "click", create_proxy(submit_info_page_report)
    )
    document.getElementById("advance-era-button").addEventListener(
        "click", create_proxy(on_advance_era)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("exit-revisit-button").addEventListener(
        "click", create_proxy(on_exit_revisit)
    )
    for _branch in research.BRANCHES:
        document.getElementById(f"research-branch-{_branch}-button").addEventListener(
            "click", create_proxy(_make_branch_chip_handler(_branch))
        )
    document.getElementById("research-search-input").addEventListener(
        "input", create_proxy(on_research_search_input)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_summary_panel)
    )
    document.getElementById("founders-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_founders)
    )
    document.getElementById("minutes-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_minutes)
    )
    document.getElementById("views-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_views)
    )
    for _tab in VIEW_TABS:
        document.getElementById(f"views-tab-{_tab}-button").addEventListener(
            "click", create_proxy(_make_views_tab_handler(_tab))
        )
    document.getElementById("founders-add-button").addEventListener(
        "click", create_proxy(on_add_founders_note)
    )
    # K12 — three static scenario buttons (never rebuilt at runtime, unlike
    # the dynamic per-era rows elsewhere in this file), so each gets its
    # own one-shot proxy here rather than the "destroy the stale proxy"
    # discipline render_research()/render_work() need for rows that are
    # rebuilt every render.
    for _scenario_id in sim.SCENARIOS:
        document.getElementById(f"scenario-{_scenario_id}-button").addEventListener(
            "click", create_proxy(_make_select_scenario_handler(_scenario_id))
        )
    document.getElementById("hard-mode-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hard_mode)
    )
    for _case_id in consulting.CASES:
        document.getElementById(f"consulting-case-{_case_id}-button").addEventListener(
            "click", create_proxy(_make_consulting_start_handler(_case_id))
        )
    document.getElementById("consulting-abandon-button").addEventListener(
        "click", create_proxy(on_consulting_abandon)
    )
    # Belt-and-suspenders: the toast starts hidden via the static `hidden`
    # attribute in index.html, but every other stateful element in this
    # file (panels, buttons) has its shown/hidden state actively driven by
    # code rather than left to rely on markup alone — setting it here too
    # means the toast's default state doesn't depend on the static HTML
    # attribute ever being present or correct.
    document.getElementById("achievement-toast").hidden = True
    update_changelog_display()
    render()
    _seed_achievement_toast_baseline()


setup()
