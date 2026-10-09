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

import advisors  # noqa: E402
import archive  # noqa: E402
import banners  # noqa: E402
import beyond  # noqa: E402
import citizens  # noqa: E402
import challengerun  # noqa: E402
import challenges  # noqa: E402
import consulting  # noqa: E402
import dataexport  # noqa: E402
import doctrines  # noqa: E402
import dynasty  # noqa: E402
import eastereggs  # noqa: E402
import explain  # noqa: E402
import founding  # noqa: E402
import geography  # noqa: E402
import hamlet  # noqa: E402
import heritage  # noqa: E402
import info_content  # noqa: E402
import info_page  # noqa: E402
import minutes  # noqa: E402
import monuments  # noqa: E402
import naming  # noqa: E402
import neighbours  # noqa: E402
import orders  # noqa: E402
import par  # noqa: E402
import postmortem  # noqa: E402
import narrative_log  # noqa: E402
import research  # noqa: E402
import rewind  # noqa: E402
import save  # noqa: E402
import sim  # noqa: E402
import statlog  # noqa: E402
import summary  # noqa: E402
import sustainability  # noqa: E402
import techdebt  # noqa: E402
import timelapse  # noqa: E402
import trajectory  # noqa: E402
import forecast  # noqa: E402
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
    effects = tree.effects()
    # K-4: technical debt (Digital Age on) reaches the season loop through this same seam.
    # Not applied during a Look Back: the live debt belongs to the present settlement.
    if campaign.revisiting is None:
        effects = techdebt.apply_effects(effects, campaign.ui, state.era)
    # K-10/K-11: a challenge run's modifier (the day's boon with a price) rides the same seam.
    effects = challengerun.apply_effects(effects, campaign.ui)
    _sync_tree_costs()
    if campaign.revisiting is None:
        # K-2/K-6/K-15: Dynasty perks, doctrines and notable citizens ride the same seam. The
        # earned advantages rest while a challenge run or consulting case is the active run.
        resting = _resting()
        effects = dynasty.apply_effects(effects, campaign.ui, resting)
        effects = doctrines.apply_effects(effects, campaign.ui)
        effects = citizens.apply_effects(effects, campaign.ui, state.era, resting)
        # K-5: kept heritage sites add to culture, cleared ones take a little away.
        effects = heritage.apply_effects(effects, campaign.ui, campaign.furthest_era, resting)
        # K-13: the Beyond's standing pressure, while a run is on.
        effects = beyond.apply_effects(effects, campaign.ui, state, not resting)
        # K-12: the generated map's boons and prices (a challenge run is always played on open land).
        effects = geography.apply_effects(effects, _geo_seed())
    return effects


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

    # Relay Age+ (R2-K26): the holdings' supply line. Narrated only when a
    # holding exists and the last delivery fell short, the same "only
    # narrate a real gap" discipline as the canal/public-works/ring lines.
    if report.get("holdings_residents", 0) > 0 and report.get("outlying_served", 1.0) < 1.0:
        served_pct = report["outlying_served"] * 100
        parts.append(
            f"The holdings received only {served_pct:.0f}% of the supplies they need — "
            "their share of the new land dries up with it, and the gap between how the "
            "core lives and how they do counts against the score."
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
    update_techdebt_display()
    update_challenge_panel()
    update_timelapse_panel()
    update_advisors_panel()
    update_summary_panel()
    update_postmortem_panel()
    update_views_panel(effects)
    update_consulting_display()
    update_found_display()
    update_dynasty_panel()
    update_doctrines_panel()
    update_citizens_panel()
    update_spotlight_card()
    update_neighbours_panel()
    update_orders_panel()
    update_heritage_panel()
    update_beyond_panel()
    update_geography_panel()
    update_rewind_button()
    render_insights(effects)
    render_hamlet(effects)
    _notify_visual_layer()


def get_visual_state():
    """Phase 5's data contract for the Three.js render layer — see
    visual.py. Exposed as a plain module-level function (same shape as
    get_state()/load_state() below) so render3d.js can call it through
    Pyodide's globals the same way the shared save widget calls those two.
    Returns a plain dict; pyodide's toJs() (called from JS) turns it into
    a plain JS object, mirroring the save widget's own contract.
    """
    visual_data = visual.visual_state(state, current_effects())
    # K-5: the heritage sites standing behind the era being drawn (none while a challenge run or
    # consulting case rests), as plain {era, kept} so the scene can draw a ruin or a cleared patch.
    sites = [] if _resting() else heritage.sites_before(state.era, campaign.ui)
    visual_data["heritage"] = [{"era": s["era"], "kept": s["kept"]} for s in sites]
    # K-12: the non-plains cells of the generated map (empty on open land) for the scene to lay down.
    visual_data["terrain"] = geography.terrain_cells(geography.generate(_geo_seed()))
    return visual_data


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
    return (
        state.season > 1
        or consulting.get(campaign.ui) is not None
        or challengerun.get(campaign.ui) is not None
    )


def refuge_unlocked():
    """O-8: the Refuge Start is offered once any settlement, ever, has
    reached the Space Age (live achievements plus the ones carried over from
    earlier settlements, or an archived settlement that got that far)."""
    return founding.refuge_unlocked(achievement_ids_earned(), archive_load())


def _scenario_available(scenario_id):
    if scenario_id in dynasty.SCENARIO_UNLOCKS:
        return dynasty.scenario_unlocked(campaign.ui, scenario_id)
    return scenario_id != "refuge" or refuge_unlocked()


def _make_select_scenario_handler(scenario_id):
    def handler(event=None):
        if _scenario_locked() or scenario_id not in sim.SCENARIOS or not _scenario_available(scenario_id):
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
        # O-8: only the Refuge Start sets its own knowledge; picking any other
        # scenario (or switching back) puts the standard opening figure back.
        state.resources["knowledge"] = config.get("knowledge", sim.START_KNOWLEDGE)
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
    if challengerun.active(campaign.ui) is not None:
        return  # K-10/K-11: Hard Mode is part of the run's setup, so the par stays comparable
    state.hard_mode = not state.hard_mode
    render()


# --- K22 consulting mode --------------------------------------------------
def _make_consulting_start_handler(case_id):
    def handler(event=None):
        if challengerun.get(campaign.ui) is not None:
            return  # a challenge run already owns this opening
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
        button.disabled = not pristine or challengerun.get(campaign.ui) is not None
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
        available = _scenario_available(scenario_id)
        button.disabled = locked or not available
        button.classList.toggle("selected", state.scenario == scenario_id)
        if scenario_id == "refuge" or scenario_id in dynasty.SCENARIO_UNLOCKS:
            label = sim.SCENARIOS[scenario_id]["label"]
            button.innerText = label if available else f"🔒 {label}"
            hint = sim.SCENARIOS[scenario_id]["blurb"]
            if scenario_id == "refuge":
                lock_text = f"reach the {sim.ERA_LABEL[sim.REFUGE_UNLOCK_ERA]} in any settlement"
            else:
                lock_text = f"buy the \u201c{dynasty.scenario_unlock_label(scenario_id)}\u201d perk in the Dynasty"
            button.title = hint if available else f"Locked: {lock_text} to unlock this opening."
            button.setAttribute(
                "aria-label",
                f"{label}, available" if available else f"{label}, locked until you {lock_text}",
            )


def update_hard_mode_display():
    button = document.getElementById("hard-mode-toggle-button")
    button.innerText = f"☠️ Hard Mode: {'ON' if state.hard_mode else 'OFF'}"
    button.classList.toggle("active", state.hard_mode)
    button.disabled = challengerun.active(campaign.ui) is not None


# ===========================================================================
# K-4: technical debt (Digital Age and later). The rules live in techdebt.py;
# this is the DOM half: the Quick builds toggle, the refactor button and the
# status lines. The section is its own block (not inside #buildings) so it is
# still reachable in the Hamlet view and the Desktop boot, which hide the
# ordinary Build panel.
# ===========================================================================
def _easter_egg(found):
    """K-23: writes a once-only flavour line into the log (hidden with the story toggle)."""
    if found is not None:
        chronicle.log_challenge(state.season, state.era, found[1])


def _debt_hazard():
    """0/1/2: the civic map's technical-debt tint band for the live settlement."""
    if campaign.revisiting is not None or not techdebt.active(state.era):
        return 0
    return techdebt.hazard_level(techdebt.get(campaign.ui)["debt"])


def _book_quick_build(building):
    """Called after a build succeeded at full price: refunds the quick-build
    discount and books the debt. Does nothing outside the Digital Age on, in a
    Look Back, or with Quick builds off."""
    if campaign.revisiting is not None or not techdebt.active(state.era):
        return False
    refund = techdebt.quick_build(campaign.ui, sim.BUILDING_COST[building])
    if refund > 0:
        state.resources["materials"] += refund
    return refund > 0


def on_toggle_quick_build(event=None):
    if campaign.revisiting is not None or not techdebt.active(state.era):
        return
    record = techdebt.get(campaign.ui)
    techdebt.set_quick(campaign.ui, not record["quick"])
    render()


def on_toggle_refactor(event=None):
    if campaign.revisiting is not None or not techdebt.active(state.era):
        return
    record = techdebt.get(campaign.ui)
    techdebt.schedule_refactor(campaign.ui, not record["refactor"])
    render()


def update_techdebt_display():
    section = document.getElementById("techdebt")
    active = techdebt.active(state.era)
    section.hidden = not (active or _pc_layout())
    record = techdebt.get(campaign.ui)
    quick = document.getElementById("quick-build-toggle-button")
    refactor = document.getElementById("refactor-button")
    status = document.getElementById("techdebt-status-display")
    note = document.getElementById("techdebt-note-display")
    quick.hidden = not active
    refactor.hidden = not active
    if not active:
        status.innerText = "Technical debt begins in the Digital Age."
        note.innerText = (
            "From then on you can build quickly and cheaply, at the price of debt that "
            "costs upkeep and output until you schedule a refactor season."
        )
        return
    locked = campaign.revisiting is not None
    quick.innerText = f"⚡ Quick builds: {'ON' if record['quick'] else 'OFF'}"
    quick.classList.toggle("active", record["quick"])
    quick.setAttribute("aria-pressed", "true" if record["quick"] else "false")
    quick.disabled = locked
    refactor.innerText = (
        "🔧 Refactor season scheduled: cancel" if record["refactor"] else "🔧 Schedule a refactor season"
    )
    refactor.setAttribute("aria-pressed", "true" if record["refactor"] else "false")
    refactor.disabled = locked or (record["debt"] <= 0 and not record["refactor"])
    status.innerText = " ".join(techdebt.status_lines(state, record))
    cost = min(sim.BUILDING_COST[b] for b in sim.buildings_for_era(state.era))
    note.innerText = techdebt.build_note(record, cost)


# ===========================================================================
# K-10 daily challenge and K-11 scenario editor with share codes. The rules, the
# par autopilot, the mod-code format and the ledger live in challengerun.py; this
# is the DOM half. A "challenge run" is a fixed start, an optional modifier, Hard
# Mode on or off and a length in seasons; it needs a fresh settlement.
# ===========================================================================
challenge_panel_open = False
_challenge_editor = challengerun.default_config()   # the editor's current dial values (not saved)
_challenge_code_message = ""
_challenge_start_message = ""
_challenge_utc_today_override = None                # tests set a date here


def _utc_today():
    """Today's date in UTC as YYYY-MM-DD (the daily changes at 00:00 UTC for everybody)."""
    if _challenge_utc_today_override:
        return _challenge_utc_today_override
    window = _js_window()
    try:
        seed_js = getattr(window, "NoyvjSeed", None) if window is not None else None
        text = str(seed_js.daily.today()) if seed_js is not None else ""
        if len(text) == 10:
            return text
    except Exception:  # noqa: BLE001 -- the page helper is optional
        pass
    return time.strftime("%Y-%m-%d", time.gmtime())


def challenge_ledger_load():
    window = _js_window()
    if window is None:
        return []
    try:
        raw = window.localStorage.getItem(challengerun.LEDGER_KEY)
    except Exception:  # noqa: BLE001
        return []
    return challengerun.clean_ledger(raw) if isinstance(raw, str) else []


def challenge_ledger_store(entries):
    window = _js_window()
    if window is None:
        return False
    try:
        window.localStorage.setItem(challengerun.LEDGER_KEY, challengerun.serialize_ledger(entries))
        return True
    except Exception:  # noqa: BLE001
        return False


def _challenge_read_inputs():
    """Reads the editor's controls into `_challenge_editor` (always a valid config)."""
    global _challenge_editor
    raw = {}
    for name in challengerun.RANGES:
        raw[name] = document.getElementById(f"challenge-dial-{name}").value
    raw["modifier"] = document.getElementById("challenge-modifier-select").value
    raw["hard"] = bool(getattr(document.getElementById("challenge-hard-checkbox"), "checked", False))
    _challenge_editor = challengerun.clean_config(raw)
    return _challenge_editor


def _challenge_write_inputs(cfg):
    for name in challengerun.RANGES:
        document.getElementById(f"challenge-dial-{name}").value = str(cfg[name])
    document.getElementById("challenge-modifier-select").value = cfg["modifier"]
    document.getElementById("challenge-hard-checkbox").checked = cfg["hard"]


def _build_challenge_controls():
    select = document.getElementById("challenge-modifier-select")
    select.innerHTML = ""
    for modifier_id in challengerun.MODIFIER_IDS:
        option = document.createElement("option")
        option.value = modifier_id
        option.innerText = challengerun.modifier_label(modifier_id)
        select.appendChild(option)
    _challenge_write_inputs(_challenge_editor)


def on_toggle_challenge(event=None):
    global challenge_panel_open
    challenge_panel_open = not challenge_panel_open
    update_challenge_panel()


def on_challenge_input(event=None):
    global _challenge_code_message
    _challenge_code_message = ""
    _challenge_read_inputs()
    update_challenge_panel()


def _begin_challenge(kind, config, seed_text="", date_text=""):
    """Starts a run on the fresh settlement. Returns True when it began."""
    global _challenge_start_message
    if not challengerun.can_start(campaign):
        _challenge_start_message = (
            "A challenge run needs a fresh settlement: before the first season, not a consulting case."
        )
        update_challenge_panel()
        return False
    if not challengerun.start(campaign, chronicle, kind, config, seed_text, date_text):
        _challenge_start_message = "That run could not be started."
        update_challenge_panel()
        return False
    _challenge_start_message = ""
    cfg = challengerun.clean_config(config)
    label = f"the daily challenge for {date_text}" if kind == "daily" else f"mod code {challengerun.encode(cfg)}"
    chronicle.log_challenge(
        state.season, state.era, f"Challenge run begins: {label}, {cfg['goal']} seasons."
    )
    sync_name_input()
    render()
    _seed_achievement_toast_baseline()
    return True


def on_challenge_daily_start(event=None):
    today = _utc_today()
    day = challengerun.daily(today)
    if day is None:
        return
    if _begin_challenge("daily", day["config"], day["seed"], day["date"]):
        window = _js_window()
        try:
            if window is not None and getattr(window, "NoyvjSeed", None) is not None:
                window.NoyvjSeed.set(day["seed"])
        except Exception:  # noqa: BLE001 -- the footer seed is a nicety
            pass


def on_challenge_custom_start(event=None):
    _begin_challenge("custom", _challenge_read_inputs())


def on_challenge_abandon(event=None):
    if challengerun.abandon(campaign):
        render()


def on_challenge_copy_code(event=None):
    global _challenge_code_message
    window = _js_window()
    code = challengerun.encode(_challenge_editor)
    copied = False
    try:
        if window is not None and getattr(window, "navigator", None) is not None:
            window.navigator.clipboard.writeText(code)
            copied = True
    except Exception:  # noqa: BLE001
        copied = False
    _challenge_code_message = (
        f"Copied {code}." if copied else f"Select the code above and press Ctrl+C: {code}"
    )
    update_challenge_panel()


def on_challenge_load_code(event=None):
    global _challenge_code_message
    cfg, error = challengerun.decode(document.getElementById("challenge-code-input").value)
    if cfg is None:
        _challenge_code_message = error
    else:
        _challenge_write_inputs(cfg)
        _challenge_read_inputs()
        _challenge_code_message = "Code loaded into the editor. Press Play this setup to try it."
    update_challenge_panel()


def _finish_challenge_run(result):
    """Called on the season the run ends: books the par, the ledger, the daily mark and a log line."""
    run = challengerun.get(campaign.ui)
    if run is None:
        return
    par_points = challengerun.par_for(run["config"])
    run["par"] = par_points
    campaign.ui[challengerun.KEY] = run
    challenge_ledger_store(challengerun.ledger_add(challenge_ledger_load(), run))
    chronicle.log_challenge(
        state.season,
        state.era,
        f"Challenge run complete: {result['points']} points over {result['seasons']} seasons. "
        + challengerun.verdict(result["points"], par_points),
    )
    if run["kind"] == "daily" and run["date"] == _utc_today():
        window = _js_window()
        try:
            if window is not None and getattr(window, "NoyvjSeed", None) is not None:
                info = window.JSON.parse(
                    json.dumps({"score": result["points"], "text": f"{result['points']} points"})
                )
                window.NoyvjSeed.daily.markCompleted("continuum", info)
        except Exception:  # noqa: BLE001 -- the hub's Today strip is a nicety
            pass
    _display_toast(f"🎯 Challenge run complete: {result['points']} points")


def challenge_share_result():
    """The finished run as JSON for the shared Copy result button ({} when none is finished)."""
    fields = challengerun.share_fields(challengerun.get(campaign.ui))
    return json.dumps(fields or {})


def _daily_done_today():
    window = _js_window()
    try:
        seed_js = getattr(window, "NoyvjSeed", None) if window is not None else None
        if seed_js is None:
            return None
        data = seed_js.daily.read()
        runs = getattr(data, "runs", None)
        entry = getattr(runs, "continuum", None) if runs is not None else None
        if entry is None:
            return None
        score = getattr(entry, "score", None)
        return int(score) if score is not None else 0
    except Exception:  # noqa: BLE001
        return None


def update_challenge_panel():
    toggle = document.getElementById("challenge-toggle-button")
    panel = document.getElementById("challenge-panel")
    toggle.innerText = "Hide Challenge Runs" if challenge_panel_open else "🎯 Challenge Runs"
    panel.hidden = not challenge_panel_open
    if not challenge_panel_open:
        return
    run = challengerun.get(campaign.ui)
    can_start = challengerun.can_start(campaign)
    status = document.getElementById("challenge-run-status-display")
    result_box = document.getElementById("challenge-result-display")
    abandon = document.getElementById("challenge-abandon-button")
    document.getElementById("challenge-copy-result").hidden = run is None or run["result"] is None
    if run is None:
        status.innerText = _challenge_start_message or (
            "No challenge run in progress."
            if can_start
            else "Start a challenge run from a fresh settlement (before the first season)."
        )
        result_box.hidden = True
        abandon.hidden = True
    else:
        kind = "Daily challenge" if run["kind"] == "daily" else "Custom run"
        when = f" {run['date']}" if run["date"] else ""
        mod = challengerun.modifier_label(run["config"]["modifier"])
        status.innerText = (
            f"{kind}{when} (code {run['code']}). {challengerun.progress_text(run)} "
            f"Modifier: {mod}. Hard Mode: {'on' if run['config']['hard'] else 'off'}."
        )
        abandon.hidden = False
        if run["result"] is None:
            result_box.hidden = True
        else:
            result_box.hidden = False
            par_points = run["par"] if run["par"] is not None else challengerun.par_for(run["config"])
            res = run["result"]
            result_box.innerHTML = ""
            for line in (
                f"Result: {res['points']} points. {challengerun.verdict(res['points'], par_points)}",
                f"Average sustainability {res['avg_score']:.0f}, {res['population']} people, "
                f"{res['discoveries']} discoveries, {res['eras']} eras entered.",
            ):
                row = document.createElement("p")
                row.className = "status-line"
                row.innerText = line
                result_box.appendChild(row)

    # today's challenge
    today = _utc_today()
    day = challengerun.daily(today)
    info = document.getElementById("challenge-daily-info")
    daily_button = document.getElementById("challenge-daily-start-button")
    if day is None:
        info.innerText = "Today's challenge is not available."
        daily_button.disabled = True
    else:
        cfg = day["config"]
        par_points = challengerun.par_for(cfg)
        scenario = sim.SCENARIOS[day["scenario"]]["label"]
        mod = challengerun.MODIFIERS[cfg["modifier"]]
        done = _daily_done_today()
        text = (
            f"{today} (UTC), seed {day['seed']}: {scenario}, modifier {mod['label']} ({mod['blurb']}) "
            f"Hard Mode {'on' if cfg['hard'] else 'off'}, {cfg['goal']} seasons. Par {par_points} points. "
            "The same for everyone, changing at 00:00 UTC."
        )
        if done is not None:
            text += f" Done today: {done} points."
        info.innerText = text
        daily_button.disabled = not can_start
        daily_button.innerText = "Play today's challenge" if done is None else "Play today's challenge again"

    # the editor
    cfg = _challenge_editor
    for name in challengerun.RANGES:
        document.getElementById(f"challenge-dial-{name}-value").innerText = str(cfg[name])
    par_points = challengerun.par_for(cfg)
    preview = " ".join(challengerun.summary_lines(cfg)) + f" Par: {par_points} points."
    document.getElementById("challenge-preview-display").innerText = preview
    document.getElementById("challenge-code-display").value = challengerun.encode(cfg)
    document.getElementById("challenge-custom-start-button").disabled = not can_start
    document.getElementById("challenge-code-message").innerText = _challenge_code_message

    # finished runs
    holder = document.getElementById("challenge-ledger-list")
    holder.innerHTML = ""
    entries = challenge_ledger_load()
    if not entries:
        row = document.createElement("p")
        row.className = "row-blurb"
        row.innerText = "No finished runs yet. Each one you finish is listed here with its points and its par."
        holder.appendChild(row)
    for entry in reversed(entries):
        row = document.createElement("p")
        row.className = "status-line challenge-ledger-row"
        row.innerText = challengerun.ledger_line(entry)
        holder.appendChild(row)


# ===========================================================================
# K-9: the time-lapse run replay. Scrub the settlement's recorded history as the civic map,
# with discoveries, eras, first buildings and founder's notes pinned on a timeline, and
# download an image strip. The data work is in timelapse.py; the panel is session-only state.
# ===========================================================================
timelapse_open = False
_tl_index = 0
_tl_playing = False
_tl_proxy = None
TIMELAPSE_STEP_MS = 450


def _tl_frames():
    return timelapse.frames(campaign.ui) if campaign.revisiting is None else []


def on_toggle_timelapse(event=None):
    global timelapse_open, _tl_index
    timelapse_open = not timelapse_open
    if timelapse_open:
        _tl_index = max(0, len(_tl_frames()) - 1)
    else:
        _tl_stop()
    update_timelapse_panel()


def _tl_stop():
    global _tl_playing
    _tl_playing = False


def _tl_set_index(index):
    global _tl_index
    count = len(_tl_frames())
    _tl_index = max(0, min(max(0, count - 1), int(index)))


def on_timelapse_scrub(event=None):
    _tl_stop()
    try:
        _tl_set_index(int(document.getElementById("timelapse-scrub").value))
    except (TypeError, ValueError):
        pass
    update_timelapse_panel()


def on_timelapse_prev(event=None):
    _tl_stop()
    _tl_set_index(_tl_index - 1)
    update_timelapse_panel()


def on_timelapse_next(event=None):
    _tl_stop()
    _tl_set_index(_tl_index + 1)
    update_timelapse_panel()


def _tl_tick(*args):
    global _tl_playing
    if not _tl_playing or not timelapse_open:
        _tl_playing = False
        return
    count = len(_tl_frames())
    if _tl_index >= count - 1:
        _tl_playing = False
        update_timelapse_panel()
        return
    _tl_set_index(_tl_index + 1)
    update_timelapse_panel()
    if _tl_playing:
        setTimeout(_tl_proxy, TIMELAPSE_STEP_MS)


def on_timelapse_play(event=None):
    global _tl_playing, _tl_proxy
    if _tl_playing:
        _tl_stop()
        update_timelapse_panel()
        return
    count = len(_tl_frames())
    if count < timelapse.MIN_FRAMES:
        return
    if _tl_index >= count - 1:
        _tl_set_index(0)
    _tl_playing = True
    if _tl_proxy is None:
        _tl_proxy = create_proxy(_tl_tick)
    update_timelapse_panel()
    setTimeout(_tl_proxy, TIMELAPSE_STEP_MS)


def _make_timelapse_jump_handler(season):
    def handler(event=None):
        _tl_stop()
        for i, frame in enumerate(_tl_frames()):
            if frame["season"] == season:
                _tl_set_index(i)
                break
        update_timelapse_panel()
    return handler


_tl_pin_proxies = []


def on_timelapse_strip(event=None):
    frame_list = _tl_frames()
    if not timelapse.usable(frame_list):
        return
    name = settlement_name()
    _download_text(timelapse.strip_svg(frame_list, name), timelapse.strip_filename(name, frame_list), "image/svg+xml")


def update_timelapse_panel():
    toggle = document.getElementById("timelapse-toggle-button")
    panel = document.getElementById("timelapse-panel")
    toggle.innerText = "Hide Time-lapse" if timelapse_open else "⏱ Time-lapse"
    panel.hidden = not timelapse_open
    if not timelapse_open:
        return
    frame_list = _tl_frames()
    caption = document.getElementById("timelapse-caption")
    scrub = document.getElementById("timelapse-scrub")
    play = document.getElementById("timelapse-play-button")
    usable = timelapse.usable(frame_list)
    for button_id in ("timelapse-prev-button", "timelapse-next-button", "timelapse-strip-button"):
        document.getElementById(button_id).disabled = not usable
    play.disabled = not usable
    scrub.disabled = not usable
    pin_box = document.getElementById("timelapse-pins-list")
    for stale in _tl_pin_proxies:
        stale.destroy()
    _tl_pin_proxies.clear()
    pin_box.innerHTML = ""
    if not usable:
        caption.innerText = (
            "Nothing to replay yet: play at least two seasons (a Look Back has no replay of its own)."
            if campaign.revisiting is None
            else "A Look Back shows a past snapshot; return to the present to use the time-lapse."
        )
        document.getElementById("timelapse-map").innerHTML = ""
        document.getElementById("timelapse-chart").innerHTML = ""
        play.innerText = "▶ Play"
        return
    _tl_set_index(_tl_index)
    frame = frame_list[_tl_index]
    pin_list = timelapse.pins(campaign.ui, frame_list)
    scrub.setAttribute("min", "0")
    scrub.setAttribute("max", str(len(frame_list) - 1))
    if str(scrub.value) != str(_tl_index):
        scrub.value = str(_tl_index)
    scrub.setAttribute("aria-valuetext", timelapse.caption(frame))
    play.innerText = "⏸ Pause" if _tl_playing else "▶ Play"
    play.setAttribute("aria-pressed", "true" if _tl_playing else "false")
    caption.innerText = timelapse.caption(frame)
    here = timelapse.pins_at(pin_list, frame["season"])
    if here:
        caption.innerText += " " + " ".join(timelapse.pin_text(p) for p in here)
    document.getElementById("timelapse-map").innerHTML = timelapse.map_svg(frame)
    document.getElementById("timelapse-chart").innerHTML = timelapse.chart_svg(frame_list, _tl_index, pin_list)
    if not pin_list:
        row = document.createElement("p")
        row.className = "row-blurb"
        row.innerText = "No events pinned yet: study a discovery, raise a building or add a founder's note."
        pin_box.appendChild(row)
    for pin in pin_list:
        button = document.createElement("button")
        button.className = "secondary timelapse-pin"
        button.type = "button"
        button.innerText = timelapse.pin_text(pin)
        proxy = create_proxy(_make_timelapse_jump_handler(pin["season"]))
        _tl_pin_proxies.append(proxy)
        button.addEventListener("click", proxy)
        pin_box.appendChild(button)


# ===========================================================================
# K-8: the advisor council. Four invented advisors give one piece of advice each, checked by
# running the coming season on a copy (advisors.py). Optional, and hidden by the story toggle.
# The buttons carry out the advice through the same handlers the Work and Build panels use.
# ===========================================================================
advisors_open = False
_advisors_proxies = []
_advisors_signature_seen = None


def _advisor_open_item(advisor_id):
    for item in advisors.get(campaign.ui)["advice"]:
        if item["id"] == advisor_id:
            return item
    return None


def _make_advisor_follow_handler(advisor_id):
    def handler(event=None):
        if campaign.revisiting is not None:
            return
        item = _advisor_open_item(advisor_id)
        if item is None or item["status"] != "open" or not advisors.available(state, item["action"]):
            return
        action = item["action"]
        if action["type"] == "assign":
            _make_assign_handler(action["role"])(None)
        elif action["type"] == "move":
            _make_unassign_handler(action["from"])(None)
            _make_assign_handler(action["role"])(None)
        else:
            _make_build_handler(action["building"])(None)
        advisors.mark_followed(campaign.ui, advisor_id)
        render()
    return handler


def on_toggle_advisors(event=None):
    global advisors_open, _advisors_signature_seen
    advisors_open = not advisors_open
    _advisors_signature_seen = None
    update_advisors_panel()


def _advisors_rows(record):
    rows = []
    by_id = {item["id"]: item for item in record["advice"]}
    for advisor_id in advisors.ORDER:
        item = by_id.get(advisor_id)
        can = bool(item and item["status"] == "open" and campaign.revisiting is None
                   and advisors.available(state, item["action"]))
        rows.append((advisor_id, item, can))
    return rows


def update_advisors_panel():
    global _advisors_signature_seen
    toggle = document.getElementById("advisors-toggle-button")
    panel = document.getElementById("advisors-panel")
    toggle.innerText = "Hide Advisors" if advisors_open else "🧭 Advisors"
    panel.hidden = not advisors_open
    if not advisors_open:
        return
    if campaign.revisiting is None and advisors.stale(campaign.ui, state):
        advisors.issue(campaign.ui, state, current_effects())
    record = advisors.get(campaign.ui)
    rows = _advisors_rows(record)
    signature = (
        record["season"], campaign.revisiting,
        tuple((a, it["text"] if it else "", it["status"] if it else "", can, record["trust"][a],
               tuple(sorted(record["record"][a].items()))) for a, it, can in rows),
        tuple(h["text"] for h in record["history"]),
    )
    if signature == _advisors_signature_seen:
        return
    _advisors_signature_seen = signature
    for stale_proxy in _advisors_proxies:
        stale_proxy.destroy()
    _advisors_proxies.clear()
    holder = document.getElementById("advisors-list")
    holder.innerHTML = ""
    for advisor_id, item, can in rows:
        info = advisors.ADVISORS[advisor_id]
        card = document.createElement("div")
        card.className = "advisor-card"
        for css, tag, text in (
            ("advisor-name", "h3", f"{info['name']}, {info['title']}"),
            ("advisor-trust status-line", "p", advisors.trust_text(record["trust"][advisor_id])),
            ("advisor-voice row-blurb", "p", f"\u201c{info['voice']}\u201d"),
        ):
            node = document.createElement(tag)
            node.className = css
            node.innerText = text
            card.appendChild(node)
        if item is None:
            node = document.createElement("p")
            node.className = "row-blurb"
            node.innerText = "Nothing to recommend this season."
            card.appendChild(node)
        else:
            for css, text in (("advisor-advice status-line", item["text"]), ("advisor-claim row-blurb", advisors.claim_text(item))):
                node = document.createElement("p")
                node.className = css
                node.innerText = text
                card.appendChild(node)
            button = document.createElement("button")
            button.id = f"advisor-{advisor_id}-follow-button"
            button.className = "secondary"
            button.type = "button"
            followed = item["status"] == "followed"
            button.innerText = "✓ Taken this season" if followed else f"Take {info['name'].split()[0]}'s advice"
            button.disabled = not can
            proxy = create_proxy(_make_advisor_follow_handler(advisor_id))
            _advisors_proxies.append(proxy)
            button.addEventListener("click", proxy)
            card.appendChild(button)
        node = document.createElement("p")
        node.className = "advisor-record row-blurb"
        node.innerText = advisors.record_text(record["record"][advisor_id])
        card.appendChild(node)
        holder.appendChild(card)
    history = document.getElementById("advisors-history")
    history.innerHTML = ""
    if not record["history"]:
        node = document.createElement("p")
        node.className = "row-blurb"
        node.innerText = "No seasons judged yet. After each season the council's advice is scored and shown here."
        history.appendChild(node)
    for entry in reversed(record["history"]):
        node = document.createElement("p")
        node.className = "status-line advisor-history-row"
        year, season_name = year_and_season(max(1, entry["season"]))
        node.innerText = f"Year {year}, {season_name}: {entry['text']}"
        history.appendChild(node)


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
    return archive.make_record(
        campaign,
        len(achievement_ids_earned()),
        _today(),
        thumbnail,
        name=settlement_name(),
        researched=None if campaign.revisiting else len(tree.researched),
        minutes=int(play_seconds() // 60),
        cosmetics=_cosmetic_choice(),
        dynasty_info=_dynasty_record_info(),
        beyond_best=beyond.get(campaign.ui)["best"],
    )


def _cosmetic_choice():
    """K-20: the banner and flourish to show (anything no longer unlocked falls back to plain)."""
    return banners.effective(
        campaign.ui, set(achievement_ids_earned()), dynasty.rank_index(dynasty.get(campaign.ui)["earned"])
    )


def _dynasty_record_info():
    """K-2: the Dynasty rank and the perks that applied to this settlement, for the archive."""
    record = dynasty.get(campaign.ui)
    return {"rank": dynasty.rank_index(record["earned"]), "perks": dynasty.active_perk_ids(campaign.ui, _resting())}


def on_archive_current(event=None):
    global _archive_confirm_clear
    _archive_confirm_clear = False
    del _compare_picks[:]
    record = current_record(archive.clean_thumbnail(_capture_image(320, 0.7)))
    if record is not None:
        archive_store(archive.add_record(archive_load(), record))
    update_summary_panel()


def _make_archive_delete_handler(index):
    def handler(event=None):
        del _compare_picks[:]  # indexes shift after a delete
        archive_store(archive.remove_record(archive_load(), index))
        update_summary_panel()
    return handler


def on_archive_clear(event=None):
    global _archive_confirm_clear
    if not _archive_confirm_clear:
        _archive_confirm_clear = True
    else:
        _archive_confirm_clear = False
        del _compare_picks[:]
        archive_store([])
    update_summary_panel()


# --- K-19: compare two archived settlements ---------------------------------
# Session-only: the archive indexes picked for comparison, in pick order (A then B).
_compare_picks = []


def _make_compare_handler(index):
    def handler(event=None):
        if index in _compare_picks:
            _compare_picks.remove(index)
        else:
            if len(_compare_picks) >= 2:
                del _compare_picks[0]  # a third pick replaces the oldest
            _compare_picks.append(index)
        update_summary_panel()
    return handler


def on_compare_clear(event=None):
    del _compare_picks[:]
    update_summary_panel()


def _compare_cell(parent, tag, text, css=None):
    cell = document.createElement(tag)
    if css:
        cell.className = css
    cell.innerText = text
    parent.appendChild(cell)
    return cell


def _render_compare_table(panel, records):
    """The side-by-side table for the two picked entries (nothing when fewer than two)."""
    picks = [i for i in _compare_picks if 0 <= i < len(records)]
    if len(picks) != 2:
        return
    a, b = records[picks[0]], records[picks[1]]
    rows = archive.compare(a, b)
    if not rows:
        return
    box = document.createElement("div")
    box.className = "archive-compare"
    box.id = "archive-compare-box"
    heading = document.createElement("h3")
    heading.className = "summary-eras-heading"
    heading.innerText = "Comparing two settlements"
    box.appendChild(heading)
    note = document.createElement("p")
    note.className = "row-blurb"
    note.innerText = "The difference column is B minus A. The settlement ahead on each row is in bold and underlined."
    box.appendChild(note)
    for letter, record, index in (("A", a, picks[0]), ("B", b, picks[1])):
        who = document.createElement("p")
        who.className = "row-blurb compare-who"
        who.innerText = f"{letter}: {archive.record_label(record, index)}"
        box.appendChild(who)
    table = document.createElement("table")
    table.className = "compare-table"
    head = document.createElement("tr")
    _compare_cell(head, "th", "")
    _compare_cell(head, "th", "A")
    _compare_cell(head, "th", "B")
    _compare_cell(head, "th", "Difference (B \u2212 A)")
    table.appendChild(head)
    for row in rows:
        line = document.createElement("tr")
        line.className = "compare-row compare-row--differs" if row["delta"] not in ("\u25AC same", "same", "no comparison") else "compare-row"
        _compare_cell(line, "th", row["label"])
        _compare_cell(line, "td", row["a"], "compare-cell compare-cell--lead" if row["lead"] == "a" else "compare-cell")
        _compare_cell(line, "td", row["b"], "compare-cell compare-cell--lead" if row["lead"] == "b" else "compare-cell")
        _compare_cell(line, "td", row["delta"], "compare-delta")
        table.appendChild(line)
    box.appendChild(table)
    actions = document.createElement("div")
    actions.className = "archive-actions"
    _archive_button(actions, "archive-compare-clear-button", "Stop comparing", on_compare_clear)
    box.appendChild(actions)
    panel.appendChild(box)


# --- K-18: export the run as CSV / JSON -------------------------------------
_export_status = ""


def _download_text(text, filename, mime):
    window = _js_window()
    card = getattr(window, "ContinuumCard", None) if window is not None else None
    download = getattr(card, "downloadText", None)
    if download is None:
        return False
    try:
        download(json.dumps({"text": text, "filename": filename, "mime": mime}))
    except Exception:
        return False
    return True


def export_text(kind):
    """(text, filename, mime) for one export kind, or None when there is nothing to export.

    kinds: "stats" (per-season stats CSV), "minutes" (Council Minutes CSV),
    "run" (both, with the settlement's name, as JSON).
    """
    history = statlog.rows(campaign.ui)
    entries = minutes.entries(campaign.ui)
    name = settlement_name()
    today = _today()
    if kind == "stats":
        if not history:
            return None
        return dataexport.stats_csv(history), dataexport.filename("stats", name, today), dataexport.CSV_MIME
    if kind == "minutes":
        if not entries:
            return None
        return dataexport.minutes_csv(entries), dataexport.filename("minutes", name, today), dataexport.CSV_MIME
    if kind == "run":
        if not history and not entries:
            return None
        text = dataexport.run_json(name, state.scenario, state.hard_mode, history, entries)
        return text, dataexport.filename("run", name, today), dataexport.JSON_MIME
    return None


def _make_export_handler(kind):
    def handler(event=None):
        global _export_status
        result = export_text(kind)
        if result is None:
            _export_status = "Nothing to export yet: play a season (or make a decision) first."
        elif _download_text(*result):
            _export_status = f"Downloaded {result[1]}."
        else:
            _export_status = "The download could not start in this browser."
        update_summary_panel()
    return handler


def _download_card(record, thumbnail):
    window = _js_window()
    card = getattr(window, "ContinuumCard", None) if window is not None else None
    download = getattr(card, "download", None)
    if download is None:
        return False
    payload = {
        "title": archive.title_of(record),
        "lines": archive.card_lines(record),
        "thumb": thumbnail,
        "filename": f"continuum-card-{record['era']}-{record['saved_on']}.png",
    }
    payload.update(banners.card_payload({"banner": record.get("banner"), "flourish": record.get("flourish")}))
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


def _found_button(parent, button_id):
    """O-6: a "Found a new settlement" button, the archive as a jumping-off
    point. Same confirm-gated action as the scenario panel's own button."""
    button = _archive_button(parent, button_id, "Found a new settlement", on_found_new_settlement)
    button.disabled = campaign.revisiting is not None
    button.setAttribute("aria-label", "Found a new settlement (files the current settlement in the archive first)")
    return button


def _render_export_section(panel):
    """K-18: the three download buttons and their status line."""
    heading = document.createElement("h3")
    heading.className = "summary-eras-heading"
    heading.innerText = "Export your data"
    panel.appendChild(heading)
    note = document.createElement("p")
    note.className = "row-blurb"
    note.innerText = (
        "Download this settlement's numbers: one row per season (CSV), the Council Minutes (CSV), "
        "or both with the settlement's name (JSON). Kept on your device; nothing is sent anywhere."
    )
    panel.appendChild(note)
    actions = document.createElement("div")
    actions.className = "archive-actions"
    _archive_button(actions, "export-stats-button", "Per-season stats (CSV)", _make_export_handler("stats"))
    _archive_button(actions, "export-minutes-button", "Council Minutes (CSV)", _make_export_handler("minutes"))
    _archive_button(actions, "export-run-button", "Everything (JSON)", _make_export_handler("run"))
    panel.appendChild(actions)
    status = document.createElement("p")
    status.id = "export-status"
    status.className = "row-blurb export-status"
    status.setAttribute("role", "status")
    status.setAttribute("aria-live", "polite")
    status.innerText = _export_status
    panel.appendChild(status)


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
    _found_button(actions, "archive-found-button")
    panel.appendChild(actions)
    _render_export_section(panel)
    if len(records) >= 2:
        hint = document.createElement("p")
        hint.className = "row-blurb"
        hint.innerText = "Pick two filed settlements with their Compare buttons to see them side by side."
        panel.appendChild(hint)
    _render_compare_table(panel, records)

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
        if record.get("name"):
            name_row = document.createElement("p")
            name_row.className = "archive-line archive-line--name"
            name_row.innerText = record["name"]
            text.appendChild(name_row)
        for i, line in enumerate(archive.card_lines(record)):
            row = document.createElement("p")
            row.className = "archive-line archive-line--head" if i == 0 else "archive-line"
            row.innerText = line
            text.appendChild(row)
        stamp = document.createElement("p")
        stamp.className = "archive-line archive-date"
        stamp.innerText = f"Filed {record['saved_on']}"
        text.appendChild(stamp)
        if record.get("banner") or record.get("flourish"):
            # K-20: the cosmetic banner and flourish, drawn from the catalogue and named in words.
            flair = document.createElement("div")
            flair.className = "archive-flair"
            picture = document.createElement("span")
            picture.className = "archive-flair-picture"
            picture.innerHTML = (
                banners.banner_svg(record["banner"], 36) if record.get("banner") else ""
            ) + (banners.flourish_svg(record["flourish"], 120) if record.get("flourish") else "")
            flair.appendChild(picture)
            names = [banners.label_of(record["banner"])] if record.get("banner") else []
            if record.get("flourish"):
                names.append(banners.flourish_label_of(record["flourish"]))
            caption = document.createElement("span")
            caption.className = "archive-line"
            caption.innerText = " · ".join(names)
            flair.appendChild(caption)
            text.appendChild(flair)
        card.appendChild(text)
        buttons = document.createElement("div")
        buttons.className = "archive-actions"
        _archive_button(buttons, f"archive-card-{index}-button", "Card", _make_card_handler(index))
        picked = index in _compare_picks
        compare_label = "Compare"
        if picked:
            compare_label = "Comparing as " + ("A" if _compare_picks.index(index) == 0 else "B")
        compare_button = _archive_button(buttons, f"archive-compare-{index}-button", compare_label, _make_compare_handler(index))
        compare_button.setAttribute("aria-pressed", "true" if picked else "false")
        compare_button.setAttribute("aria-label", f"{compare_label}: {archive.record_label(record, index)}")
        _archive_button(buttons, f"archive-delete-{index}-button", "Delete", _make_archive_delete_handler(index))
        _found_button(buttons, f"archive-found-{index}-button")
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


# ===========================================================================
# O-5/O-6/O-7: "Found a New Settlement". The front door back to the scenario
# picker (K12), hard mode (K18) and consulting mode (K22): a confirm-gated
# action that FIRST files the current settlement in the archive (unless it is
# already filed, or has nothing in it), and only then resets the campaign in
# place (founding.found_new). If the archive write fails the whole thing is
# refused, so a settlement that has not been archived is never thrown away.
# The new settlement inherits one small founder's legacy (founding.py), from
# the settlement just filed, and nothing else.
# ===========================================================================
found_status = ""


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    """Same helper shape as SOL's: the shared ConfirmDialog when present, else
    (pytest's fake `js`, or a page without confirm-dialog.js) confirm at once."""
    window = _js_window()
    confirm_dialog = getattr(window, "ConfirmDialog", None) if window is not None else None
    if confirm_dialog is None:
        on_confirm()
        return
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        allowSkip=False,
        onConfirm=create_proxy(on_confirm),
    )


def _departing_is_inherited_only():
    """True when the settlement being left is an unplayed-beyond-its-start
    consulting case: its era was handed over, not reached, so it earns no
    legacy (the same fairness rule the era achievements follow)."""
    case = consulting.get(campaign.ui)
    if case is None:
        return False
    return sim.era_index(campaign.furthest_era) <= sim.era_index(consulting.CASES[case["case"]]["era"])


def pending_legacy():
    """The legacy entry the NEXT settlement would inherit, or None: from the
    current settlement (which founding archives first), or, when there is
    nothing worth archiving, from the newest archived settlement."""
    if founding.is_pristine(campaign):
        records = archive_load()
        record = records[-1] if records else None
    elif _departing_is_inherited_only():
        record = None
    else:
        record = current_record()
    return founding.make_legacy(record)


def _archive_departing():
    """Files the current settlement unless it is empty or already filed.
    True only when it is safe to leave it behind."""
    if founding.is_pristine(campaign):
        return True
    record = current_record(archive.clean_thumbnail(_capture_image(320, 0.7)))
    if record is None:
        return False
    records = archive_load()
    if records and archive.same_settlement(records[-1], record):
        return True
    return archive_store(archive.add_record(records, record))


def found_new_settlement():
    """Archive, then reset. Returns True when a new settlement was founded."""
    global found_status, sim_speed, season_progress, _last_tick, _archive_confirm_clear
    if campaign.revisiting is not None:
        found_status = "Return to the present before founding a new settlement."
        render()
        return False
    legacy_entry = pending_legacy()
    if not _archive_departing():
        found_status = (
            "The current settlement could not be filed in the archive (browser storage is "
            "unavailable), so nothing was changed."
        )
        render()
        return False
    earned = achievement_ids_earned()
    # K-2: the departing settlement's Legacy is banked first (by the difference), then the
    # player-level records (Dynasty, tokens used, banner, citizens switch) follow into the next one.
    banked, _info = _bank_current()
    carry = {key: campaign.ui[key] for key in founding.CARRY_KEYS if key in campaign.ui and key != "citizens"}
    if not _citizens_on():
        carry["citizens"] = {"off": True}
    if not founding.found_new(campaign, chronicle, legacy_entry, earned, carry):
        found_status = "A new settlement could not be founded, so nothing was changed."
        render()
        return False
    _rewind_clear()
    sim_speed = 0
    season_progress = 0.0
    _last_tick = time.time()
    _archive_confirm_clear = False
    del _compare_picks[:]
    sync_name_input()
    found_status = (
        "A new settlement is founded. The old one is filed in the archive. Pick a starting "
        "scenario, Hard Mode or a consulting case, then press 1x to begin."
    )
    if banked["gained"]:
        found_status += f" Its Legacy is banked: +{banked['gained']} points."
    render()
    _seed_achievement_toast_baseline()
    return True


def _found_confirm_message():
    parts = [
        "Found a new settlement? The current one is filed in your archive first, then a brand-new "
        "Tribal-era settlement begins, paused, with the scenario picker, Hard Mode and consulting "
        "cases open again."
    ]
    entry = pending_legacy()
    if entry is not None:
        legacy = founding.LEGACIES[entry["id"]]
        parts.append(
            f"It inherits one founder's legacy: {legacy['label']} ({founding.bonus_text(entry)}), "
            f"from a {sim.ERA_LABEL[entry['from_era']]}-era settlement."
        )
    else:
        parts.append("There is no founder's legacy to inherit yet.")
    return " ".join(parts)


def on_found_new_settlement(event=None):
    if campaign.revisiting is not None:
        global found_status
        found_status = "Return to the present before founding a new settlement."
        update_found_display()
        return
    _confirm_dialog_ask(
        "continuum-found-settlement",
        _found_confirm_message(),
        "Found a new settlement",
        found_new_settlement,
    )


def update_found_display():
    button = document.getElementById("found-settlement-button")
    button.disabled = campaign.revisiting is not None
    document.getElementById("found-settlement-status").innerText = found_status
    legacy_line = document.getElementById("legacy-display")
    text = founding.status_text(
        founding.get_legacy(campaign.ui), consulting.get(campaign.ui) is not None
    )
    legacy_line.innerText = text
    legacy_line.hidden = not text


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
    if founders_log_open:
        sync_name_input()
    update_founders_panel()


def on_add_founders_note(event=None):
    field = document.getElementById("founders-input")
    if add_founders_note(field.value):
        field.value = ""
        update_founders_panel()


# --- K-24: naming the settlement --------------------------------------------
# The name lives in campaign.ui (naming.py); the input in the Founder's Log
# window is only written to on open, on a suggestion and after a save, never on
# an ordinary render, so it never overwrites what the player is typing.
_name_roll = int(time.time() * 1000) % 100003


def settlement_name():
    return naming.get(campaign.ui)


def sync_name_input():
    document.getElementById("settlement-name-input").value = settlement_name()


def _name_status(text):
    document.getElementById("settlement-name-status").innerText = text


def on_name_suggest(event=None):
    global _name_roll
    _name_roll += 1
    suggestion = naming.suggest(state.era, _name_roll)
    document.getElementById("settlement-name-input").value = suggestion
    _name_status(f"Suggested: {suggestion}. Press Save name to keep it, or suggest another.")


def on_name_save(event=None):
    field = document.getElementById("settlement-name-input")
    stored = naming.set_name(campaign.ui, field.value)
    field.value = stored
    _name_status(f"Your settlement is named {stored}." if stored else "No name set. The settlement is unnamed.")
    render()


def on_name_keydown(event=None):
    if getattr(event, "key", None) == "Enter":
        on_name_save()


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


# --- K-14 post-mortem ---------------------------------------------------
# A report built on demand from the saved record (postmortem.py); opened from
# a button inside the Civilization Summary and closed from its own button.
# Session-only display state, never saved.
postmortem_open = False
_postmortem_proxies = []       # the panel's own Close button
_postmortem_open_proxies = []  # the Open/Close button inside the Civilization Summary


def on_toggle_postmortem(event=None):
    global postmortem_open
    postmortem_open = not postmortem_open
    update_postmortem_panel()
    update_summary_panel()  # its button's label follows


def _postmortem_button(parent, button_id, text, proxies):
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.innerText = text
    proxy = create_proxy(on_toggle_postmortem)
    proxies.append(proxy)
    button.addEventListener("click", proxy)
    parent.appendChild(button)
    return button


def _pm_text(parent, tag, css, text):
    element = document.createElement(tag)
    element.className = css
    element.innerText = text
    parent.appendChild(element)
    return element


def update_postmortem_panel():
    panel = document.getElementById("postmortem-panel")
    panel.hidden = not postmortem_open
    if not postmortem_open:
        return
    for proxy in _postmortem_proxies:
        proxy.destroy()
    del _postmortem_proxies[:]
    panel.innerHTML = ""
    report = postmortem.build(campaign)
    _pm_text(panel, "h2", "section-heading", "Post-mortem")
    _pm_text(
        panel, "p", "row-blurb",
        "A look back at this settlement in the style of an engineering post-mortem, written from the "
        "livability record, the per-season stats and your Council Minutes. The prompts are things to "
        "think about, not verdicts.",
    )
    if not report["ready"]:
        for note in report["notes"]:
            _pm_text(panel, "p", "status-line pm-line", note)
    else:
        for title, key, empty in (
            ("What went well", "went_well", "Nothing stood out yet."),
            ("What went wrong", "went_wrong", "Nothing went badly wrong."),
        ):
            _pm_text(panel, "h3", "summary-eras-heading", title)
            for line in report[key] or [empty]:
                _pm_text(panel, "p", "status-line pm-line", line)
        _pm_text(panel, "h3", "summary-eras-heading", "Root cause of the biggest livability drop")
        block = report["root_cause"]
        _pm_text(panel, "p", "status-line pm-line pm-line--head", block["headline"])
        for line in block["lines"]:
            _pm_text(panel, "p", "status-line pm-line", line)
        _pm_text(panel, "h3", "summary-eras-heading", "Three decisions to redo")
        if report["redo"]:
            for item in report["redo"]:
                row = document.createElement("div")
                row.className = "pm-decision"
                _pm_text(row, "p", "status-line pm-line pm-line--head", item["decision"])
                _pm_text(row, "p", "row-blurb pm-line", f"{item['when']}. {item['hint']}")
                panel.appendChild(row)
        else:
            _pm_text(panel, "p", "status-line pm-line", "None to show.")
        for note in report["notes"]:
            _pm_text(panel, "p", "row-blurb pm-line", note)
    actions = document.createElement("div")
    actions.className = "archive-actions"
    _postmortem_button(actions, "postmortem-close-button", "Close post-mortem", _postmortem_proxies)
    panel.appendChild(actions)


def on_toggle_summary_panel(event=None):
    global summary_panel_open
    summary_panel_open = not summary_panel_open
    update_summary_panel()


def _summary_stat_row(container, text):
    row = document.createElement("p")
    row.className = "status-line summary-line"
    row.innerText = text
    container.appendChild(row)


def _detach_copy_result_holder(panel):
    """Z-20: empties the summary panel but keeps the shared "Copy result" button's container (and so
    its listener and its "Copied" message) alive, returning it with whether it held keyboard focus."""
    holder = document.getElementById("summary-copy-result")
    focused = False
    try:
        focused = holder is not None and bool(holder.contains(document.activeElement))
    except Exception:  # noqa: BLE001 -- no focus API (tests)
        pass
    panel.innerHTML = ""
    return holder, focused


def _reattach_copy_result_holder(panel, held):
    holder, focused = held
    if holder is None:
        return
    panel.appendChild(holder)
    if focused:
        try:
            holder.querySelector("button").focus()
        except Exception:  # noqa: BLE001
            pass


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (it calls this by name through window.pyodide): the furthest era, seasons played, peak
    population and the peak sustainability score, from the same summary the panel shows."""
    data = summary.summary(campaign)
    stats = [
        data["furthest_era_label"] + " reached",
        {"n": data["total_seasons"], "one": "season", "many": "seasons"},
        f"peak population {data['peak_population']}",
    ]
    if data["peak_score"] is not None:
        stats.append(f"peak sustainability {data['peak_score']:.0f}/100")
    return json.dumps({"game": "Continuum", "score": f"{data['eras_completed']} of {data['eras_total']} eras", "stats": stats})


def update_summary_panel():
    toggle = document.getElementById("summary-toggle-button")
    panel = document.getElementById("summary-panel")
    toggle.innerText = "Hide Civilization Summary" if summary_panel_open else "📜 Civilization Summary"
    panel.hidden = not summary_panel_open
    if not summary_panel_open:
        return

    holder = _detach_copy_result_holder(panel)
    data = summary.summary(campaign)

    # K7: in-character stakeholder-report framing, K17: efficiency rank.
    statement = document.createElement("p")
    statement.className = "row-blurb summary-statement"
    statement.innerText = summary.stakeholder_statement(data, data["rank"], settlement_name())
    panel.appendChild(statement)
    if data["rank"]:
        _summary_stat_row(panel, f"Efficiency rank: {data['rank']} city.")
    # K-14: the post-mortem opens from here (its own proxy list, since the archive
    # section below destroys every proxy in `_archive_proxies` each time it rebuilds).
    for proxy in _postmortem_open_proxies:
        proxy.destroy()
    del _postmortem_open_proxies[:]
    pm_actions = document.createElement("div")
    pm_actions.className = "archive-actions"
    _postmortem_button(
        pm_actions, "postmortem-open-button",
        "Close the post-mortem report" if postmortem_open else "Open a post-mortem report",
        _postmortem_open_proxies,
    )
    panel.appendChild(pm_actions)
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
        _summary_stat_row(panel, f"This settlement has carried its story all the way to the {sim.ERA_LABEL[sim.ERA_ORDER[-1]]}.")
    if consulting.get(campaign.ui) is None:
        for line in par.lines(state.scenario, SEASON_SECONDS, par.get(campaign.ui), data["total_seasons"], play_seconds()):
            _summary_stat_row(panel, line)
    if data["has_revisited"]:
        _summary_stat_row(panel, "You've looked back at least once during this playthrough.")
    _summary_stat_row(panel, f"Achievements earned: {len(achievement_ids_earned())} of {len(ACHIEVEMENTS)}.")
    _reattach_copy_result_holder(panel, holder)

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
        # K-27/K-16: sparklines, deltas and the "why did that change" hover
        # come from the per-season stat history. A Look Back shows a past
        # snapshot, which that history does not describe, so they are left out.
        history = statlog.rows(campaign.ui) if campaign.revisiting is None else []
        container.className = "views-dashboard views-dashboard--spark" if history else "views-dashboard"
        sections = views.dashboard(
            state, effects, (done, total), techdebt.get(campaign.ui) if campaign.revisiting is None else None
        )
        if campaign.revisiting is None:
            sections = sections + _extra_dashboard_sections()
        for section in sections:
            block = document.createElement("div")
            block.className = "views-dash-section"
            heading = document.createElement("h3")
            heading.className = "summary-eras-heading"
            heading.innerText = section["title"]
            block.appendChild(heading)
            for label, value in section["rows"]:
                block.appendChild(_dashboard_row(label, value, history, effects))
            container.appendChild(block)
    elif views_tab == "map":
        hazard = _debt_hazard()
        sites = [] if _resting() else heritage.sites_before(state.era, campaign.ui)
        document.getElementById("views-map-svg").innerHTML = views.civic_map_svg(state, hazard, sites) + geography.map_svg(
            geography.generate(_geo_seed())
        )
        document.getElementById("views-map-caption").innerText = views.map_caption(state, hazard)
    else:
        document.getElementById("views-flow-svg").innerHTML = views.flow_svg(state, state.last_report)
        document.getElementById("views-flow-caption").innerText = views.flow_caption(state.last_report)


def _dashboard_row(label, value, history, effects):
    """One dashboard row: label, K-27 sparkline, value, K-16 delta + hover waterfall."""
    row = document.createElement("p")
    row.className = "views-dash-row"
    name = document.createElement("span")
    name.className = "views-dash-name"
    name.innerText = label
    row.appendChild(name)
    key = views.spark_key(label)
    if key and history:
        kind_format = lambda v: statlog.format_value(key, v)  # noqa: E731
        svg = views.sparkline_svg(statlog.series(history, key, views.SPARK_SEASONS), label, kind_format)
        if svg:
            spark = document.createElement("span")
            spark.className = "views-dash-spark"
            spark.innerHTML = svg
            row.appendChild(spark)
    number = document.createElement("span")
    number.className = "views-dash-value"
    number.innerText = value
    row.appendChild(number)
    if key and len(history) >= 2:
        change = explain.delta(history, key)
        if change is not None:
            delta_text = statlog.format_delta(key, change)
            chip = document.createElement("span")
            chip.className = "views-dash-delta"
            chip.innerText = delta_text
            chip.setAttribute("title", "Change over the last completed season")
            row.appendChild(chip)
            explained = explain.explain(key, history, state.last_report, effects)
            if explained is not None and explained["factors"]:
                row.className = "views-dash-row views-dash-row--why"
                row.setAttribute("tabindex", "0")
                row.setAttribute("role", "group")
                row.setAttribute(
                    "aria-label",
                    f"{label}: {value}. Last season {delta_text}. Why: " + "; ".join(explain.waterfall_lines(explained)),
                )
                row.appendChild(_why_popover(explained))
    return row


def _why_popover(explained):
    """The K-16 small waterfall: a signed line and a floating bar per factor."""
    pop = document.createElement("span")
    pop.className = "why-pop"
    pop.setAttribute("role", "tooltip")
    title = document.createElement("span")
    title.className = "why-title"
    title.innerText = f"Why {explained['label'].lower()} changed last season"
    pop.appendChild(title)
    for step in explain.waterfall_geometry(explained):
        line = document.createElement("span")
        line.className = "why-line why-line--net" if step["kind"] == "net" else "why-line"
        text = document.createElement("span")
        text.className = "why-name"
        text.innerText = step["label"]
        track = document.createElement("span")
        track.className = "why-track"
        bar = document.createElement("span")
        bar.className = f"why-bar why-bar--{step['kind']}"
        bar.style.left = f"{step['left']}%"
        bar.style.width = f"{step['width']}%"
        track.appendChild(bar)
        amount = document.createElement("span")
        amount.className = "why-amount"
        amount.innerText = explain.amount_text(step["amount"], explained["unit"])
        line.appendChild(text)
        line.appendChild(track)
        line.appendChild(amount)
        pop.appendChild(line)
    return pop


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
    document.getElementById("founded-display").innerText = naming.with_name(
        settlement_name(), f"Founded Year 1 · now Year {year}, {season_name}"
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


def _record_par():
    """K-26: stores the run's season count and time the moment the last era is entered."""
    if campaign.furthest_era != par.final_era():
        return False
    return par.record(
        campaign.ui,
        max(1, int(state.season) - 1),
        play_seconds(),
        state.scenario,
        already_inherited=consulting.get(campaign.ui) is not None,
    )


def _log_heritage_left_behind():
    """K-5: the era just left stays standing as a heritage site; say so once, in the log."""
    if _resting() or campaign.revisiting is not None:
        return
    for site in heritage.sites_before(state.era, campaign.ui):
        if site["era"] == sim.ERA_ORDER[sim.era_index(state.era) - 1]:
            chronicle.log_challenge(
                state.season, state.era,
                f"{site['name']} is left standing at the edge of town: {site['blurb']} Keep it for the "
                "culture it gives, or clear it (see Heritage sites).",
            )


def on_advance_era(event=None):
    if transition.attempt_transition(campaign):
        _rewind_clear()
        chronicle.log_challenge(
            state.season, state.era,
            f"A doctrine can now be adopted for the {sim.ERA_LABEL[state.era]} era (see Doctrines).",
        )
        _tick_play_time()
        _record_par()
        record_motion("era", sim.ERA_LABEL[state.era] + " era")
        _easter_egg(eastereggs.on_era(campaign.ui, state.era))
        _log_heritage_left_behind()
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
            hint = heritage.preview_text(era, campaign.ui)
            if hint and not _resting():
                note = document.createElement("p")
                note.className = "row-blurb heritage-preview"
                note.innerText = hint
                row.appendChild(note)

            container.appendChild(row)

    for era in list(_revisit_button_proxies):
        if era not in live_eras:
            _revisit_button_proxies.pop(era).destroy()


def _make_enter_revisit_handler(era):
    def handler(event=None):
        if campaign.enter_revisit(era):
            _rewind_clear()
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


def _well_supplied_holdings():
    report = state.last_report or {}
    return report.get("holdings_residents", 0) > 0 and report.get("outlying_served", 0.0) >= 1.0


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
    "reached_relay": lambda: _era_reached("relay"),
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
    "well_supplied_holdings": _well_supplied_holdings,
    "a_real_city": lambda: state.population >= A_REAL_CITY_POPULATION,
    "looking_back": lambda: campaign.has_revisited,
    # K-26: the par-time badges, from the result stored on entering the last era.
    "par_seasons": lambda: par.seasons_earned(par.get(campaign.ui)),
    "par_time": lambda: par.time_earned(par.get(campaign.ui), SEASON_SECONDS),
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
    # O-5: badges earned in an earlier settlement (kept in campaign.ui by
    # founding.found_new) stay earned; the live checks add this settlement's.
    before = set(founding.earned_before(campaign.ui, [entry["id"] for entry in ACHIEVEMENTS]))
    return [entry["id"] for entry in ACHIEVEMENTS if entry["id"] in before or ACHIEVEMENT_CHECKS[entry["id"]]()]


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
    # K-31: a "monument row": each card stands on a plinth with a drawn monument
    # for its era, laid out era by era. Order is chronological, then catalog order.
    ordered = sorted(
        enumerate(achievements_summary()),
        key=lambda pair: monuments.sort_key(pair[1]["id"], pair[0]),
    )
    for _index, entry in ordered:
        kind = monuments.kind_of(entry["id"])
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        card.dataset.achievementId = entry["id"]

        icon = document.createElement("div")
        icon.className = "monument-icon"
        icon.setAttribute("aria-hidden", "true")
        icon.innerHTML = monuments.icon_svg(kind, entry["earned"])
        card.appendChild(icon)

        era_caption = document.createElement("p")
        era_caption.className = "monument-caption"
        era_caption.innerText = monuments.caption(kind)
        card.appendChild(era_caption)

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        state_text = document.createElement("p")
        state_text.className = "monument-state"
        state_text.innerText = "Earned" if entry["earned"] else "Not yet earned"
        card.appendChild(state_text)

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
    render_real_world()


def render_real_world():
    """W2-continuum: the collapsible "In the real world" note. Purely
    presentational (reads only state.era, changes no game number)."""
    box = document.getElementById("real-world-note")
    example = info_content.real_world_example(state.era)
    box.hidden = example is None
    if example is None:
        return
    document.getElementById("real-world-text").innerText = f"In the real world: {example['title']}. {example['text']}"
    link = document.getElementById("real-world-source")
    link.innerText = f"Source: {example['source']} (read {info_content.REAL_WORLD_READ_DATE})"
    link.href = example["url"]


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
    tree runs to sixteen tiers across eight eras, so static markup for it
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
        cost.innerText = "—" if researched else f"{tree.cost_of(node.node_id):g}"
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
            button.innerText = f"Study ({tree.cost_of(node.node_id):g})"
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
            quick = _book_quick_build(building)
            if campaign.revisiting is None:
                _easter_egg(eastereggs.on_build(campaign.ui, state, building, quick))
        update_minutes_panel()
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_research_handler(node_id):
    def handler(event=None):
        if tree.research(node_id, state.resources):
            record_motion("research", tree.nodes[node_id].name)
            if campaign.revisiting is None:
                _easter_egg(eastereggs.on_research(campaign.ui, state, tree.nodes[node_id].tier))
        update_minutes_panel()
        chronicle.check_research(state, tree)
        render()
        _check_new_achievements_for_toast()
    return handler


# ===========================================================================
# U2: the optional Hamlet view (desktop only, off by default).
#
# A "Hearth and Hamlet"-style way to play: the controls live INSIDE the
# scene as clickable buildings, one per "thing" (see hamlet.py for the
# station list and what a station is), instead of the Work / Build /
# Research panels. This whole section is the DOM half; it owns no game
# rules. Every button below is wired to the exact same handler factory the
# ordinary panels use (`_make_assign_handler`, `_make_unassign_handler`,
# `_make_build_handler`, `_make_research_handler`,
# `_make_start_challenge_handler`, `on_advance_era`, ...), wrapped only to
# say what happened to a screen reader.
#
# Design calls worth knowing:
#   - The overlay is plain DOM (real <button>s), not 3D picking. hamlet.js
#     projects each chip onto its building in the 3D scene and also lets a
#     click on the 3D building itself press that same button, so mouse,
#     keyboard and screen reader all go through one code path. With no
#     WebGL, or with the 2D view chosen, the chips simply sit at their flat
#     top-down positions (the percentages set below) -- the mode still works.
#   - Chips are built once per era and then UPDATED IN PLACE on every
#     render. Seasons now tick on a clock, so a rebuild-everything render
#     would drop keyboard focus every few seconds.
#   - The ordinary Work / Build / Research / Civic / Era Progress panels are
#     hidden by CSS (the `hamlet-on` class on #game), not removed: they keep
#     rendering underneath, so switching the mode off is instant and lossless.
#   - A browser preference (localStorage), not part of the save, same category
#     as the text-size and reduce-motion settings.
# ===========================================================================
HAMLET_STORAGE_KEY = "continuum-hamlet-view"
# Wide enough to hold the stage, and a mouse-like pointer: this is a
# desktop-only pilot, so a phone or a touch tablet never sees the toggle.
HAMLET_MEDIA_QUERY = "(min-width: 960px) and (hover: hover) and (pointer: fine)"

hamlet_on = False
hamlet_town_open = False
_hamlet_built_key = None   # tuple of station ids the chips were built for
_hamlet_els = {}           # station id -> dict of that chip's elements
_hamlet_proxies = []       # click proxies for the chips (destroyed on rebuild)
_hamlet_town_key = None    # signature of the town panel's dynamic lists
_hamlet_town_proxies = []
_hamlet_town_els = {}


def _hamlet_storage_get():
    window = _js_window()
    if window is None:
        return None
    try:
        return window.localStorage.getItem(HAMLET_STORAGE_KEY)
    except Exception:
        return None


def _hamlet_storage_set(value):
    window = _js_window()
    if window is None:
        return False
    try:
        window.localStorage.setItem(HAMLET_STORAGE_KEY, value)
        return True
    except Exception:
        return False


def _hamlet_capable():
    """True when this browser can host the hamlet: a desktop-class screen
    and pointer. Without a `window` (the test harness) it is simply True."""
    window = _js_window()
    if window is None:
        return True
    try:
        return bool(window.matchMedia(HAMLET_MEDIA_QUERY).matches)
    except Exception:
        return False


def _pc_layout():
    """True on the Desktop boot (pc.html sets window.NOYVJ_LAYOUT = "pc"
    before anything else loads). There the Hamlet view is the way the game is
    played, not an option: it starts on and its toggle is hidden. Without a
    `window` (the test harness) it is False, so the Classic page and every
    existing test behave exactly as before."""
    window = _js_window()
    if window is None:
        return False
    try:
        return getattr(window, "NOYVJ_LAYOUT", None) == "pc"
    except Exception:
        return False


def hamlet_active():
    return hamlet_on and _hamlet_capable()


def on_toggle_hamlet(event=None):
    global hamlet_on
    hamlet_on = not hamlet_on
    _hamlet_storage_set("on" if hamlet_on else "off")
    render()
    _hamlet_say(
        "Hamlet view on. Click a building to use it." if hamlet_active()
        else "Hamlet view off."
    )


def on_hamlet_capability_change(event=None):
    """Called by hamlet.js when the screen crosses the desktop threshold
    (a resized window), so the mode switches on or off without a reload."""
    render()


def _hamlet_say(text):
    """One short line into the polite live region."""
    try:
        document.getElementById("hamlet-live").innerText = text
    except KeyError:
        pass


def _hamlet_el(tag, cls=None, text=None, element_id=None):
    element = document.createElement(tag)
    if cls:
        element.className = cls
    if text is not None:
        element.innerText = text
    if element_id:
        element.id = element_id
    return element


def _hamlet_wire(button, handler):
    proxy = create_proxy(handler)
    _hamlet_proxies.append(proxy)
    button.addEventListener("click", proxy)


def _hamlet_set_blocked(button, blocked):
    """Blocked buttons stay focusable (aria-disabled, not `disabled`), so a
    keyboard or screen-reader user can still land on a building and hear why
    it cannot be used right now."""
    button.setAttribute("aria-disabled", "true" if blocked else "false")
    if blocked:
        button.classList.add("hamlet-blocked")
    else:
        button.classList.remove("hamlet-blocked")


def _make_hamlet_assign_handler(role, label):
    inner = _make_assign_handler(role)

    def handler(event=None):
        before = state.allocation[role]
        inner(event)
        after = state.allocation[role]
        _hamlet_say(
            f"{label}: {after} working." if after != before
            else f"No one is idle to assign to {label}."
        )
    return handler


def _make_hamlet_unassign_handler(role, label):
    inner = _make_unassign_handler(role)

    def handler(event=None):
        before = state.allocation[role]
        inner(event)
        after = state.allocation[role]
        _hamlet_say(
            f"{label}: {after} working." if after != before
            else f"Nobody is working at {label}."
        )
    return handler


def _make_hamlet_build_handler(building):
    inner = _make_build_handler(building)

    def handler(event=None):
        before = state.buildings[building]
        inner(event)
        after = state.buildings[building]
        label = sim.BUILDING_LABEL[building]
        _hamlet_say(
            f"Built {label}. You now have {after}." if after != before
            else f"Not enough materials for {label}: it costs {sim.BUILDING_COST[building]:.0f}."
        )
    return handler


def _make_hamlet_research_handler(node_id):
    inner = _make_research_handler(node_id)

    def handler(event=None):
        was_known = tree.is_researched(node_id)
        inner(event)
        name = tree.nodes[node_id].name
        _hamlet_say(
            f"Studied {name}." if (tree.is_researched(node_id) and not was_known)
            else f"Not enough knowledge to study {name} yet."
        )
    return handler


def _make_hamlet_town_handler():
    def handler(event=None):
        global hamlet_town_open
        hamlet_town_open = not hamlet_town_open
        _hamlet_town_button_state()
        _hamlet_render_town(current_effects(), force=True)
        _hamlet_say("Town Centre open." if hamlet_town_open else "Town Centre closed.")
    return handler


def _hamlet_close_town(event=None):
    global hamlet_town_open
    hamlet_town_open = False
    _hamlet_town_button_state()
    _hamlet_render_town(current_effects(), force=True)
    _hamlet_focus(f"hamlet-{hamlet.TOWN_ID}-main")


def _hamlet_town_button_state():
    els = _hamlet_els.get(hamlet.TOWN_ID)
    if els:
        els["main"].setAttribute("aria-expanded", "true" if hamlet_town_open else "false")
        if hamlet_town_open:
            els["chip"].classList.add("hamlet-chip--open")
        else:
            els["chip"].classList.remove("hamlet-chip--open")


def _hamlet_focus(element_id):
    """Puts keyboard focus back on `element_id` if it still exists."""
    try:
        target = document.getElementById(element_id)
        if target is not None:
            target.focus()
            return True
    except Exception:
        pass
    return False


def _hamlet_active_id():
    try:
        active = getattr(document, "activeElement", None)
        return active.id if active is not None and active.id else None
    except Exception:
        return None


def _hamlet_build_chips(stations):
    """(Re)builds every chip. Only runs when the set of stations changes,
    i.e. on entering the mode and on each new era."""
    global _hamlet_built_key
    for proxy in _hamlet_proxies:
        proxy.destroy()
    del _hamlet_proxies[:]
    _hamlet_els.clear()
    container = document.getElementById("hamlet-chips")
    container.innerHTML = ""

    for station in stations:
        sid = station["id"]
        chip = _hamlet_el("div", "hamlet-chip", element_id=f"hamlet-chip-{sid}")
        chip.setAttribute("role", "group")
        chip.setAttribute("data-station", sid)
        chip.setAttribute("data-shape", station["shape"])
        x, z = hamlet.position(station)
        chip.setAttribute("data-hx", str(x))
        chip.setAttribute("data-hz", str(z))
        chip.setAttribute("data-count", "0")

        main = _hamlet_el("button", "hamlet-main", element_id=f"hamlet-{sid}-main")
        main.setAttribute("type", "button")
        icon = _hamlet_el("span", "hamlet-icon", station["emoji"])
        icon.setAttribute("aria-hidden", "true")
        name = _hamlet_el("span", "hamlet-name", station["label"])
        count = _hamlet_el("span", "hamlet-count")
        main.appendChild(icon)
        main.appendChild(name)
        main.appendChild(count)
        chip.appendChild(main)

        sub = _hamlet_el("span", "hamlet-sub")
        els = {"chip": chip, "main": main, "count": count, "sub": sub,
               "unassign": None, "build": None}

        if station["kind"] == "town":
            _hamlet_wire(main, _make_hamlet_town_handler())
            main.setAttribute("aria-expanded", "false")
            main.setAttribute("aria-controls", "hamlet-town-panel")
            chip.appendChild(sub)
        else:
            role, building = station["role"], station["building"]
            if role:
                # A workplace: [-] [caption] [+ build cost, pairs only] under
                # the building, so the whole control sits in one compact row.
                actions = _hamlet_el("div", "hamlet-actions")
                _hamlet_wire(main, _make_hamlet_assign_handler(role, station["label"]))
                minus = _hamlet_el("button", "hamlet-mini", "−", f"hamlet-{sid}-unassign")
                minus.setAttribute("type", "button")
                minus.setAttribute("aria-label", f"Take one worker off {sim.ROLE_LABEL[role]}")
                _hamlet_wire(minus, _make_hamlet_unassign_handler(role, station["label"]))
                actions.appendChild(minus)
                els["unassign"] = minus
                actions.appendChild(sub)
                if building:
                    buy = _hamlet_el("button", "hamlet-mini hamlet-buy", "", f"hamlet-{sid}-build")
                    buy.setAttribute("type", "button")
                    _hamlet_wire(buy, _make_hamlet_build_handler(building))
                    actions.appendChild(buy)
                    els["build"] = buy
                chip.appendChild(actions)
            else:
                _hamlet_wire(main, _make_hamlet_build_handler(building))
                chip.appendChild(sub)
        _hamlet_els[sid] = els
        container.appendChild(chip)
    _hamlet_built_key = tuple(s["id"] for s in stations)


def _hamlet_update_chips(stations, effects):
    for station in stations:
        view = hamlet.station_view(station, state, effects)
        els = _hamlet_els[station["id"]]
        chip, main = els["chip"], els["main"]
        els["count"].innerText = view["count_text"]
        els["sub"].innerText = view["sub_text"]
        els["sub"].hidden = not view["sub_text"]
        chip.setAttribute("data-count", str(view["count"] or 0))
        main.setAttribute("aria-label", view["aria_label"])
        main.title = view["title"]
        _hamlet_set_blocked(main, not view["primary_ok"])
        left, top = hamlet.flat_percent(view["x"], view["z"])
        chip.style.left = f"{left}%"
        chip.style.top = f"{top}%"
        chip.style.zIndex = str(int(50 + view["z"] * 10))
        if els["unassign"] is not None:
            _hamlet_set_blocked(els["unassign"], not view["can_unassign"])
        if els["build"] is not None:
            els["build"].innerText = f"＋{view['cost']:.0f}"
            els["build"].setAttribute(
                "aria-label",
                f"Build one more {sim.BUILDING_LABEL[station['building']]} for {view['cost']:.0f} materials",
            )
            _hamlet_set_blocked(els["build"], not view["can_build"])
    _hamlet_town_button_state()


def _hamlet_update_hud(effects):
    housing = state.housing_capacity(effects)
    score = sustainability.score(state, effects)
    label = sustainability.score_label(score, sustainability.is_hard_mode(state))
    resources = state.resources
    document.getElementById("hamlet-hud").innerText = (
        f"👥 {state.population}/{housing:.0f}  ·  🍖 {resources['food']:.0f}/"
        f"{state.food_storage_capacity(effects):.0f}  ·  🪵 {resources['materials']:.0f}  ·  "
        f"🔧 {resources['tools']:.1f}  ·  💡 {resources['knowledge']:.1f}  ·  "
        f"idle {state.idle_workers()}  ·  {sim.ERA_LABEL[state.era]}, season {state.season}  ·  "
        f"score {score:.0f} ({label})"
    )


# --- Desktop boot: the readouts as a HUD in the scene --------------------------------
# On the Desktop boot (pc.html) the side column of readouts is gone: the same numbers are
# drawn as a row of chips over the scene, and each chip opens a small dropdown with the
# detail and the trend ("+1 person per season"). The trend comes from forecast.py, a probe
# of the next season on a copy of the state, so it is exactly what the next season will do
# if nothing changes. The old readout elements keep updating (they are only moved out of
# the layout), and the Classic page never builds any of this.
PC_HUD_CHIPS = (
    ("population", "\U0001F465", "People"),
    ("food", "\U0001F356", "Food"),
    ("materials", "\U0001FAB5", "Materials"),
    ("tools", "\U0001F527", "Tools"),
    ("knowledge", "\U0001F4A1", "Knowledge"),
    ("sustainability", "\U0001F331", "Sustainability"),
)
_pc_hud_els = {}


def _pc_hud_build():
    stage = document.getElementById("hamlet-stage")
    bar = document.createElement("div")
    bar.id = "pc-hud"
    bar.className = "pc-hud"
    bar.setAttribute("role", "group")
    bar.setAttribute("aria-label", "Settlement readouts")
    for key, icon, label in PC_HUD_CHIPS:
        wrap = document.createElement("div")
        wrap.className = "pc-dropdown-wrap"
        toggle = document.createElement("button")
        toggle.type = "button"
        toggle.className = "pc-hud-chip"
        toggle.setAttribute("data-pc-dropdown", "1")
        toggle.setAttribute("aria-expanded", "false")
        toggle.setAttribute("aria-label", f"{label}: details and trend")
        icon_el = document.createElement("span")
        icon_el.className = "pc-hud-icon"
        icon_el.innerText = icon
        value_el = document.createElement("span")
        value_el.className = "pc-hud-value"
        caret = document.createElement("span")
        caret.className = "pc-hud-caret"
        caret.innerText = "\u25BE"
        toggle.appendChild(icon_el)
        toggle.appendChild(value_el)
        toggle.appendChild(caret)
        dropdown = document.createElement("div")
        dropdown.className = "pc-dropdown"
        dropdown.hidden = True
        dropdown.setAttribute("role", "group")
        dropdown.setAttribute("aria-label", f"{label} detail")
        wrap.appendChild(toggle)
        wrap.appendChild(dropdown)
        bar.appendChild(wrap)
        _pc_hud_els[key] = {"toggle": toggle, "value": value_el, "dropdown": dropdown}
    era = document.createElement("span")
    era.className = "pc-hud-era"
    bar.appendChild(era)
    _pc_hud_els["_era"] = {"el": era}
    setup = document.createElement("button")
    setup.type = "button"
    setup.className = "pc-hud-chip pc-hud-setup"
    setup.id = "pc-hud-setup"
    setup.title = "Pick the starting scenario before the first season"
    setup.addEventListener("click", create_proxy(_pc_hud_open_setup))
    bar.appendChild(setup)
    _pc_hud_els["_setup"] = {"el": setup}
    stage.appendChild(bar)


def _pc_hud_open_setup(event=None):
    opener = document.getElementById("pc-open-pc-setup-panel")
    if opener is not None:
        opener.click()


def _pc_hud_fill(dropdown, title, lines):
    dropdown.innerHTML = ""
    heading = document.createElement("strong")
    heading.innerText = title
    dropdown.appendChild(heading)
    for text in lines:
        row = document.createElement("p")
        row.innerText = text
        dropdown.appendChild(row)


def _pc_hud_update(effects):
    if not _pc_hud_els:
        _pc_hud_build()
    housing = state.housing_capacity(effects)
    resources = state.resources
    values = {
        "population": f"{state.population}/{housing:.0f}",
        "food": f"{resources['food']:.0f}/{state.food_storage_capacity(effects):.0f}",
        "materials": f"{resources['materials']:.0f}",
        "tools": f"{resources['tools']:.1f}",
        "knowledge": f"{resources['knowledge']:.1f}",
    }
    try:
        preview = forecast.preview(state, effects)
    except Exception:
        preview = None
    reading = sustainability.evaluate(state, effects)
    score = reading["score"]
    label = sustainability.score_label(score, sustainability.is_hard_mode(state))
    values["sustainability"] = f"{score:.0f}"
    for key, icon, name in PC_HUD_CHIPS:
        els = _pc_hud_els[key]
        els["value"].innerText = values[key]
        if key == "sustainability":
            lines = [f"{label}, {score:.0f} out of 100"]
            for component in sustainability.COMPONENTS:
                lines.append(f"{sustainability.COMPONENT_LABEL[component]}: {reading['components'][component]:.0f}")
            lines.append(sustainability.score_note(state, effects))
        elif preview is not None:
            lines = forecast.lines(key, preview[key])
            if key == "food":
                lines.append(f"Land health {state.land_health * 100:.0f}%")
        else:
            lines = ["Trend unavailable right now."]
        _pc_hud_fill(els["dropdown"], name, lines)
    _pc_hud_els["_era"]["el"].innerText = naming.with_name(
        settlement_name(),
        f"{sim.ERA_LABEL[state.era]}, season {state.season}  \u00B7  idle {state.idle_workers()}",
    )
    setup = _pc_hud_els["_setup"]["el"]
    show_setup = not _scenario_locked()
    setup.hidden = not show_setup
    if show_setup:
        setup.innerText = f"\U0001F3D5 {sim.scenario_config(state.scenario)['label']} \u00B7 change"


def _hamlet_town_signature(effects):
    nodes = hamlet.researchable_nodes(tree)
    research_part = tuple((n.node_id, tree.can_afford(n.node_id, state.resources)) for n in nodes)
    active_line = challenges.status_text(state)
    civic_part = (
        ("active", active_line) if active_line
        else ("offered", tuple(challenges.offered(state, effects)) if campaign.revisiting is None else ())
    )
    next_era = transition.next_era_for(state.era)
    ready = next_era is not None and transition.transition_ready(state, tree, effects)
    reasons = tuple(transition.missing_requirements(state, tree, effects)) if next_era else ()
    return (hamlet_town_open, state.era, research_part, hamlet.locked_count(tree),
            civic_part, next_era, ready, reasons)


def _hamlet_town_button(parent, button_id, text, aria_label, handler, blocked=False):
    button = _hamlet_el("button", "hamlet-mini hamlet-town-button", text, button_id)
    button.setAttribute("type", "button")
    button.setAttribute("aria-label", aria_label)
    proxy = create_proxy(handler)
    _hamlet_town_proxies.append(proxy)
    button.addEventListener("click", proxy)
    _hamlet_set_blocked(button, blocked)
    parent.appendChild(button)
    return button


def _hamlet_render_town(effects, force=False):
    """The Town Centre panel: research, civic challenges, era advance -- the
    non-per-building actions. Dynamic lists are rebuilt only when their
    signature changes, and focus is put back afterwards."""
    global _hamlet_town_key
    panel = document.getElementById("hamlet-town-panel")
    panel.hidden = not hamlet_town_open
    if not hamlet_town_open:
        _hamlet_town_key = None
        return
    key = _hamlet_town_signature(effects)
    if not force and key == _hamlet_town_key and _hamlet_town_els:
        _hamlet_town_els["knowledge"].innerText = f"Knowledge: {state.resources['knowledge']:.1f}"
        return
    _hamlet_town_key = key
    previous_focus = _hamlet_active_id()

    for proxy in _hamlet_town_proxies:
        proxy.destroy()
    del _hamlet_town_proxies[:]
    _hamlet_town_els.clear()
    panel.innerHTML = ""
    panel.setAttribute("role", "region")
    panel.setAttribute("aria-label", "Town Centre: research, civic challenges, next era")
    panel.setAttribute("tabindex", "-1")

    head = _hamlet_el("div", "hamlet-town-head")
    head.appendChild(_hamlet_el("strong", None, f"{hamlet.TOWN_EMOJI} {hamlet.TOWN_LABEL}"))
    _hamlet_town_button(head, "hamlet-town-close", "Close", "Close the Town Centre panel",
                        _hamlet_close_town)
    panel.appendChild(head)
    knowledge = _hamlet_el("p", "hamlet-town-line",
                           f"Knowledge: {state.resources['knowledge']:.1f}", "hamlet-town-knowledge")
    panel.appendChild(knowledge)
    _hamlet_town_els["knowledge"] = knowledge

    # --- research ---
    panel.appendChild(_hamlet_el("h3", "hamlet-town-heading", "Research"))
    nodes = hamlet.researchable_nodes(tree)
    if not nodes:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line", "Nothing to study right now."))
    for node in nodes:
        row = _hamlet_el("div", "hamlet-town-row")
        effect = research.describe_effects(node)
        affordable = tree.can_afford(node.node_id, state.resources)
        row.appendChild(_hamlet_el(
            "span", "hamlet-town-name", f"{node.name} · {research.BRANCH_LABEL[node.branch]}"))
        row.title = f"{node.blurb} Effect: {effect}"
        _hamlet_town_button(
            row, f"hamlet-study-{node.node_id}", f"Study {tree.cost_of(node.node_id):g}",
            f"Study {node.name}: {tree.cost_of(node.node_id):g} knowledge. Effect: {effect}."
            + ("" if affordable else " Not enough knowledge yet."),
            _make_hamlet_research_handler(node.node_id), blocked=not affordable)
        panel.appendChild(row)
    locked = hamlet.locked_count(tree)
    if locked:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line hamlet-town-dim", f"{locked} more still locked."))

    # --- civic challenges ---
    panel.appendChild(_hamlet_el("h3", "hamlet-town-heading", "Civic challenges"))
    active_line = challenges.status_text(state)
    if active_line:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line", active_line))
        row = _hamlet_el("div", "hamlet-town-row")
        _hamlet_town_button(row, "hamlet-challenge-abandon", "Abandon",
                            "Abandon the active civic challenge", on_abandon_challenge)
        panel.appendChild(row)
    elif campaign.revisiting is not None:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line hamlet-town-dim",
                                     "Not available while looking back."))
    else:
        offered = challenges.offered(state, effects)
        if not offered:
            panel.appendChild(_hamlet_el("p", "hamlet-town-line hamlet-town-dim",
                                         "None on offer right now."))
        for cid in offered:
            spec = challenges.CHALLENGES[cid]
            row = _hamlet_el("div", "hamlet-town-row")
            row.appendChild(_hamlet_el("span", "hamlet-town-name",
                                       f"{spec['label']} ({spec['seasons']} seasons)"))
            row.title = f"{spec['blurb']} Reward: +{challenges.reward_for(state.era):.0f} knowledge."
            _hamlet_town_button(row, f"hamlet-challenge-{cid}", "Accept",
                                f"Accept the civic challenge {spec['label']}. {spec['blurb']}",
                                _make_start_challenge_handler(cid))
            panel.appendChild(row)

    # --- next era ---
    panel.appendChild(_hamlet_el("h3", "hamlet-town-heading", "Next era"))
    next_era = transition.next_era_for(state.era)
    if next_era is None:
        panel.appendChild(_hamlet_el("p", "hamlet-town-line hamlet-town-dim",
                                     "Nothing more to reach from here yet."))
    else:
        ready = transition.transition_ready(state, tree, effects)
        reasons = " ".join(transition.missing_requirements(state, tree, effects))
        panel.appendChild(_hamlet_el(
            "p", "hamlet-town-line",
            f"Ready to move into the {sim.ERA_LABEL[next_era]} era." if ready
            else f"Working toward the {sim.ERA_LABEL[next_era]} era. {reasons}"))
        row = _hamlet_el("div", "hamlet-town-row")
        _hamlet_town_button(row, "hamlet-advance-era", f"Advance to {sim.ERA_LABEL[next_era]}",
                            f"Advance to the {sim.ERA_LABEL[next_era]} era", on_advance_era,
                            blocked=not ready)
        panel.appendChild(row)

    if previous_focus and previous_focus.startswith("hamlet-") and previous_focus != f"hamlet-{hamlet.TOWN_ID}-main":
        if not _hamlet_focus(previous_focus):
            panel.focus()


