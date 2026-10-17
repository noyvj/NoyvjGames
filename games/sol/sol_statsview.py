"""The Stats and Share panel, share card text, cross-planet summaries, stats codes and the run compare."""

import math

import challenges
import export_progress
from js import document, setTimeout
from pyodide.ffi import create_proxy

import sol_runstate as runstate
from sol_achievements import achievement_ids_earned, best_run_text
from sol_rhythm import CHAINS, chains_found
from sol_rules import BODY_DISPLAY_NAMES, PLANETS, RESEARCH_TIERS, TICK_INTERVAL_MS, planet_state
from sol_runmods import MUTATOR_BY_ID, mutator_glyphs
from sol_scarcity import _scarcity_mean_progress, scarcity_run_card_text, scarcity_share_lines
from sol_story import ACHIEVEMENTS
from sol_util import _dom_id, _format_duration, _split_time, _terraformed_planet_count


# ===========================================================================
# Lifetime Stats + Shareable Summary Card (A4 + A8) — one consolidated
# toolbar panel rather than two, since both are read-only "look back at
# your progress" views and the toolbar already carries four other buttons.
# ===========================================================================


def _lifetime_playtime_seconds():
    # total_ticks is in-game simulated time (ticks * TICK_INTERVAL_MS), not
    # a wall-clock reading -- see its own module-level comment for why.
    return runstate.total_ticks * (TICK_INTERVAL_MS / 1000)


