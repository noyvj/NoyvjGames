"""Small things many panels share: the season's effects and report text, the visual-state hook, the season calendar and clock constants, the Desktop-layout check, and the dynasty/rewind/citizen helpers that the archive and the save code also need."""

import json

import beyond
import challengerun
import citizens
import consulting
import doctrines
import dynasty
import geography
import heritage
import techdebt
import visual

import continuum_runstate as runstate


def current_effects():
    """The aggregate modifiers applied to the simulation this season.

    The single seam through which research reaches both the simulation and
    the sustainability score — nothing else in the game reads the tree.
    """
    effects = runstate.tree.effects()
    # K-4: technical debt (Digital Age on) reaches the season loop through this same seam.
    # Not applied during a Look Back: the live debt belongs to the present settlement.
    if runstate.campaign.revisiting is None:
        effects = techdebt.apply_effects(effects, runstate.campaign.ui, runstate.state.era)
    # K-10/K-11: a challenge run's modifier (the day's boon with a price) rides the same seam.
    effects = challengerun.apply_effects(effects, runstate.campaign.ui)
    _sync_tree_costs()
    if runstate.campaign.revisiting is None:
        # K-2/K-6/K-15: Dynasty perks, doctrines and notable citizens ride the same seam. The
        # earned advantages rest while a challenge run or consulting case is the active run.
        resting = _resting()
        effects = dynasty.apply_effects(effects, runstate.campaign.ui, resting)
        effects = doctrines.apply_effects(effects, runstate.campaign.ui)
        effects = citizens.apply_effects(effects, runstate.campaign.ui, runstate.state.era, resting)
        # K-5: kept heritage sites add to culture, cleared ones take a little away.
        effects = heritage.apply_effects(effects, runstate.campaign.ui, runstate.campaign.furthest_era, resting)
        # K-13: the Beyond's standing pressure, while a run is on.
        effects = beyond.apply_effects(effects, runstate.campaign.ui, runstate.state, not resting)
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


def get_visual_state():
    """Phase 5's data contract for the Three.js render layer — see
    visual.py. Exposed as a plain module-level function (same shape as
    get_state()/load_state() below) so render3d.js can call it through
    Pyodide's globals the same way the shared save widget calls those two.
    Returns a plain dict; pyodide's toJs() (called from JS) turns it into
    a plain JS object, mirroring the save widget's own contract.
    """
    visual_data = visual.visual_state(runstate.state, current_effects())
    # K-5: the heritage sites standing behind the era being drawn (none while a challenge run or
    # consulting case rests), as plain {era, kept} so the scene can draw a ruin or a cleared patch.
    sites = [] if _resting() else heritage.sites_before(runstate.state.era, runstate.campaign.ui)
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


def _js_window():
    try:
        from js import window
    except ImportError:
        return None
    return window


SEASONS_PER_YEAR = 4
SEASON_NAMES = ["Spring", "Summer", "Autumn", "Winter"]


def year_and_season(season):
    index = max(1, int(season)) - 1
    return index // SEASONS_PER_YEAR + 1, SEASON_NAMES[index % SEASONS_PER_YEAR]


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


SEASON_SECONDS = {
    "tribal": 10.0, "agrarian": 10.0, "classical": 12.0, "medieval": 12.0,
    "industrial": 14.0, "digital": 16.0, "space": 18.0, "relay": 20.0,
}
SPEEDS = (0, 1, 2, 4)
MAX_SEASONS_PER_TICK = 2  # a stalled frame must never fire a burst of seasons

DYNASTY_STORAGE_KEY = "continuum-dynasty-v1"


def _resting():
    """True while a challenge run or consulting case is the active run: every earned advantage
    (Dynasty perks, citizen bonuses, rewinds, neighbours) rests so those runs stay comparable."""
    return challengerun.get(runstate.campaign.ui) is not None or consulting.get(runstate.campaign.ui) is not None


def _inherited_era():
    case = consulting.get(runstate.campaign.ui)
    return consulting.CASES[case["case"]]["era"] if case is not None else None


def _sync_tree_costs():
    """Doctrines make some research branches cheaper; the tree is told each time effects are read."""
    if runstate.campaign.revisiting is not None:
        runstate.tree.cost_mults = {}
        return
    runstate.tree.cost_mults = doctrines.cost_multipliers(runstate.campaign.ui, dynasty.doctrine_edge(runstate.campaign.ui, _resting()))


def _dynasty_local_store():
    window = _js_window()
    if window is None or runstate.sandbox_active:  # Z-18
        return
    record = dynasty.get(runstate.campaign.ui)
    try:
        window.localStorage.setItem(DYNASTY_STORAGE_KEY, json.dumps(record))
    except Exception:
        pass


def _bank_current():
    """Banks the live settlement's Legacy (by the difference). Returns (result, info)."""
    info = dynasty.run_info(runstate.campaign, _inherited_era())
    result = dynasty.bank(runstate.campaign.ui, info)
    if result["gained"] or result["first"]:
        _dynasty_local_store()
    return result, info


def _rewind_clear():
    runstate._rewind_snapshot = None


def _citizens_on():
    return citizens.is_on(runstate.campaign.ui)


def _geo_seed():
    """The seed in force: a consulting case's inherited map, else the player's (none in a challenge run)."""
    case = consulting.get(runstate.campaign.ui)
    if case is not None:
        return geography.active_seed(runstate.campaign.ui, case["case"])
    if challengerun.get(runstate.campaign.ui) is not None:
        return None
    return geography.chosen_seed(runstate.campaign.ui)