def render_hamlet(effects=None):
    """Draws (or, when the mode is off, quietly hides) the Hamlet view. Off
    by default: with the mode off this only sets the toggle button and leaves
    every existing panel exactly as it was."""
    if effects is None:
        effects = current_effects()
    capable = _hamlet_capable()
    active = hamlet_on and capable
    toggle = document.getElementById("hamlet-toggle-button")
    toggle.hidden = (not capable) or _pc_layout()
    toggle.innerText = f"🏘 Hamlet view: {'On' if hamlet_on else 'Off'}"
    toggle.setAttribute("aria-pressed", "true" if hamlet_on else "false")
    document.getElementById("game").classList.toggle("hamlet-on", active)
    document.getElementById("hamlet-stage").hidden = not active
    if not active:
        return

    stations = hamlet.stations_for_era(state.era)
    if _hamlet_built_key != tuple(s["id"] for s in stations):
        _hamlet_build_chips(stations)
    _hamlet_update_chips(stations, effects)
    _hamlet_update_hud(effects)
    if _pc_layout():
        _pc_hud_update(effects)
    _hamlet_render_town(effects)


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
    "industrial": 14.0, "digital": 16.0, "space": 18.0, "relay": 20.0,
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
    global found_status, _rewind_snapshot
    # K-17: remember the world just before the season runs, so it can be unwound once.
    _rewind_snapshot = rewind.capture(campaign)
    effects = current_effects()
    # O-7: a pending founder's legacy arrives with the opening season, once.
    delivered = founding.apply_legacy(campaign, consulting.get(campaign.ui) is not None)
    if delivered is not None:
        legacy = founding.LEGACIES[delivered["id"]]
        chronicle.log_challenge(
            state.season,
            state.era,
            f"Founder's legacy arrives: {legacy['label']} ({founding.bonus_text(delivered)}). {legacy['blurb']}",
        )
    # K-2: the Dynasty's starting perks arrive with the opening season, once (they rest in a
    # challenge run or consulting case, and the turn is used up either way).
    if campaign.revisiting is None:
        bonuses = dynasty.apply_start(campaign, _resting())
        if bonuses:
            chronicle.log_challenge(state.season, state.era, _dynasty_start_message(bonuses))
            effects = current_effects()
    found_status = ""
    report = state.advance_season(effects)
    if campaign.revisiting is None:
        settle = techdebt.after_season(campaign.ui, state)
        if settle["refactored"]:
            _easter_egg(eastereggs.on_refactor(campaign.ui, state))
            chronicle.log_challenge(
                state.season,
                state.era,
                f"Refactor season complete: technical debt eased from {settle['before'] * 100:.0f}% "
                f"to {settle['after'] * 100:.0f}%. The crews spent the season rewriting, not producing.",
            )
        elif settle["warn"]:
            chronicle.log_challenge(
                state.season,
                state.era,
                "Technical debt has passed 50%: the old shortcuts are failing more often and upkeep is "
                "climbing. A refactor season would pay it down.",
            )
    state.record_score(sustainability.score(state, effects))
    if campaign.revisiting is None:
        _beyond_after_season(sustainability.score(state, effects))
    if campaign.revisiting is None:
        run_result = challengerun.after_season(campaign, sustainability.score(state, effects))
        if run_result is not None:
            _finish_challenge_run(run_result)
    trajectory.record(state, report, sustainability.livability(state, effects) * 100.0)
    if campaign.revisiting is None:
        # K-27/K-16/K-18/K-14: one row of stats per completed season (statlog.py).
        statlog.record(campaign.ui, state, effects, report, len(tree.researched))
    before = consulting.get(campaign.ui)
    after = consulting.step(campaign, effects)
    if after is not None and after["result"] and (before is None or before["result"] is None):
        chronicle.log_challenge(state.season, state.era, consulting.status_text(after, state))
    event = challenges.after_season(state, report, effects)
    if event is not None:
        chronicle.log_challenge(state.season, state.era, event["text"])
    chronicle.check_population(state)
    chronicle.check_livability(state, effects)
    if campaign.revisiting is None:
        _run_standing_orders(effects)
    if campaign.revisiting is None:
        digital_rows = sum(
            1 for row in statlog.rows(campaign.ui) if int(statlog.value(row, "era")) == sim.era_index(eastereggs.DIGITAL_ERA)
        )
        _easter_egg(eastereggs.on_season(campaign.ui, state, digital_rows))
        # K-8: the council's advice for the season that just ended is judged now; new advice is
        # issued when the panel next draws (so a closed council costs nothing).
        advisors.settle(campaign.ui, state, current_effects())
    if campaign.revisiting is None:
        _citizens_after_season(report)
        if _neighbours_allowed():
            for text in neighbours.after_season(campaign.ui, state.season, state.resources, _player_era_index()):
                chronicle.log_challenge(state.season, state.era, text)
        _bank_if_collapsed()
    _tick_play_time()
    render()
    _check_new_achievements_for_toast()