def build_share_card_text():
    """A8: a shareable "my solar system" end-state summary card. Plain
    text, not a rendered image -- this project has no asset/image pipeline
    (A6's own build note), and plain text is trivially "shareable" (paste
    it anywhere) without inventing one just for this."""
    if runstate._scarcity is not None:
        return scarcity_run_card_text()
    terraform_values = [planet_state[p]["terraform_progress"] for p in PLANETS]
    avg_terraform = sum(terraform_values) / len(terraform_values)
    lines = [
        "🌌 My Solar System — SOL",
        f"Worlds visited: {len(runstate.visited_bodies)}/{len(PLANETS)}",
        f"Worlds unlocked: {min(len(runstate.unlocked_bodies) + 1, len(PLANETS))}/{len(PLANETS)}",
        f"Average terraforming: {round(avg_terraform)}%",
        f"Fully terraformed worlds: {_terraformed_planet_count()}/{len(PLANETS)}",
        f"Achievements: {len(achievement_ids_earned())}/{len(ACHIEVEMENTS)}",
        f"Prestige level: {runstate.prestige_level}",
    ]
    if runstate.mutators_run:
        lines.append(f"Run rules: {mutator_glyphs(runstate.mutators_run).strip()} " + ", ".join(
            MUTATOR_BY_ID[m_id]["label"] for m_id in runstate.mutators_run))
    lines.extend(scarcity_share_lines())  # A-12: today's seed words and today's Scarcity Run result
    return "\n".join(lines)


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "SOL, 100% terraformed, 9/9 worlds fully terraformed, ...". Read by
    the page's own inline script through pyodide.globals when the shared
    Copy result button is pressed, so it always matches the run right now."""
    if runstate._scarcity is not None:
        run = runstate._scarcity
        spec = run["spec"]
        score = _split_time(run["done"]) if run["done"] is not None else f"{round(_scarcity_mean_progress())}%"
        return {"game": "SOL", "score": score, "unit": f"Scarcity Run {spec['words']}",
                "stats": [challenges.goal_text(spec), f"Governor alone {_split_time(spec['par'])}"]}
    terraform_values = [planet_state[p]["terraform_progress"] for p in PLANETS]
    average = round(sum(terraform_values) / len(terraform_values))
    stats = [
        f"{_terraformed_planet_count()}/{len(PLANETS)} worlds fully terraformed",
        f"{len(achievement_ids_earned())}/{len(ACHIEVEMENTS)} achievements",
        "played " + _format_duration(_lifetime_playtime_seconds()),
    ]
    if runstate.prestige_level > 0:
        stats.append(f"prestige {runstate.prestige_level}")
    if runstate.mutators_run:
        stats.append("rules: " + ", ".join(MUTATOR_BY_ID[m_id]["label"] for m_id in runstate.mutators_run))
    return {"game": "SOL", "score": f"{average}%", "unit": "terraformed", "stats": stats}


def update_stats_panel_display():
    toggle = document.getElementById("stats-toggle-button")
    panel = document.getElementById("stats-panel")
    toggle.innerText = "Hide Stats & Share" if runstate.stats_open else "📊 Stats & Share"
    panel.hidden = not runstate.stats_open
    if not runstate.stats_open:
        return

    content = document.getElementById("stats-panel-content")
    content.innerHTML = ""

    heading = document.createElement("p")
    heading.className = "stats-panel-heading"
    heading.innerText = "Lifetime Stats"
    content.appendChild(heading)

    stat_lines = [
        ("Time played", _format_duration(_lifetime_playtime_seconds())),
        ("Manual clicks", str(runstate.total_manual_clicks)),
        ("Resources mined by hand", str(math.floor(runstate.lifetime_resources_mined_by_click + 1e-9))),
        (
            "Resources generated by automation",
            str(math.floor(runstate.lifetime_resources_generated_by_automation + 1e-9)),
        ),
        (
            "Generated while governed (all worlds)",
            str(math.floor(sum(planet_state[p]["governed_resource_generated"] for p in PLANETS) + 1e-9)),
        ),
        ("Generators built", str(runstate.lifetime_generators_built)),
        ("Recyclers built", str(runstate.lifetime_recyclers_built)),
        ("Trade routes built", str(runstate.lifetime_trade_routes_built)),
        ("Sky cities built", str(runstate.lifetime_sky_cities_built)),
        ("Research tiers completed", f"{runstate.completed_tiers}/{len(RESEARCH_TIERS)}"),
        ("Worlds visited", f"{len(runstate.visited_bodies)}/{len(PLANETS)}"),
        ("Achievements earned", f"{len(achievement_ids_earned())}/{len(ACHIEVEMENTS)}"),
        ("Prestige level", str(runstate.prestige_level)),
        ("Fastest full playthrough", best_run_text()),
        ("Best rhythm streak", str(runstate.best_click_streak)),
        ("Chain reactions found", f"{chains_found()}/{len(CHAINS)}"),
    ]
    for label, value in stat_lines:
        row = document.createElement("p")
        row.className = "stats-panel-row"
        row.innerText = f"{label}: {value}"
        content.appendChild(row)

    # The share card text (a static <pre>) and its Copy button live outside
    # this rebuilt content div (index.html) so the button's own click
    # listener is bound exactly once in setup() -- rebuilding it every tick
    # the panel is open, the same way the rows above are rebuilt, would
    # leak a new create_proxy() listener each time (press_feedback's own
    # module docstring already flags this exact class of leak).
    document.getElementById("share-card-text").innerText = build_share_card_text()


def update_cross_summary(viewer, target):
    # Shows `target`'s governed stats on `viewer`'s own view — e.g. Earth's
    # view shows a "Mars (governed)" widget, Mars's view shows an "Earth
    # (governed)" widget, and so on for every pair of real economies, once
    # there are more than two. Ids are viewer-prefixed (via _dom_id) so each
    # view's widget for the same target doesn't collide with any other
    # view's widget for that same target.
    #
    # The widget is hidden until `target` is unlocked (Earth is always
    # treated as unlocked, since it's the home planet and never appears in
    # unlocked_bodies) — enforced here so every view is consistent, not just
    # Earth's own (which used to be the only one gated, via
    # update_travel_display(), leaking every other view's not-yet-unlocked
    # bodies' names/existence).
    state = planet_state[target]

    def widget_id(field):
        return _dom_id(viewer, f"{target.lower()}-summary-{field}")

    document.getElementById(_dom_id(viewer, f"{target.lower()}-summary")).hidden = (
        target != "Earth" and target not in runstate.unlocked_bodies
    )
    document.getElementById(widget_id("resource")).innerText = str(math.floor(state["resource_count"] + 1e-9))
    document.getElementById(widget_id("generators")).innerText = str(state["generator_count"])
    document.getElementById(widget_id("recyclers")).innerText = str(state["recycler_count"])
    document.getElementById(widget_id("ecology")).innerText = str(round(state["ecology_health"]))


def update_all_cross_summaries():
    for viewer in PLANETS:
        for target in PLANETS:
            if viewer != target:
                update_cross_summary(viewer, target)


def update_away_summary():
    # Every undeveloped body (Moon, Venus, Asteroid Belt, Pluto, Jupiter's
    # Moons, Saturn's Moons) shares this one placeholder screen, showing
    # ALL real economies as "governed" — not just Earth's, a gap flagged
    # (and left as a known simplification) back in Milestone 6. Each future
    # milestone that turns one of these bodies into a real economy needs to
    # add its own summary block here too, same as Mars's was just added.
    document.getElementById("away-planet-name").innerText = BODY_DISPLAY_NAMES.get(
        runstate.current_planet, runstate.current_planet.upper()
    )
    for planet in PLANETS:
        state = planet_state[planet]
        prefix = f"away-{planet.lower()}"
        document.getElementById(f"{prefix}-resource").innerText = str(math.floor(state["resource_count"] + 1e-9))
        document.getElementById(f"{prefix}-generators").innerText = str(state["generator_count"])
        document.getElementById(f"{prefix}-recyclers").innerText = str(state["recycler_count"])
        document.getElementById(f"{prefix}-ecology").innerText = str(round(state["ecology_health"]))


# --- A6 / A17 / A21 / A8-support: stats-panel extras ---
STATS_CODE_PREFIX = "SOLSTATS1:"
_STATS_CODE_FIELDS = (
    "total_ticks",
    "total_manual_clicks",
    "lifetime_resources_mined_by_click",
    "lifetime_resources_generated_by_automation",
    "lifetime_generators_built",
    "lifetime_recyclers_built",
    "lifetime_trade_routes_built",
    "lifetime_sky_cities_built",
)
COMPARE_FIELDS = (
    "prestige_level",
    "total_ticks",
    "total_manual_clicks",
    "lifetime_generators_built",
    "lifetime_recyclers_built",
    "lifetime_trade_routes_built",
    "lifetime_sky_cities_built",
    "governor_purchase_count",
)


def export_stats_code():
    if runstate._scarcity is not None:
        return ""
    # Z8: codec now lives in shared/export_progress.py (the "portable
    # progress-code" pattern shared with Aftermath's E12) -- behavior is
    # unchanged, same STATS_CODE_PREFIX, same flat-counter payload.
    payload = {name: vars(runstate)[name] for name in _STATS_CODE_FIELDS}
    payload["prestige_level"] = runstate.prestige_level
    return export_progress.encode_progress_code(payload, prefix=STATS_CODE_PREFIX)


def import_stats_code(code):
    """Returns (ok, message). Only ever raises a counter, never lowers one, so
    a stale code from an old device can't undo newer progress."""
    if runstate._scarcity is not None:
        return False, "A Scarcity Run is on. Leave it first: stats codes belong to your campaign."
    ok, payload = export_progress.decode_progress_code(
        code, prefix=STATS_CODE_PREFIX, bad_format_message="That doesn't look like a SOL stats code."
    )
    if not ok:
        return False, payload
    if not export_progress.validate_numeric_fields(payload, _STATS_CODE_FIELDS):
        return False, "That stats code has invalid values."
    merged = export_progress.merge_counters_max(
        {name: vars(runstate)[name] for name in _STATS_CODE_FIELDS}, payload, _STATS_CODE_FIELDS
    )
    for name in _STATS_CODE_FIELDS:
        vars(runstate)[name] = merged[name]
    return True, "Stats imported. Counters only ever go up."


def compare_values():
    values = {name: vars(runstate).get(name, 0) for name in COMPARE_FIELDS}
    values["governor_purchase_count"] = runstate.governor_purchase_count
    return values


def _flash_copy_button(button, done_text):
    original = "📋 Copy to Clipboard"
    button.innerText = done_text

    def _restore(*args):
        button.innerText = original
        proxy.destroy()

    proxy = create_proxy(_restore)
    setTimeout(proxy, 1500)