# ===========================================================================
# Round 3, third batch: K-2 Dynasty (and K-20 banners), K-6 era doctrines, K-17 the
# rewind token, K-15/K-28 notable citizens and the citizen of the season, and K-7
# computer-controlled neighbouring settlements. The rules live in dynasty.py, banners.py,
# doctrines.py, rewind.py, citizens.py and neighbours.py; this is the DOM half.
# ===========================================================================
DYNASTY_STORAGE_KEY = "continuum-dynasty-v1"
_rewind_snapshot = None
dynasty_open = False
doctrines_open = False
citizens_open = False
neighbours_open = False
_dynasty_view = None
_dynasty_proxies = []
_dynasty_status = ""
_banner_proxies = []
_doctrine_proxies = []
_citizens_proxies = []
_neighbour_proxies = []
neighbours_status = ""


def _resting():
    """True while a challenge run or consulting case is the active run: every earned advantage
    (Dynasty perks, citizen bonuses, rewinds, neighbours) rests so those runs stay comparable."""
    return challengerun.get(campaign.ui) is not None or consulting.get(campaign.ui) is not None


def _rest_reason():
    if challengerun.get(campaign.ui) is not None:
        return "a challenge run is the active run, so its score stays comparable."
    if consulting.get(campaign.ui) is not None:
        return "a consulting case is the active run, so its goal stays comparable."
    return ""


def _inherited_era():
    case = consulting.get(campaign.ui)
    return consulting.CASES[case["case"]]["era"] if case is not None else None


def _seed_hint():
    return int(time.time()) % 2147483647 or 1


def _sync_tree_costs():
    """Doctrines make some research branches cheaper; the tree is told each time effects are read."""
    if campaign.revisiting is not None:
        tree.cost_mults = {}
        return
    tree.cost_mults = doctrines.cost_multipliers(campaign.ui, dynasty.doctrine_edge(campaign.ui, _resting()))


# --- per-browser copy of the Dynasty (so a reload or an older save never takes progress away) --------------
def _dynasty_local_load():
    window = _js_window()
    if window is None:
        return None
    try:
        raw = window.localStorage.getItem(DYNASTY_STORAGE_KEY)
        return json.loads(raw) if isinstance(raw, str) else None
    except Exception:
        return None


def _dynasty_local_store():
    window = _js_window()
    if window is None:
        return
    record = dynasty.get(campaign.ui)
    try:
        window.localStorage.setItem(DYNASTY_STORAGE_KEY, json.dumps(record))
    except Exception:
        pass


def _adopt_local_dynasty():
    """Merges this browser's Dynasty with the one in the live save (neither loses progress)."""
    local = _dynasty_local_load()
    if local is None:
        return
    merged = dynasty.merge(campaign.ui.get(dynasty.KEY), local)
    if merged != dynasty.get(campaign.ui):
        dynasty.put(campaign.ui, merged)


# --- K-2 Dynasty ----------------------------------------------------------------------------------------
def _rank_names():
    return [name for _need, name in dynasty.RANKS]


def _bank_current():
    """Banks the live settlement's Legacy (by the difference). Returns (result, info)."""
    info = dynasty.run_info(campaign, _inherited_era())
    result = dynasty.bank(campaign.ui, info)
    if result["gained"] or result["first"]:
        _dynasty_local_store()
    return result, info


def _banked_text(result):
    if result["points"] <= 0:
        return (
            f"A settlement is only worth banking once it has lived {dynasty.MIN_SEASONS_TO_BANK} seasons; "
            "this one has not yet."
        )
    if result["gained"] <= 0:
        return f"Already banked: this settlement is worth {result['points']} Legacy points and all of them are in."
    return f"Banked {result['gained']} Legacy points ({result['total']} earned in all)."


def on_toggle_dynasty(event=None):
    global dynasty_open
    dynasty_open = not dynasty_open
    update_dynasty_panel()


def on_dynasty_bank(event=None):
    global _dynasty_status
    if campaign.revisiting is not None:
        _dynasty_status = "Return to the present before banking."
    else:
        result, _info = _bank_current()
        _dynasty_status = _banked_text(result)
    render()


def on_dynasty_off(event=None):
    record = dynasty.get(campaign.ui)
    dynasty.set_off(campaign.ui, not record["off"])
    _dynasty_local_store()
    render()


def _dynasty_buy(node_id):
    result = dynasty.buy(campaign.ui, node_id)
    if result["ok"]:
        _dynasty_local_store()
        render()
    return result


def _dynasty_refund(node_id):
    result = dynasty.refund(campaign.ui, node_id)
    if result["ok"]:
        _dynasty_local_store()
        render()
    return result


def _dynasty_refund_all():
    result = dynasty.refund_all(campaign.ui)
    _dynasty_local_store()
    render()
    return result


def _to_js(value):
    try:
        from js import Object  # noqa: PLC0415
        from pyodide.ffi import to_js  # noqa: PLC0415
    except ImportError:
        return None
    return to_js(value, dict_converter=Object.fromEntries)


def _render_dynasty_tree():
    global _dynasty_view
    window = _js_window()
    skill_view = getattr(window, "NoyvjSkillTree", None) if window is not None else None
    container = document.getElementById("dynasty-tree")
    if skill_view is None:
        return
    record = dynasty.get(campaign.ui)
    if _dynasty_view is None:
        if not _dynasty_proxies:
            _dynasty_proxies.extend([
                create_proxy(lambda node_id, node=None: _dynasty_buy(str(node_id))),
                create_proxy(lambda node_id, node=None: _dynasty_refund(str(node_id))),
                create_proxy(lambda: _dynasty_refund_all()),
            ])
        buy, refund, refund_all = _dynasty_proxies
        options = _to_js({
            "tree": dynasty.DYNASTY_TREE, "owned": list(record["owned"]), "earned": record["earned"],
            "refundNodes": True, "onBuy": buy, "onRefund": refund, "onRefundAll": refund_all,
        })
        if options is not None:
            _dynasty_view = skill_view.render(container, options)
        return
    update = _to_js({"owned": list(record["owned"]), "earned": record["earned"]})
    if update is not None:
        _dynasty_view.update(update)


def _make_banner_handler(kind, item_id):
    def handler(event=None):
        banner_id = item_id if kind == "banner" else None
        flourish_id = item_id if kind == "flourish" else None
        ok, _reason = banners.choose(
            campaign.ui, banner_id, flourish_id, set(achievement_ids_earned()),
            dynasty.rank_index(dynasty.get(campaign.ui)["earned"]),
        )
        if ok:
            render()
    return handler


def _achievement_names():
    return {entry["id"]: entry["label"] for entry in ACHIEVEMENTS}


def _render_banner_picker():
    for proxy in _banner_proxies:
        proxy.destroy()
    del _banner_proxies[:]
    holder = document.getElementById("banner-list")
    holder.innerHTML = ""
    earned = set(achievement_ids_earned())
    rank_index = dynasty.rank_index(dynasty.get(campaign.ui)["earned"])
    choice = banners.effective(campaign.ui, earned, rank_index)
    names = _achievement_names()
    for heading, kind, catalog, current in (
        ("Banners", "banner", banners.BANNERS, choice["banner"]),
        ("Skyline flourishes", "flourish", banners.FLOURISHES, choice["flourish"]),
    ):
        title = document.createElement("h4")
        title.className = "banner-heading"
        title.innerText = heading
        holder.appendChild(title)
        row = document.createElement("div")
        row.className = "banner-row"
        for item in catalog:
            unlocked = banners.is_unlocked(item, earned, rank_index)
            card = document.createElement("div")
            card.className = "banner-card" + (" banner-card--locked" if not unlocked else "")
            picture = document.createElement("span")
            picture.className = "banner-picture"
            picture.innerHTML = (
                banners.banner_svg(item["id"], 44) if kind == "banner" else banners.flourish_svg(item["id"], 120)
            ) if unlocked else ""
            card.appendChild(picture)
            button = document.createElement("button")
            button.id = f"{kind}-{item['id']}-button"
            button.className = "secondary banner-button"
            button.type = "button"
            selected = item["id"] == current
            button.innerText = ("✓ " if selected else ("" if unlocked else "🔒 ")) + item["label"]
            button.disabled = not unlocked
            button.setAttribute("aria-pressed", "true" if selected else "false")
            if not unlocked:
                button.title = banners.unlock_text(item, names, _rank_names())
                button.setAttribute("aria-label", f"{item['label']}, locked. {button.title}")
            proxy = create_proxy(_make_banner_handler(kind, item["id"]))
            _banner_proxies.append(proxy)
            button.addEventListener("click", proxy)
            card.appendChild(button)
            if not unlocked:
                hint = document.createElement("span")
                hint.className = "banner-hint"
                hint.innerText = banners.unlock_text(item, names, _rank_names())
                card.appendChild(hint)
            row.appendChild(card)
        holder.appendChild(row)


def update_dynasty_panel():
    record = dynasty.get(campaign.ui)
    toggle = document.getElementById("dynasty-toggle-button")
    free = dynasty.points_free(record)
    toggle.innerText = "Hide Dynasty" if dynasty_open else (f"🏰 Dynasty ({free} pts)" if free else "🏰 Dynasty")
    panel = document.getElementById("dynasty-panel")
    panel.hidden = not dynasty_open
    if not dynasty_open:
        return
    resting = _resting()
    lines = dynasty.status_lines(campaign.ui, resting, _rest_reason())
    info = dynasty.run_info(campaign, _inherited_era())
    run = dynasty.get_run(campaign.ui)
    lines.append(
        f"This settlement is worth {info['points']} Legacy points so far ({run['banked']} banked). "
        "Points are banked when you found a new settlement or when it collapses, or any time with the button below."
    )
    document.getElementById("dynasty-summary").innerText = " ".join(lines)
    off = document.getElementById("dynasty-off-button")
    off.innerText = f"Dynasty perks: {'OFF' if record['off'] else 'ON'}"
    off.setAttribute("aria-pressed", "false" if record["off"] else "true")
    bank_button = document.getElementById("dynasty-bank-button")
    bank_button.disabled = campaign.revisiting is not None
    document.getElementById("dynasty-bank-status").innerText = _dynasty_status
    _render_dynasty_tree()
    _render_banner_picker()


def _dynasty_start_message(bonuses):
    return f"Dynasty heritage arrives with the first season: {dynasty.start_text(bonuses)}."


# --- K-6 doctrines ----------------------------------------------------------------------------------------
def on_toggle_doctrines(event=None):
    global doctrines_open
    doctrines_open = not doctrines_open
    update_doctrines_panel()


def _make_doctrine_handler(doctrine_id):
    def handler(event=None):
        if campaign.revisiting is not None:
            return
        era = state.era
        ok, _reason = doctrines.choose(campaign.ui, era, doctrine_id)
        if ok:
            line = doctrines.log_line(era, doctrine_id)
            add_founders_note(line)
            chronicle.log_challenge(state.season, state.era, line)
            update_founders_panel()
            render()
    return handler


def update_doctrines_panel():
    open_now = campaign.revisiting is None and doctrines.is_open(campaign.ui, state.era)
    toggle = document.getElementById("doctrines-toggle-button")
    toggle.innerText = "Hide Doctrines" if doctrines_open else ("⚖️ Doctrines (choose)" if open_now else "⚖️ Doctrines")
    panel = document.getElementById("doctrines-panel")
    panel.hidden = not doctrines_open
    if not doctrines_open:
        return
    for proxy in _doctrine_proxies:
        proxy.destroy()
    del _doctrine_proxies[:]
    edge = dynasty.doctrine_edge(campaign.ui, _resting())
    chosen = doctrines.chosen_for(campaign.ui, state.era)
    if state.era == sim.FIRST_ERA:
        status = "Doctrines begin with your first era transition. Enter the Agrarian era to adopt one."
    elif chosen:
        status = f"The {sim.ERA_LABEL[state.era]} era follows the {doctrines.DOCTRINES[chosen]['label']} doctrine."
    elif campaign.revisiting is not None:
        status = "Return to the present to adopt a doctrine."
    else:
        status = f"Choose a doctrine for the {sim.ERA_LABEL[state.era]} era. The choice is final for this era."
    if edge:
        status += f" Schools of Thought makes each doctrine's main discount {edge} points deeper."
    document.getElementById("doctrines-status").innerText = status
    holder = document.getElementById("doctrines-list")
    holder.innerHTML = ""
    counts = doctrines.counts(campaign.ui)
    for doctrine_id, info in doctrines.DOCTRINES.items():
        card = document.createElement("div")
        card.className = "doctrine-card"
        for css, tag, text in (
            ("doctrine-name", "h3", info["label"] + (" (entrenched)" if counts.get(doctrine_id, 0) >= 2 else "")),
            ("row-blurb", "p", info["blurb"]),
            ("status-line", "p", doctrines.discount_text(doctrine_id) + "; " + doctrines.effect_text(doctrine_id) + "."),
        ):
            node = document.createElement(tag)
            node.className = css
            node.innerText = text
            card.appendChild(node)
        button = document.createElement("button")
        button.id = f"doctrine-{doctrine_id}-button"
        button.className = "secondary"
        button.type = "button"
        button.innerText = "✓ Adopted for this era" if chosen == doctrine_id else f"Adopt the {info['label']} doctrine"
        button.disabled = not open_now
        proxy = create_proxy(_make_doctrine_handler(doctrine_id))
        _doctrine_proxies.append(proxy)
        button.addEventListener("click", proxy)
        card.appendChild(button)
        holder.appendChild(card)
    history = document.getElementById("doctrines-history")
    history.innerHTML = ""
    rows = doctrines.history(campaign.ui)
    if not rows:
        node = document.createElement("p")
        node.className = "row-blurb"
        node.innerText = "No doctrine adopted yet."
        history.appendChild(node)
    for era, doctrine_id in rows:
        node = document.createElement("p")
        node.className = "status-line"
        node.innerText = f"{sim.ERA_LABEL[era]} era: {doctrines.DOCTRINES[doctrine_id]['label']}"
        history.appendChild(node)


# --- K-17 rewind ------------------------------------------------------------------------------------------
def _rewind_tokens():
    return rewind.tokens_left(
        campaign.ui, len(achievement_ids_earned()), dynasty.rewind_perk_tokens(campaign.ui)
    )


def _rewind_clear():
    global _rewind_snapshot
    _rewind_snapshot = None


def on_rewind(event=None):
    global _rewind_snapshot
    reason = rewind.refusal(_rewind_snapshot, campaign, _rewind_tokens(), _resting())
    if reason:
        _display_toast(reason)
        return
    ok, cost = rewind.apply(campaign, _rewind_snapshot)
    _rewind_snapshot = None
    if not ok:
        _display_toast("The season could not be unwound.")
        return
    set_speed(0)
    chronicle.log_challenge(
        state.season, state.era,
        f"A season was unwound. It cost a rewind token and {cost:.1f} knowledge; time is held until you choose a speed.",
    )
    sync_name_input()
    _dynasty_local_store()
    render()
    _seed_achievement_toast_baseline()
    _display_toast(f"Season unwound. {cost:.1f} knowledge spent, {_rewind_tokens()} rewind tokens left.")


def update_rewind_button():
    button = document.getElementById("rewind-button")
    tokens = _rewind_tokens()
    button.innerText = f"↶ Rewind ({tokens})"
    reason = rewind.refusal(_rewind_snapshot, campaign, tokens, _resting())
    text = rewind.preview(_rewind_snapshot, campaign, tokens, _resting())
    button.disabled = bool(reason)
    button.title = text
    button.setAttribute("aria-label", f"Rewind one season, {tokens} tokens. {text}")


# --- K-15 / K-28 citizens ---------------------------------------------------------------------------------
def _citizens_on():
    return citizens.is_on(campaign.ui)


def on_toggle_citizens(event=None):
    global citizens_open
    citizens_open = not citizens_open
    if citizens_open and campaign.revisiting is None and _citizens_on() and state.season > 1:
        citizens.ensure_roster(campaign.ui, campaign.furthest_era, _seed_hint())
    update_citizens_panel()


def on_citizens_off(event=None):
    citizens.set_off(campaign.ui, _citizens_on())
    render()


def _citizen_effects_text():
    return citizens.bonus_text(citizens.bonus_deltas(campaign.ui, state.era, _resting())) or "none right now"


def update_spotlight_card():
    card = document.getElementById("citizen-spotlight")
    spot = citizens.latest_spot(campaign.ui) if _citizens_on() else None
    card.hidden = spot is None
    if spot is not None:
        year, season_name = year_and_season(max(1, spot["season"]))
        card.innerText = f"Citizen of the season, Year {year} {season_name}: {spot['name']}. {spot['line']}"


def update_citizens_panel():
    toggle = document.getElementById("citizens-toggle-button")
    toggle.innerText = "Hide Citizens" if citizens_open else "🧑 Citizens"
    panel = document.getElementById("citizens-panel")
    panel.hidden = not citizens_open
    if not citizens_open:
        return
    on = _citizens_on()
    off_button = document.getElementById("citizens-off-button")
    off_button.innerText = f"Notable citizens: {'ON' if on else 'OFF'}"
    off_button.setAttribute("aria-pressed", "true" if on else "false")
    holder = document.getElementById("citizens-list")
    holder.innerHTML = ""
    record = citizens.get(campaign.ui)
    if not on:
        text = "Notable citizens are switched off: no citizens appear and none give a bonus."
    elif not record["roster"]:
        text = "Citizens appear as the settlement lives its first seasons. They are invented people."
    else:
        text = (
            f"Invented people who follow the settlement from era to era. Their standing bonus right now: "
            f"{_citizen_effects_text()}." + (" (Resting during a challenge run or consulting case.)" if _resting() else "")
        )
    document.getElementById("citizens-bonus").innerText = text
    for citizen in reversed(record["roster"]) if on else []:
        stage = citizens.stage_of(citizen, state.era)
        card = document.createElement("div")
        card.className = "citizen-card"
        title = document.createElement("h3")
        title.className = "citizen-name"
        title.innerText = f"{citizen['name']}, {stage['title']}"
        card.appendChild(title)
        for line in citizens.thread(citizen, state.era):
            node = document.createElement("p")
            node.className = "row-blurb citizen-thread"
            node.innerText = line
            card.appendChild(node)
        holder.appendChild(card)
    spots = document.getElementById("citizens-spots")
    spots.innerHTML = ""
    for spot in reversed(record["spots"]) if on else []:
        year, season_name = year_and_season(max(1, spot["season"]))
        node = document.createElement("p")
        node.className = "status-line"
        node.innerText = f"Year {year} {season_name}: {spot['name']}. {spot['line']}"
        spots.appendChild(node)


def _citizens_after_season(report):
    """New children for new eras, and the citizen of the season."""
    if campaign.revisiting is not None or not _citizens_on():
        return
    added = citizens.ensure_roster(campaign.ui, campaign.furthest_era, _seed_hint())
    for citizen in added:
        chronicle.log_challenge(
            state.season, state.era,
            f"{citizen['name']} is born among the {citizens.ERA_TRADES[citizen['born']]['household']}.",
        )
    citizens.make_spotlight(campaign.ui, state.era, report.get("season", state.season - 1), report, minutes.entries(campaign.ui))


# --- K-7 neighbours ---------------------------------------------------------------------------------------
def on_toggle_neighbours(event=None):
    global neighbours_open
    neighbours_open = not neighbours_open
    if neighbours_open:
        neighbours.ensure(campaign.ui, _seed_hint()) if campaign.revisiting is None else None
    update_neighbours_panel()


def _neighbours_allowed():
    return campaign.revisiting is None and not _resting()


def _player_era_index():
    return sim.era_index(state.era)


def _make_trade_handler(sid):
    def handler(event=None):
        global neighbours_status
        if not _neighbours_allowed():
            return
        ok, text = neighbours.apply_trade(campaign.ui, sid, state.season, state.resources, _player_era_index())
        neighbours_status = text
        render()
    return handler


def _make_share_handler(sid):
    def handler(event=None):
        global neighbours_status
        if not _neighbours_allowed():
            return
        costs = {nid: node.cost for nid, node in tree.nodes.items()}
        names = {nid: node.name for nid, node in tree.nodes.items()}
        ok, text, gained = neighbours.apply_share(
            campaign.ui, sid, state.season, list(tree.researched), costs, names, _player_era_index()
        )
        if ok:
            state.resources["knowledge"] += gained
        neighbours_status = text
        render()
    return handler


def _make_bid_handler(amount):
    def handler(event=None):
        global neighbours_status
        if not _neighbours_allowed():
            return
        ok, text = neighbours.place_bid(campaign.ui, amount, state.resources, state.season, _player_era_index())
        neighbours_status = text
        render()
    return handler


def _neighbour_button(parent, button_id, text, handler, disabled=False, title=""):
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.type = "button"
    button.innerText = text
    button.disabled = disabled
    if title:
        button.title = title
    proxy = create_proxy(handler)
    _neighbour_proxies.append(proxy)
    button.addEventListener("click", proxy)
    parent.appendChild(button)
    return button


def update_neighbours_panel():
    toggle = document.getElementById("neighbours-toggle-button")
    toggle.innerText = "Hide Neighbours" if neighbours_open else "🗺 Neighbours"
    panel = document.getElementById("neighbours-panel")
    panel.hidden = not neighbours_open
    if not neighbours_open:
        return
    for proxy in _neighbour_proxies:
        proxy.destroy()
    del _neighbour_proxies[:]
    record = neighbours.get(campaign.ui)
    era_index = _player_era_index()
    season = state.season
    slot_views = [neighbours.view(record, sid, season, era_index) for sid in neighbours.SLOT_IDS]
    allowed = _neighbours_allowed()
    label = naming.title(settlement_name()) if settlement_name() else "Your settlement"
    document.getElementById("neighbours-map").innerHTML = neighbours.map_svg(slot_views, record, season, label[:20])
    document.getElementById("neighbours-caption").innerText = neighbours.map_caption(slot_views)
    if not allowed:
        note = (
            "Return to the present to deal with your neighbours." if campaign.revisiting is not None
            else f"Neighbours rest: {_rest_reason()}"
        )
    else:
        note = "Three computer-controlled neighbours. They never attack; you trade, share discoveries and bid for the lease on the Salt Flats."
    document.getElementById("neighbours-note").innerText = note
    holder = document.getElementById("neighbours-list")
    holder.innerHTML = ""
    resources = state.resources
    costs = {nid: node.cost for nid, node in tree.nodes.items()}
    for v in slot_views:
        card = document.createElement("div")
        card.className = "neighbour-card"
        head = document.createElement("h3")
        head.className = "neighbour-name"
        head.innerText = f"{v['name']}: {v['era_label']} era, {v['population']} people, {v['attitude_word']}"
        card.appendChild(head)
        need = document.createElement("p")
        need.className = "row-blurb"
        need.innerText = f"Needs {v['need']}; offers {v['offer']}. A trade: you give {v['give']} {v['need']}, you receive {v['get']} {v['offer']}."
        card.appendChild(need)
        ok_trade, why_trade = neighbours.can_trade(record, v["id"], season, resources, era_index)
        _neighbour_button(
            card, f"neighbour-{v['id']}-trade-button", f"Trade with {v['name']}",
            _make_trade_handler(v["id"]), disabled=not (allowed and ok_trade), title=why_trade,
        )
        candidate = neighbours.next_share_candidate(record, v["id"], list(tree.researched), costs)
        why_share = ""
        if v["share_ready_in"]:
            why_share = f"Ready in {v['share_ready_in']} seasons."
        elif candidate is None:
            why_share = "No discovery they have not heard."
        share_label = "Share a discovery"
        if candidate is not None:
            share_label = f"Share {tree.nodes[candidate].name}"
        _neighbour_button(
            card, f"neighbour-{v['id']}-share-button", share_label,
            _make_share_handler(v["id"]), disabled=not (allowed and not why_share), title=why_share,
        )
        holder.appendChild(card)
    document.getElementById("neighbours-lease").innerText = neighbours.lease_text(record, season)
    bids = document.getElementById("neighbours-bids")
    bids.innerHTML = ""
    low, high = neighbours.rival_range(record, season, era_index)
    hint = document.createElement("p")
    hint.className = "row-blurb"
    hint.innerText = (
        f"Rival bids usually fall between {low} and {high} materials; friendlier neighbours ask a little less. "
        f"The lease pays {neighbours.lease_income(era_index)} materials a season for {neighbours.LEASE_LENGTH} seasons. "
        "A bid is paid only if you win; otherwise it is returned."
    )
    bids.appendChild(hint)
    for name, amount in neighbours.bid_options(era_index):
        _neighbour_button(
            bids, f"neighbours-bid-{name}-button", f"Bid {amount} ({name})", _make_bid_handler(amount),
            disabled=not allowed or bool(record["lease"]["pending"]) or resources.get("materials", 0.0) < amount,
        )
    document.getElementById("neighbours-status").innerText = neighbours_status
    events = document.getElementById("neighbours-events")
    events.innerHTML = ""
    for entry in reversed(record["events"]):
        node = document.createElement("p")
        node.className = "status-line"
        year, season_name = year_and_season(max(1, entry["season"]))
        node.innerText = f"Year {year} {season_name}: {entry['text']}"
        events.appendChild(node)


# --- K-1 standing orders ------------------------------------------------------------------------------------
# The rules live in orders.py. This is the DOM half: a panel of if/then rows chosen from menus,
# and the one call after each season that lets the council carry them out.
orders_open = False
orders_status = ""
_orders_proxies = []
_orders_signature = None


def _run_standing_orders(effects):
    """After a season: check every order once; each firing is minuted in the Council Minutes."""
    global orders_status
    fired = orders.run(campaign.ui, state, list(tree.researched), lambda: sustainability.score(state, effects))
    for item in fired:
        record_motion("order", item["text"])
    if fired:
        update_minutes_panel()
        acted = [item for item in fired if item["acted"]]
        orders_status = f"Last season the council carried out {len(acted)} standing order(s)." if acted else (
            "A standing order could not act last season; see the Council Minutes."
        )


def on_toggle_orders(event=None):
    global orders_open, _orders_signature
    orders_open = not orders_open
    _orders_signature = None
    update_orders_panel()


def on_orders_master(event=None):
    global orders_status, _orders_signature
    if campaign.revisiting is not None:
        return
    on = orders.set_master(campaign.ui, not orders.get(campaign.ui)["on"])
    orders_status = "Standing orders are on." if on else "Standing orders are paused: none will fire until you switch them on."
    _orders_signature = None
    update_orders_panel()


def on_orders_add(event=None):
    global orders_status, _orders_signature
    if campaign.revisiting is not None:
        return
    ok, text = orders.add_rule(campaign.ui, list(tree.researched), state.era)
    orders_status = text
    _orders_signature = None
    update_orders_panel()


def orders_set(rule_id, field, raw):
    """Apply one menu choice to one order (also what the menus call)."""
    global orders_status, _orders_signature
    if campaign.revisiting is not None:
        return False
    ok, text = orders.update_rule(campaign.ui, rule_id, field, raw, list(tree.researched), state.era)
    orders_status = text
    _orders_signature = None
    update_orders_panel()
    return ok


def orders_remove(rule_id):
    global orders_status, _orders_signature
    if campaign.revisiting is not None:
        return False
    removed = orders.remove_rule(campaign.ui, rule_id)
    orders_status = "Order removed." if removed else ""
    _orders_signature = None
    update_orders_panel()
    return removed


def _unlock_hint(node_id):
    node = tree.nodes.get(node_id)
    return f"research {node.name}" if node is not None else "research a later discovery"


def _orders_select(parent, select_id, label, options, current, field, rule_id, locked=False):
    """One menu: options are (value, text, disabled). The chosen value is applied by orders_set()."""
    wrap = document.createElement("label")
    wrap.className = "orders-field"
    caption = document.createElement("span")
    caption.className = "orders-field-label"
    caption.innerText = label
    wrap.appendChild(caption)
    select = document.createElement("select")
    select.id = select_id
    select.setAttribute("aria-label", label)
    for value, text, disabled in options:
        option = document.createElement("option")
        option.value = str(value)
        option.innerText = text
        option.disabled = bool(disabled)
        select.appendChild(option)
    select.value = str(current)
    select.disabled = locked

    def handler(event=None):
        orders_set(rule_id, field, select.value)

    proxy = create_proxy(handler)
    _orders_proxies.append(proxy)
    select.addEventListener("change", proxy)
    wrap.appendChild(select)
    parent.appendChild(wrap)
    return select


def _orders_button(parent, button_id, text, handler, disabled=False):
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.type = "button"
    button.innerText = text
    button.disabled = disabled
    proxy = create_proxy(handler)
    _orders_proxies.append(proxy)
    button.addEventListener("click", proxy)
    parent.appendChild(button)
    return button


def _make_orders_toggle(rule_id, on):
    def handler(event=None):
        orders_set(rule_id, "on", on)
    return handler


def _make_orders_remove(rule_id):
    def handler(event=None):
        orders_remove(rule_id)
    return handler


def _orders_menu_values(rule, researched, era):
    """The option lists for one rule's menus."""
    roles = sim.roles_for_era(era)
    triggers = []
    for key, spec in orders.TRIGGERS.items():
        if not orders._era_ok(era, spec["era"]):
            continue
        open_ = orders.trigger_available(key, researched, era)
        text = spec["label"] if open_ else f"{spec['label']} (locked: {_unlock_hint(spec['unlock'])})"
        triggers.append((key, text, not open_))
    spec = orders.TRIGGERS[rule["trigger"]]
    values = [(v, orders.threshold_text(rule["trigger"], v), False) for v in spec["values"]]
    actions = []
    for key, aspec in orders.ACTIONS.items():
        if not orders._era_ok(era, aspec["era"]):
            continue
        open_ = orders.action_available(key, researched, era)
        text = aspec["label"] if open_ else f"{aspec['label']} (locked: {_unlock_hint(aspec['unlock'])})"
        actions.append((key, text, not open_))
    sources = [(orders.NO_SOURCE, "Idle people", False), (orders.LARGEST, "The biggest group", False)]
    sources += [(r, sim.ROLE_LABEL[r], r == rule["to"]) for r in roles]
    targets = [(r, sim.ROLE_LABEL[r], False) for r in roles]
    return triggers, values, actions, sources, targets


def _orders_signature_now():
    record = orders.get(campaign.ui)
    return (
        json.dumps(record, sort_keys=True), orders_open, state.era, len(tree.researched), campaign.revisiting,
        orders_status, tuple(e["season"] for e in minutes.entries(campaign.ui) if e["kind"] == "order"),
        tuple(sorted(tree.researched)),
    )


def update_orders_panel():
    global _orders_signature
    toggle = document.getElementById("orders-toggle-button")
    toggle.innerText = "Hide Standing Orders" if orders_open else "📌 Standing Orders"
    panel = document.getElementById("orders-panel")
    panel.hidden = not orders_open
    if not orders_open:
        return
    signature = _orders_signature_now()
    if signature == _orders_signature:
        return
    _orders_signature = signature
    for proxy in _orders_proxies:
        proxy.destroy()
    del _orders_proxies[:]
    researched = list(tree.researched)
    record = orders.get(campaign.ui)
    open_slots = orders.slots(researched)
    revisiting = campaign.revisiting is not None
    master = document.getElementById("orders-master-button")
    master.innerText = f"Standing orders: {'ON' if record['on'] else 'OFF'}"
    master.setAttribute("aria-pressed", "true" if record["on"] else "false")
    master.disabled = revisiting
    nxt = orders.next_slot_unlock(researched)
    summary = f"{len(record['rules'])} of {open_slots} slot(s) in use ({orders.MAX_RULES} possible)."
    if nxt is not None:
        summary += f" The next slot opens when you {_unlock_hint(nxt)}."
    if open_slots == 0:
        summary = f"No slot yet. The first opens when you {_unlock_hint(orders.SLOT_UNLOCKS[0])}."
    if record["fired"]:
        summary += f" The council has carried out {record['fired']} order(s) so far."
    document.getElementById("orders-summary").innerText = summary
    add = document.getElementById("orders-add-button")
    add.disabled = revisiting or len(record["rules"]) >= open_slots
    note = document.getElementById("orders-note")
    note.innerText = (
        "Return to the present to change orders; they do not run during a Look Back." if revisiting else
        "After every season the council checks each order from the top. A matching order does its job at once and "
        "is written into the Council Minutes. Orders only do what you could do by hand: move people between jobs, "
        "schedule a refactor season, stop quick builds."
    )
    holder = document.getElementById("orders-list")
    holder.innerHTML = ""
    if not record["rules"]:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "No orders yet. Press Add an order, then choose from the menus."
        holder.appendChild(empty)
    for index, rule in enumerate(record["rules"]):
        rid = rule["id"]
        dormant = index >= open_slots
        card = document.createElement("div")
        card.className = "orders-card" + ("" if rule["on"] and not dormant else " orders-card--off")
        title = document.createElement("p")
        title.className = "orders-sentence"
        title.innerText = f"Order {index + 1}. {orders.describe(rule)}" + (
            f" Carried out {rule['fires']} time(s)." if rule["fires"] else ""
        )
        card.appendChild(title)
        triggers, values, actions, sources, targets = _orders_menu_values(rule, researched, state.era)
        controls = document.createElement("div")
        controls.className = "orders-controls"
        lock = revisiting
        _orders_select(controls, f"orders-{rid}-trigger", "If", triggers, rule["trigger"], "trigger", rid, lock)
        _orders_select(
            controls, f"orders-{rid}-op", "is", [("below", "below", False), ("above", "above", False)],
            rule["op"], "op", rid, lock,
        )
        _orders_select(controls, f"orders-{rid}-value", "this value", values, rule["value"], "value", rid, lock)
        _orders_select(controls, f"orders-{rid}-action", "Then", actions, rule["action"], "action", rid, lock)
        if rule["action"] == "shift":
            _orders_select(
                controls, f"orders-{rid}-n", "people", [(n, str(n), False) for n in range(1, orders.MAX_MOVE + 1)],
                rule["n"], "n", rid, lock,
            )
            _orders_select(controls, f"orders-{rid}-from", "from", sources, rule["from"], "from", rid, lock)
            _orders_select(controls, f"orders-{rid}-to", "to", targets, rule["to"], "to", rid, lock)
        _orders_select(
            controls, f"orders-{rid}-repeat", "Run",
            [(k, orders.REPEAT_LABEL[k], False) for k in orders.REPEATS], rule["repeat"], "repeat", rid, lock,
        )
        card.appendChild(controls)
        buttons = document.createElement("div")
        buttons.className = "orders-buttons"
        _orders_button(
            buttons, f"orders-{rid}-toggle", "Pause this order" if rule["on"] else "Resume this order",
            _make_orders_toggle(rid, not rule["on"]), disabled=revisiting,
        )
        _orders_button(buttons, f"orders-{rid}-remove", "Remove", _make_orders_remove(rid), disabled=revisiting)
        card.appendChild(buttons)
        holder.appendChild(card)
    document.getElementById("orders-status").innerText = orders_status
    recent = document.getElementById("orders-recent")
    recent.innerHTML = ""
    fired = [e for e in minutes.entries(campaign.ui) if e["kind"] == "order"]
    if not fired:
        none = document.createElement("p")
        none.className = "row-blurb"
        none.innerText = "Nothing yet. When an order fires it appears here and in the Council Minutes."
        recent.appendChild(none)
    for entry in reversed(fired[-6:]):
        year, season_name = year_and_season(entry["season"])
        line = document.createElement("p")
        line.className = "status-line"
        line.innerText = f"Year {year}, {season_name}: {entry['text']}"
        recent.appendChild(line)


# --- K-5 living ruins (heritage sites) ----------------------------------------------------------------------
# The rules live in heritage.py. This is the DOM half: a panel listing the sites the settlement has left
# behind, each kept (a culture bonus) or cleared (materials and land now, a culture cost for good).
heritage_open = False
heritage_status = ""
heritage_confirm = None
_heritage_proxies = []


def _heritage_sites():
    return [] if _resting() else heritage.sites_before(campaign.furthest_era, campaign.ui)


def _heritage_summary_text():
    if _resting():
        return "resting (comparable run)"
    kept, cleared = heritage.counts(campaign.ui, campaign.furthest_era)
    if kept + cleared == 0:
        return "none yet"
    return f"{kept} kept, {cleared} cleared"


def on_toggle_heritage(event=None):
    global heritage_open, heritage_confirm
    heritage_open = not heritage_open
    heritage_confirm = None
    update_heritage_panel()


def _make_heritage_demolish_handler(era):
    def handler(event=None):
        global heritage_confirm, heritage_status
        if heritage_confirm != era:
            heritage_confirm = era
            heritage_status = "Clearing a heritage site cannot be undone. Press Confirm to go ahead."
            update_heritage_panel()
            return
        ok, text = heritage.demolish(
            campaign.ui, state, campaign.furthest_era, era, _resting(), campaign.revisiting is not None
        )
        heritage_confirm = None
        heritage_status = text
        if ok:
            chronicle.log_challenge(state.season, state.era, text)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_heritage_cancel_handler():
    def handler(event=None):
        global heritage_confirm, heritage_status
        heritage_confirm = None
        heritage_status = "Nothing was cleared."
        update_heritage_panel()
    return handler


def update_heritage_panel():
    toggle = document.getElementById("heritage-toggle-button")
    toggle.innerText = "Hide Heritage" if heritage_open else "🏛 Heritage Sites"
    panel = document.getElementById("heritage-panel")
    panel.hidden = not heritage_open
    if not heritage_open:
        return
    for proxy in _heritage_proxies:
        proxy.destroy()
    del _heritage_proxies[:]
    sites = _heritage_sites()
    locked = campaign.revisiting is not None or _resting()
    note = document.getElementById("heritage-note")
    if campaign.revisiting is not None:
        note.innerText = "Return to the present to change a heritage site."
    elif _resting():
        note.innerText = f"Heritage sites rest: {_rest_reason()}"
    else:
        note.innerText = (
            "Each era you leave behind stays standing as a heritage site. Kept, it adds "
            f"{heritage.KEEP_BONUS * 100:.0f}% to culture capacity. Cleared, you gain materials and a little land health "
            f"now, and culture capacity is {heritage.DEMOLISH_PENALTY * 100:.0f}% lower for good. Keeping is the default."
        )
    document.getElementById("heritage-summary").innerText = _heritage_summary_text() + "."
    holder = document.getElementById("heritage-list")
    holder.innerHTML = ""
    if not sites:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "No heritage sites yet. The first appears when you leave the Tribal era."
        holder.appendChild(empty)
    for site in sites:
        card = document.createElement("div")
        card.className = "heritage-card" + ("" if site["kept"] else " heritage-card--cleared")
        head = document.createElement("h3")
        head.className = "heritage-name"
        head.innerText = f"{site['name']} ({sim.ERA_LABEL[site['era']]} era)"
        card.appendChild(head)
        blurb = document.createElement("p")
        blurb.className = "row-blurb"
        blurb.innerText = site["blurb"]
        card.appendChild(blurb)
        status = document.createElement("p")
        status.className = "status-line"
        status.innerText = heritage.status_text(site)
        card.appendChild(status)
        if site["kept"]:
            era = site["era"]
            confirming = heritage_confirm == era
            gain = heritage.demolish_gain(era)
            button = document.createElement("button")
            button.id = f"heritage-{era}-demolish-button"
            button.className = "secondary"
            button.type = "button"
            button.disabled = locked
            button.innerText = (
                f"Confirm: clear it for {gain:.0f} materials" if confirming else f"Clear this site (+{gain:.0f} materials)"
            )
            proxy = create_proxy(_make_heritage_demolish_handler(era))
            _heritage_proxies.append(proxy)
            button.addEventListener("click", proxy)
            card.appendChild(button)
            if confirming:
                cancel = document.createElement("button")
                cancel.id = f"heritage-{era}-cancel-button"
                cancel.className = "secondary"
                cancel.type = "button"
                cancel.innerText = "Keep it"
                cancel_proxy = create_proxy(_make_heritage_cancel_handler())
                _heritage_proxies.append(cancel_proxy)
                cancel.addEventListener("click", cancel_proxy)
                card.appendChild(cancel)
        holder.appendChild(card)
    document.getElementById("heritage-status").innerText = heritage_status


# --- K-13 the Beyond ------------------------------------------------------------------------------------------
# The rules live in beyond.py. This is the DOM half: the panel, the ladder kept in localStorage, and the
# one call after each season that scores a Beyond era.
beyond_open = False
beyond_status = ""
_beyond_signature = None


def beyond_ladder_load():
    window = _js_window()
    if window is None:
        return []
    try:
        raw = window.localStorage.getItem(beyond.LADDER_KEY)
    except Exception:  # noqa: BLE001
        return []
    return beyond.clean_ladder(raw) if isinstance(raw, str) else []


def beyond_ladder_store(rows):
    window = _js_window()
    if window is None:
        return False
    try:
        window.localStorage.setItem(beyond.LADDER_KEY, json.dumps(beyond.clean_ladder(rows)))
        return True
    except Exception:  # noqa: BLE001
        return False


def _bank_beyond_result(survived):
    """A run ended: put its result on the ladder (a run that survived no era is not listed)."""
    if survived and survived >= 1:
        beyond_ladder_store(beyond.add_to_ladder(beyond_ladder_load(), _today(), survived, settlement_name()))


def _beyond_after_season(score):
    global beyond_status, _beyond_signature
    event = beyond.after_season(campaign.ui, score)
    _beyond_signature = None
    if event is None:
        return
    if event["kind"] == "survived":
        beyond_status = f"Beyond era {event['era']} survived. Next: {event['next_theme']}."
        chronicle.log_challenge(state.season, state.era, f"Beyond era {event['era']} survived. Next comes {event['next_theme']}.")
    else:
        beyond_status = (
            f"The Beyond run ended after {event['survived']} era(s) survived. The settlement carries on as it is; "
            "you can begin a new run whenever you like."
        )
        chronicle.log_challenge(state.season, state.era, beyond_status)
        _bank_beyond_result(event["survived"])


def _beyond_summary_text():
    record = beyond.get(campaign.ui)
    if not beyond.available(campaign.furthest_era):
        return "opens at the Relay Age"
    if record["on"]:
        return f"era {record['era']} under way, best {record['best']}"
    return f"best {record['best']} era(s) survived"


def on_toggle_beyond(event=None):
    global beyond_open, _beyond_signature
    beyond_open = not beyond_open
    _beyond_signature = None
    update_beyond_panel()


def on_beyond_start(event=None):
    global beyond_status, _beyond_signature
    ok, text = beyond.start(campaign.ui, campaign.furthest_era, _resting(), campaign.revisiting is not None)
    beyond_status = text
    _beyond_signature = None
    if ok:
        chronicle.log_challenge(state.season, state.era, text)
        render()
    else:
        update_beyond_panel()


def on_beyond_stop(event=None):
    global beyond_status, _beyond_signature
    survived = beyond.stop(campaign.ui)
    _beyond_signature = None
    if survived is None:
        return
    _bank_beyond_result(survived)
    beyond_status = f"You ended the run with {survived} Beyond era(s) survived. The pressure is lifted."
    render()


def update_beyond_panel():
    global _beyond_signature
    toggle = document.getElementById("beyond-toggle-button")
    toggle.innerText = "Hide the Beyond" if beyond_open else "🌌 The Beyond"
    panel = document.getElementById("beyond-panel")
    panel.hidden = not beyond_open
    if not beyond_open:
        return
    record = beyond.get(campaign.ui)
    ladder = beyond_ladder_load()
    signature = (json.dumps(record, sort_keys=True), campaign.revisiting, campaign.furthest_era, beyond_status,
                 json.dumps(ladder), _resting(), round(state.land_health, 2), state.population)
    if signature == _beyond_signature:
        return
    _beyond_signature = signature
    available = beyond.available(campaign.furthest_era)
    note = document.getElementById("beyond-note")
    if not available:
        note.innerText = "The Beyond opens once the settlement reaches the Relay Age."
    elif _resting():
        note.innerText = f"The Beyond is not offered: {_rest_reason()}"
    elif campaign.revisiting is not None:
        note.innerText = "Return to the present to take part in the Beyond."
    else:
        note.innerText = (
            "An optional endless mode. Each Beyond era has a named pressure that grows with entropy; keep the "
            "sustainability score up for 10 of its 12 seasons to survive it. A run that falls short simply ends: "
            "nothing is lost and you can begin again."
        )
    start = document.getElementById("beyond-start-button")
    start.disabled = (not available) or record["on"] or _resting() or campaign.revisiting is not None
    stop = document.getElementById("beyond-stop-button")
    stop.hidden = not record["on"]
    holder = document.getElementById("beyond-lines")
    holder.innerHTML = ""
    for line in beyond.status_lines(record, state, current_effects()):
        node = document.createElement("p")
        node.className = "row-blurb"
        node.innerText = line
        holder.appendChild(node)
    document.getElementById("beyond-status").innerText = beyond_status
    rows = document.getElementById("beyond-ladder")
    rows.innerHTML = ""
    if not ladder:
        none = document.createElement("p")
        none.className = "row-blurb"
        none.innerText = "No finished runs yet. Your furthest runs on this device are listed here."
        rows.appendChild(none)
    for index, row in enumerate(ladder, start=1):
        line = document.createElement("p")
        line.className = "status-line"
        line.innerText = beyond.ladder_text(row, index)
        rows.appendChild(line)


# --- K-12 generated map with biomes -------------------------------------------------------------------------
# The rules live in geography.py. This is the DOM half: an opt-in map chosen before the first season (or
# inherited from a consulting case), shown as a grid, with each biome's boon and price in words.
geography_open = False
geography_status = ""


def _geo_seed():
    """The seed in force: a consulting case's inherited map, else the player's (none in a challenge run)."""
    case = consulting.get(campaign.ui)
    if case is not None:
        return geography.active_seed(campaign.ui, case["case"])
    if challengerun.get(campaign.ui) is not None:
        return None
    return geography.chosen_seed(campaign.ui)


def _geo_editable():
    return (
        campaign.revisiting is None
        and consulting.get(campaign.ui) is None
        and challengerun.get(campaign.ui) is None
        and founding.is_pristine(campaign)
    )


def on_toggle_geography(event=None):
    global geography_open
    geography_open = not geography_open
    update_geography_panel()


def _geo_set(seed, message):
    global geography_status
    if not _geo_editable():
        geography_status = "The map can only be chosen before the first season of a fresh settlement."
        update_geography_panel()
        return
    geography.set_seed(campaign.ui, seed)
    geography_status = message
    render()


def on_geography_new(event=None):
    seed = _seed_hint() % geography.SEED_MAX or 1
    current = geography.chosen_seed(campaign.ui)
    if seed == current:
        seed = seed % (geography.SEED_MAX - 1) + 1
    _geo_set(seed, f"A new map was drawn (seed {seed}).")


def on_geography_off(event=None):
    _geo_set(None, "Back to open land: no map.")


def on_geography_use_seed(event=None):
    raw = document.getElementById("geography-seed-input").value
    try:
        seed = int(str(raw).strip())
    except (TypeError, ValueError):
        seed = None
    if geography.clean_seed(seed) is None:
        global geography_status
        geography_status = "Type a whole number from 1 to 2147483647."
        update_geography_panel()
        return
    _geo_set(seed, f"Map for seed {seed}.")


def update_geography_panel():
    toggle = document.getElementById("geography-toggle-button")
    toggle.innerText = "Hide Geography" if geography_open else "🗺 Geography"
    panel = document.getElementById("geography-panel")
    panel.hidden = not geography_open
    if not geography_open:
        return
    seed = _geo_seed()
    grid = geography.generate(seed)
    case = consulting.get(campaign.ui)
    editable = _geo_editable()
    note = document.getElementById("geography-note")
    if case is not None:
        note.innerText = "This consulting case comes with its own inherited ground, so the map is fixed."
    elif challengerun.get(campaign.ui) is not None:
        note.innerText = "Challenge runs are played on open land so their scores stay comparable."
    elif not editable:
        note.innerText = "The map is fixed once the first season has begun (or while looking back)."
    else:
        note.innerText = (
            "Optional. Draw a map for this settlement before its first season: each biome gives a small boon and a "
            "small price. Share the seed number and someone else gets the same ground."
        )
    document.getElementById("geography-seed").innerText = (
        f"Seed {seed}: {geography.summary_text(grid)}." if grid else "Open land: no map (every number as usual)."
    )
    document.getElementById("geography-map").innerHTML = geography.map_svg(grid)
    holder = document.getElementById("geography-list")
    holder.innerHTML = ""
    for line in geography.describe(grid):
        node = document.createElement("p")
        node.className = "row-blurb"
        node.innerText = line
        holder.appendChild(node)
    document.getElementById("geography-new-button").disabled = not editable
    document.getElementById("geography-new-button").innerText = "New map" if grid else "Draw a map"
    document.getElementById("geography-off-button").disabled = not editable or not grid
    document.getElementById("geography-use-seed-button").disabled = not editable
    document.getElementById("geography-seed-input").disabled = not editable
    document.getElementById("geography-status").innerText = geography_status


def _extra_dashboard_sections():
    """Standing advantages as dashboard rows, so none is ever a hidden mechanic."""
    resting = _resting()
    record = dynasty.get(campaign.ui)
    if record["off"]:
        perks = "switched off"
    elif resting:
        perks = "resting (comparable run)"
    else:
        perks = f"{len(record['owned'])} owned"
    doctrine_rows = doctrines.history(campaign.ui)
    doctrine_text = ", ".join(f"{doctrines.DOCTRINES[d]['label']} ({sim.ERA_LABEL[e]})" for e, d in doctrine_rows) or "none"
    rows = [
        ("Dynasty perks", perks),
        ("Dynasty rank", dynasty.rank_name(record["earned"])),
        ("Doctrines", doctrine_text),
        ("Citizen bonuses", _citizen_effects_text() if _citizens_on() else "switched off"),
        ("Heritage sites", _heritage_summary_text()),
        ("The Beyond", _beyond_summary_text()),
        ("Geography", geography.summary_text(geography.generate(_geo_seed()))),
    ]
    return [{"title": "Standing advantages", "rows": rows}]


def _bank_if_collapsed():
    """A collapsed settlement banks what it reached, once."""
    if campaign.revisiting is not None or not dynasty.is_collapsed(state):
        return
    if dynasty.get_run(campaign.ui)["failed"]:
        return
    result, info = _bank_current()
    if result["points"] > 0:
        chronicle.log_challenge(
            state.season, state.era,
            f"The settlement has failed. Its lessons are banked in the Dynasty: {result['gained']} Legacy points.",
        )


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
    _rewind_clear()
    _adopt_local_dynasty()
    sync_name_input()
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
    # U2: the optional Hamlet view. Preference is read once at load; the
    # toggle button itself is only shown on a desktop-class screen.
    global hamlet_on
    hamlet_on = _pc_layout() or _hamlet_storage_get() == "on"
    document.getElementById("hamlet-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hamlet)
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
    # K-14: a hidden twin of the in-panel buttons, so the Desktop window frame
    # can close the post-mortem through the same handler (keeps one open flag).
    document.getElementById("postmortem-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_postmortem)
    )
    document.getElementById("founders-add-button").addEventListener(
        "click", create_proxy(on_add_founders_note)
    )
    document.getElementById("settlement-name-suggest-button").addEventListener(
        "click", create_proxy(on_name_suggest)
    )
    document.getElementById("settlement-name-save-button").addEventListener(
        "click", create_proxy(on_name_save)
    )
    document.getElementById("settlement-name-input").addEventListener(
        "keydown", create_proxy(on_name_keydown)
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
    document.getElementById("challenge-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_challenge)
    )
    _build_challenge_controls()
    for _name in challengerun.RANGES:
        document.getElementById(f"challenge-dial-{_name}").addEventListener(
            "input", create_proxy(on_challenge_input)
        )
    document.getElementById("challenge-modifier-select").addEventListener(
        "change", create_proxy(on_challenge_input)
    )
    document.getElementById("challenge-hard-checkbox").addEventListener(
        "change", create_proxy(on_challenge_input)
    )
    for _id, _handler in (
        ("challenge-daily-start-button", on_challenge_daily_start),
        ("challenge-custom-start-button", on_challenge_custom_start),
        ("challenge-abandon-button", on_challenge_abandon),
        ("challenge-code-copy-button", on_challenge_copy_code),
        ("challenge-code-load-button", on_challenge_load_code),
    ):
        document.getElementById(_id).addEventListener("click", create_proxy(_handler))
    document.getElementById("timelapse-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_timelapse)
    )
    document.getElementById("timelapse-scrub").addEventListener("input", create_proxy(on_timelapse_scrub))
    for _id, _handler in (
        ("timelapse-prev-button", on_timelapse_prev),
        ("timelapse-next-button", on_timelapse_next),
        ("timelapse-play-button", on_timelapse_play),
        ("timelapse-strip-button", on_timelapse_strip),
    ):
        document.getElementById(_id).addEventListener("click", create_proxy(_handler))
    document.getElementById("advisors-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_advisors)
    )
    document.getElementById("quick-build-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_quick_build)
    )
    document.getElementById("refactor-button").addEventListener(
        "click", create_proxy(on_toggle_refactor)
    )
    for _case_id in consulting.CASES:
        document.getElementById(f"consulting-case-{_case_id}-button").addEventListener(
            "click", create_proxy(_make_consulting_start_handler(_case_id))
        )
    document.getElementById("consulting-abandon-button").addEventListener(
        "click", create_proxy(on_consulting_abandon)
    )
    document.getElementById("found-settlement-button").addEventListener(
        "click", create_proxy(on_found_new_settlement)
    )
    for _id, _handler in (
        ("dynasty-toggle-button", on_toggle_dynasty),
        ("dynasty-bank-button", on_dynasty_bank),
        ("dynasty-off-button", on_dynasty_off),
        ("doctrines-toggle-button", on_toggle_doctrines),
        ("citizens-toggle-button", on_toggle_citizens),
        ("citizens-off-button", on_citizens_off),
        ("neighbours-toggle-button", on_toggle_neighbours),
        ("orders-toggle-button", on_toggle_orders),
        ("heritage-toggle-button", on_toggle_heritage),
        ("beyond-toggle-button", on_toggle_beyond),
        ("geography-toggle-button", on_toggle_geography),
        ("geography-new-button", on_geography_new),
        ("geography-off-button", on_geography_off),
        ("geography-use-seed-button", on_geography_use_seed),
        ("beyond-start-button", on_beyond_start),
        ("beyond-stop-button", on_beyond_stop),
        ("orders-master-button", on_orders_master),
        ("orders-add-button", on_orders_add),
        ("rewind-button", on_rewind),
    ):
        document.getElementById(_id).addEventListener("click", create_proxy(_handler))
    _adopt_local_dynasty()
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
