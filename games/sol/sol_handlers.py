"""Click and change handlers: every on_* function."""

import json

import challenges
from js import document
from pyodide.ffi import create_proxy

import sol_runstate as runstate
from sol_achievements import update_achievements_display
from sol_actions import (
    _buy_generator, _buy_recycler, _buy_sky_city, _buy_trade_route, _confirm_dialog_ask,
    _cycle_trade_destination, _mine, _reset_world, _return_to_earth, _travel_from_button, _travel_to,
    research_node_action,
)
from sol_capsules import (
    _capsule_refs, capsule_diff, capsule_replay, delete_capsule, freeze_capsule, update_capsules_display,
)
from sol_charter import megaproject_progress, reroll_mission, send_to_megaproject
from sol_charter_panel import update_charter_display
from sol_codex import CLUE_BY_ID, _codex_hints
from sol_doctrines import (
    DOCTRINE_ACTIONS, DOCTRINE_CONDITIONS, DOCTRINE_MAX_RULES, DRY_RUN_TICKS, _doctrine_draft,
    _doctrine_reset_runtime, doctrine_rule_limit, doctrine_rules,
)
from sol_econ import (
    _forget_close_call_history, _recompute_research, research_tree_collapsed, update_governor_display,
    update_research_display, update_research_tree_display, update_resource_display,
)
from sol_ghost import _refresh_ghost_strip, ghost_enabled, make_friend_ghost, update_splits_display
from sol_headless import (
    _blueprint_status, _ghost, blueprint_code, doctrine_dry_run, parse_blueprint, run_stress_test,
    update_blueprint_ghost, update_doctrine_display,
)
from sol_observatory import (
    SURVEY_PER_PRESTIGE, _award_survey, catch_comet, claim_point, comets_caught_run, contest_point,
    partner_point, survey_region, update_comet_strip, update_observatory_display,
)
from sol_overview import update_overview_display
from sol_panels import update_changelog_display, update_governor_report_display
from sol_planner import (
    _add_build_step, _node_unlockable, _refresh_all_cost_displays, build_plan_tsv,
    update_build_plan_display, update_epilogue_display, update_prestige_tree_display, update_win_display,
)
from sol_rhythm import _action_log, _chain_cooldown_until, run_splits, update_chains_display
from sol_rules import (
    BUILD_PLAN_SUGGESTED, GHOST_ON_KEY, GOVERNOR_BUDGET_MAX, GOVERNOR_BUDGET_MIN, GOVERNOR_BUDGET_STEP,
    GOVERNOR_PERSONALITIES, PLANETS, PRESTIGE_BONUS_PER_LEVEL, PRESTIGE_TREE_BY_ID, RESEARCH_TIERS,
    SPECIALIZATION_LABELS, TICK_INTERVAL_MS, _challenge_on, _prestige_available, build_plan, planet_state,
    prestige_has, researched_nodes, specialization_eligible,
)
from sol_run import _full_render
from sol_runmods import (
    _mutator_confirm_note, _toggle_mutator_pick, megaprojects_built, mutator_points, mutators_next,
)
from sol_scarcity import _scarcity_refs
from sol_scarcity_panel import update_scarcity_display
from sol_session import leave_scarcity_run, start_scarcity_run
from sol_statsview import (
    _flash_copy_button, build_share_card_text, compare_values, export_stats_code, import_stats_code,
    update_stats_panel_display,
)
from sol_util import (
    _fresh_planet_state, _target_attr, _today_utc, _write_local_storage_item, clamp, press_feedback,
)


def on_toggle_splits(event=None):
    runstate.splits_open = not runstate.splits_open
    update_splits_display()


def on_toggle_chains(event=None):
    runstate.chains_open = not runstate.chains_open
    update_chains_display()


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def on_toggle_governor_report(event=None):
    runstate.governor_report_open = not runstate.governor_report_open
    update_governor_report_display()


def on_toggle_stats(event=None):
    runstate.stats_open = not runstate.stats_open
    update_stats_panel_display()


def on_copy_share_card(event=None):
    # Clipboard access is browser-only (no navigator in the pytest fake-DOM
    # harness) -- guarded the same lazy-import-and-degrade way
    # _read_achievements_json() guards its own browser-only access, so this
    # stays importable/callable under test even though the actual copy
    # can't happen there.
    text = build_share_card_text()
    status = document.getElementById("copy-share-card-status")
    try:
        import js  # noqa: PLC0415

        js.navigator.clipboard.writeText(text)
        status.innerText = "Copied to clipboard!"
        _flash_copy_button(document.getElementById("copy-share-card-button"), "✓ Copied!")
    except (ImportError, AttributeError):
        status.innerText = "Couldn't access the clipboard — copy the text above manually."
    press_feedback(document.getElementById("copy-share-card-button"))


def on_earth_click(event):
    _mine("Earth", event)


def on_mars_click(event):
    _mine("Mars", event)


def on_moon_click(event):
    _mine("Moon", event)


def on_venus_click(event):
    _mine("Venus", event)


def on_asteroid_belt_click(event):
    _mine("AsteroidBelt", event)


def on_pluto_click(event):
    _mine("Pluto", event)


def on_jupiter_moons_click(event):
    _mine("JupiterMoons", event)


def on_saturn_moons_click(event):
    _mine("SaturnMoons", event)


def on_earth_buy_generator(event):
    _buy_generator("Earth")


def on_mars_buy_generator(event):
    _buy_generator("Mars")


def on_moon_buy_generator(event):
    _buy_generator("Moon")


def on_venus_buy_generator(event):
    _buy_generator("Venus")


def on_asteroid_belt_buy_generator(event):
    _buy_generator("AsteroidBelt")


def on_pluto_buy_generator(event):
    _buy_generator("Pluto")


def on_jupiter_moons_buy_generator(event):
    _buy_generator("JupiterMoons")


def on_saturn_moons_buy_generator(event):
    _buy_generator("SaturnMoons")


def on_earth_buy_recycler(event):
    _buy_recycler("Earth")


def on_mars_buy_recycler(event):
    _buy_recycler("Mars")


def on_moon_buy_recycler(event):
    _buy_recycler("Moon")


def on_venus_buy_recycler(event):
    _buy_recycler("Venus")


def on_asteroid_belt_buy_recycler(event):
    _buy_recycler("AsteroidBelt")


def on_pluto_buy_recycler(event):
    _buy_recycler("Pluto")


def on_jupiter_moons_buy_recycler(event):
    _buy_recycler("JupiterMoons")


def on_saturn_moons_buy_recycler(event):
    _buy_recycler("SaturnMoons")


def on_earth_buy_trade_route(event):
    _buy_trade_route("Earth")


def on_mars_buy_trade_route(event):
    _buy_trade_route("Mars")


def on_moon_buy_trade_route(event):
    _buy_trade_route("Moon")


def on_venus_buy_trade_route(event):
    _buy_trade_route("Venus")


def on_asteroid_belt_buy_trade_route(event):
    _buy_trade_route("AsteroidBelt")


def on_pluto_buy_trade_route(event):
    _buy_trade_route("Pluto")


def on_jupiter_moons_buy_trade_route(event):
    _buy_trade_route("JupiterMoons")


def on_saturn_moons_buy_trade_route(event):
    _buy_trade_route("SaturnMoons")


def on_jupiter_moons_buy_sky_city(event):
    _buy_sky_city("JupiterMoons")


def on_saturn_moons_buy_sky_city(event):
    _buy_sky_city("SaturnMoons")


def on_earth_cycle_trade_destination(event):
    _cycle_trade_destination("Earth")


def on_mars_cycle_trade_destination(event):
    _cycle_trade_destination("Mars")


def on_moon_cycle_trade_destination(event):
    _cycle_trade_destination("Moon")


def on_venus_cycle_trade_destination(event):
    _cycle_trade_destination("Venus")


def on_asteroid_belt_cycle_trade_destination(event):
    _cycle_trade_destination("AsteroidBelt")


def on_pluto_cycle_trade_destination(event):
    _cycle_trade_destination("Pluto")


def on_jupiter_moons_cycle_trade_destination(event):
    _cycle_trade_destination("JupiterMoons")


def on_saturn_moons_cycle_trade_destination(event):
    _cycle_trade_destination("SaturnMoons")


def on_research_node_click(event):
    node_id = _target_attr(event, "data-node")
    if not node_id:
        return
    if research_node_action(node_id):
        update_resource_display("Earth")
        update_research_display()
        update_research_tree_display()


def on_priority_growth(event):
    runstate.governor_priority = "growth"
    update_governor_display()
    press_feedback(document.getElementById("priority-growth-button"))


def on_priority_balance(event):
    runstate.governor_priority = "balance"
    update_governor_display()
    press_feedback(document.getElementById("priority-balance-button"))


def on_priority_ecology(event):
    runstate.governor_priority = "ecology"
    update_governor_display()
    press_feedback(document.getElementById("priority-ecology-button"))


def on_budget_increase(event):
    runstate.governor_budget_pct = clamp(runstate.governor_budget_pct + GOVERNOR_BUDGET_STEP, GOVERNOR_BUDGET_MIN, GOVERNOR_BUDGET_MAX)
    update_governor_display()
    press_feedback(document.getElementById("budget-increase-button"))


def on_budget_decrease(event):
    runstate.governor_budget_pct = clamp(runstate.governor_budget_pct - GOVERNOR_BUDGET_STEP, GOVERNOR_BUDGET_MIN, GOVERNOR_BUDGET_MAX)
    update_governor_display()
    press_feedback(document.getElementById("budget-decrease-button"))


def on_dismiss_away_report(event=None):
    document.getElementById("away-report").hidden = True


def on_travel_moon(event):
    _travel_from_button("Moon", "travel-moon-button")


def on_travel_venus(event):
    _travel_from_button("Venus", "travel-venus-button")


def on_travel_asteroid_belt(event):
    _travel_from_button("AsteroidBelt", "travel-asteroid-belt-button")


def on_travel_pluto(event):
    _travel_from_button("Pluto", "travel-pluto-button")


def on_travel_jupiter_moons(event):
    _travel_from_button("JupiterMoons", "travel-jupiter-moons-button")


def on_travel_saturn_moons(event):
    _travel_from_button("SaturnMoons", "travel-saturn-moons-button")


def on_travel_mars(event):
    _travel_from_button("Mars", "travel-mars-button")


def on_return_to_earth_from_away_view(event):
    _return_to_earth()
    press_feedback(document.getElementById("return-to-earth-button"))


def on_return_to_earth_from_mars(event):
    _return_to_earth()
    press_feedback(document.getElementById("mars-return-to-earth-button"))


def on_return_to_earth_from_moon(event):
    _return_to_earth()
    press_feedback(document.getElementById("moon-return-to-earth-button"))


def on_return_to_earth_from_venus(event):
    _return_to_earth()
    press_feedback(document.getElementById("venus-return-to-earth-button"))


def on_return_to_earth_from_asteroid_belt(event):
    _return_to_earth()
    press_feedback(document.getElementById("asteroidbelt-return-to-earth-button"))


def on_return_to_earth_from_pluto(event):
    _return_to_earth()
    press_feedback(document.getElementById("pluto-return-to-earth-button"))


def on_return_to_earth_from_jupiter_moons(event):
    _return_to_earth()
    press_feedback(document.getElementById("jupitermoons-return-to-earth-button"))


def on_return_to_earth_from_saturn_moons(event):
    _return_to_earth()
    press_feedback(document.getElementById("saturnmoons-return-to-earth-button"))


def on_reset_earth(event):
    _reset_world("Earth")


def on_reset_mars(event):
    _reset_world("Mars")


def on_reset_moon(event):
    _reset_world("Moon")


def on_reset_venus(event):
    _reset_world("Venus")


def on_reset_asteroid_belt(event):
    _reset_world("AsteroidBelt")


def on_reset_pluto(event):
    _reset_world("Pluto")


def on_reset_jupiter_moons(event):
    _reset_world("JupiterMoons")


def on_reset_saturn_moons(event):
    _reset_world("SaturnMoons")


def on_toggle_overview(event=None):
    runstate.overview_open = not runstate.overview_open
    update_overview_display()


def on_overview_click(event):
    action = _target_attr(event, "data-action")
    planet = _target_attr(event, "data-planet")
    value = _target_attr(event, "data-value")
    if action is None or planet not in PLANETS:
        return
    if action == "travel":
        _travel_to(planet)
    elif action == "personality" and value in GOVERNOR_PERSONALITIES:
        planet_state[planet]["governor_personality"] = value
    elif action == "specialize" and value in SPECIALIZATION_LABELS and specialization_eligible(planet):
        state = planet_state[planet]
        state["specialization"] = None if state.get("specialization") == value else value
    update_overview_display()
    update_governor_report_display()


def on_toggle_build_plan(event=None):
    runstate.build_plan_open = not runstate.build_plan_open
    update_build_plan_display()


def on_build_plan_add(event=None):
    field = document.getElementById("build-plan-input")
    if _add_build_step(getattr(field, "value", "") or ""):
        field.value = ""
    update_build_plan_display()


def on_build_plan_suggest(event=None):
    for text in BUILD_PLAN_SUGGESTED:
        if not any(step["text"] == text for step in build_plan):
            _add_build_step(text)
    update_build_plan_display()


def on_build_plan_copy(event=None):
    text = build_plan_tsv()
    status = document.getElementById("build-plan-copy-status")
    output = document.getElementById("build-plan-copy-output")
    output.value = text

    def _manual(*args):
        output.hidden = False
        status.innerText = "Could not reach the clipboard: select the text below and copy it yourself."

    if not build_plan:
        output.hidden = True
        status.innerText = "Nothing to copy yet: add a step first."
        return
    try:
        import js  # noqa: PLC0415

        promise = js.navigator.clipboard.writeText(text)
        output.hidden = True
        status.innerText = "Copied as tab-separated rows: paste into a spreadsheet."
        catch = getattr(promise, "catch", None)
        if catch is not None:
            def _failed(*args):
                proxy.destroy()
                _manual()

            proxy = create_proxy(_failed)
            catch(proxy)
    except (ImportError, AttributeError):
        _manual()


def on_build_plan_clear_done(event=None):
    build_plan[:] = [step for step in build_plan if not step["done"]]
    update_build_plan_display()


def on_build_plan_click(event):
    action = _target_attr(event, "data-action")
    raw = _target_attr(event, "data-step")
    try:
        index = int(raw)
    except (TypeError, ValueError):
        return
    if not 0 <= index < len(build_plan):
        return
    if action == "toggle":
        build_plan[index]["done"] = not build_plan[index]["done"]
    elif action == "remove":
        del build_plan[index]
    update_build_plan_display()


def on_toggle_prestige_tree(event=None):
    runstate.prestige_tree_open = not runstate.prestige_tree_open
    update_prestige_tree_display()


def on_prestige_tree_click(event):
    action = _target_attr(event, "data-action")
    if action == "unlock":
        node = PRESTIGE_TREE_BY_ID.get(_target_attr(event, "data-node"))
        if node is not None and _node_unlockable(node):
            runstate.prestige_nodes.add(node["id"])
    elif action == "challenge" and prestige_has("ng_challenge"):
        runstate.ng_challenge_active = not runstate.ng_challenge_active
    elif action == "mutator":
        _toggle_mutator_pick(_target_attr(event, "data-mutator"))
    update_prestige_tree_display()
    _refresh_all_cost_displays()


def on_toggle_sandbox(event=None):
    if not _prestige_available():
        return
    runstate.sandbox_mode = not runstate.sandbox_mode
    _refresh_all_cost_displays()
    update_win_display()


def on_toggle_epilogue(event=None):
    if not _prestige_available():
        runstate.epilogue_open = False
    else:
        runstate.epilogue_open = not runstate.epilogue_open
    update_epilogue_display()


def on_export_stats(event=None):
    if runstate._scarcity is not None:
        document.getElementById("stats-code-status").innerText = "A Scarcity Run is on. Leave it first: stats codes belong to your campaign."
        return
    document.getElementById("stats-code-output").value = export_stats_code()
    document.getElementById("stats-code-status").innerText = "Copy this code and keep it somewhere safe."


def on_import_stats(event=None):
    field = document.getElementById("stats-code-input")
    ok, message = import_stats_code(getattr(field, "value", ""))
    document.getElementById("stats-code-status").innerText = message
    if ok:
        update_stats_panel_display()


def on_compare_run(event=None):
    if runstate._scarcity is not None:
        document.getElementById("compare-run-results").innerText = "A Scarcity Run is on. Leave it first to compare your campaign."
        return
    try:
        import js  # noqa: PLC0415

        js.SolCompare.run(json.dumps(compare_values()))
    except (ImportError, AttributeError):
        document.getElementById("compare-run-results").innerText = "Comparison isn't available right now."


def on_research_tree_click(event):
    raw = _target_attr(event, "data-tier")
    try:
        index = int(raw)
    except (TypeError, ValueError):
        return
    if not 0 <= index < len(RESEARCH_TIERS):
        return
    if index in research_tree_collapsed:
        research_tree_collapsed.discard(index)
    else:
        research_tree_collapsed.add(index)
    update_research_tree_display()


def on_prestige(event=None):
    # No `global` needed here -- `prestige_level` is only read (for
    # `next_level`/`next_bonus_pct`'s preview text below); every actual
    # mutation happens inside `_do_prestige()`, which declares its own.
    if not _prestige_available():
        return

    next_level = runstate.prestige_level + 1
    next_bonus_pct = round(PRESTIGE_BONUS_PER_LEVEL * next_level * 100)

    def _do_prestige():
        megaproject_progress.clear()  # A-13: a megaproject belongs to the run that built it
        comets_caught_run.clear()  # A-10: each run has its comets again
        runstate._comet_since = None
        _award_survey(SURVEY_PER_PRESTIGE)  # A-9
        megaprojects_built.clear()

        runstate.prestige_level = next_level
        runstate.run_start_tick = runstate.total_ticks  # R-10: a new run starts its own clock
        runstate.run_completed = False
        run_splits.clear()  # A-30: a new run starts new splits (the personal best stays)
        del _action_log[:]
        _chain_cooldown_until.clear()
        # A1/A3: 1 tree point per prestige, +1 if the New Game+ Challenge was on.
        runstate.prestige_points_earned += 1 + (1 if _challenge_on() else 0) + mutator_points(runstate.mutators_run)
        runstate.mutators_run = list(mutators_next)  # A-3: the picks are locked in the moment a new run starts
        runstate.sandbox_mode = False
        runstate.epilogue_open = False
        _forget_close_call_history()
        runstate._departure_snapshots.clear()
        for planet in PLANETS:
            planet_state[planet] = _fresh_planet_state(planet)
        researched_nodes.clear()
        _recompute_research()
        runstate.unlocked_bodies = set()
        # Prestige is a genuine "run reset", not a lifetime wipe: visited_bodies
        # goes back to just Earth (matching a fresh planet_state, since nothing
        # else has been visited yet in this new run), current_planet returns to
        # Earth, and the Governor's own run-scoped counters (not the lifetime
        # ones in the stats panel) reset to their fresh-game defaults.
        # any_generator_ever_built resets too -- deliberately -- so a player who
        # already automated everything pre-prestige gets a genuine second shot
        # at the pure-clicker achievements (A2/A13) in their New Game+, without
        # touching manual_labor_hit/off_the_grid_hit themselves, which (once
        # True) never reset.
        runstate.visited_bodies = {"Earth"}
        runstate.current_planet = "Earth"
        runstate.governor_priority = "balance"
        runstate.governor_budget_pct = 50.0
        runstate.governor_tick_count = 0
        runstate.governor_purchase_count = 0
        runstate.any_generator_ever_built = False
        if prestige_has("head_start"):
            planet_state["Earth"]["resource_count"] = 50.0

        _full_render()
        press_feedback(document.getElementById("prestige-button"))

    # Z22 cross-game audit: migrated from a native browser confirm() (see
    # `_confirm_dialog_ask()`'s own comment above `_reset_world`) to the
    # shared ConfirmDialog, same as reset-this-world.
    _confirm_dialog_ask(
        action_id="sol-prestige",
        message=(
            f"Prestige into a New Game+? Every world resets to its starting state -- "
            f"research, travel, and the Governor included -- and you keep a permanent "
            f"+{next_bonus_pct}% resource yield (Prestige Level {next_level}) and a Prestige Tree "
            "point" + _mutator_confirm_note() + ". Lifetime stats, tree unlocks and every achievement you've "
            "already earned are kept. This cannot be undone."
        ),
        confirm_label="Prestige into New Game+",
        on_confirm=_do_prestige,
    )


def on_toggle_charter(event=None):
    runstate.charter_open = not runstate.charter_open
    update_charter_display()


def on_charter_click(event):
    action = _target_attr(event, "data-action")
    if action == "reroll":
        reroll_mission(_target_attr(event, "data-mission"))
    elif action == "stress":
        run_stress_test()
    elif action == "hint":
        clue_id = _target_attr(event, "data-clue")
        if clue_id in CLUE_BY_ID:
            _codex_hints.add(clue_id)
    elif action == "send":
        send_to_megaproject(_target_attr(event, "data-project"), _target_attr(event, "data-planet"))
    update_charter_display()


def on_toggle_doctrine(event=None):
    runstate.doctrine_open = not runstate.doctrine_open
    update_doctrine_display()


def on_doctrine_click(event):
    action = _target_attr(event, "data-action")
    value = _target_attr(event, "data-value")
    if action == "draft-planet" and value in PLANETS:
        _doctrine_draft["planet"] = value
    elif action == "draft-cond" and value and ":" in value:
        cond, _, level = value.partition(":")
        if cond in DOCTRINE_CONDITIONS and level.isdigit() and int(level) in DOCTRINE_CONDITIONS[cond]["levels"]:
            _doctrine_draft["cond"], _doctrine_draft["level"] = cond, int(level)
    elif action == "draft-action" and value in DOCTRINE_ACTIONS:
        _doctrine_draft["action"] = value
    elif action == "add":
        if len(doctrine_rules) < doctrine_rule_limit():
            doctrine_rules.append(dict(_doctrine_draft))
            _doctrine_reset_runtime()
    elif action == "remove":
        index = int(value) if value and value.isdigit() else -1
        if 0 <= index < len(doctrine_rules):
            del doctrine_rules[index]
            _doctrine_reset_runtime()
    elif action == "dry-run":
        total, counts = doctrine_dry_run()
        runstate._doctrine_dry_text = (
            f"Over the next {DRY_RUN_TICKS} ticks ({DRY_RUN_TICKS * TICK_INTERVAL_MS / 1000:g} seconds) these rules "
            f"would have fired {total} time{'s' if total != 1 else ''}"
            + (": " + ", ".join(f"rule {i + 1} x{n}" for i, n in sorted(counts.items())) if counts else "")
            + ". Nothing was changed."
        )
    runstate._doctrine_signature = None
    update_doctrine_display()


def on_blueprint_make(event=None):
    code = blueprint_code()
    output = document.getElementById("blueprint-output")
    output.value = code
    output.hidden = False
    try:
        import js  # noqa: PLC0415

        js.navigator.clipboard.writeText(code)
        _blueprint_status("Blueprint made and copied. Share the code; the other player pastes it under Import.")
    except (ImportError, AttributeError):
        _blueprint_status("Blueprint made: select the code below and copy it.")


def on_blueprint_import(event=None):
    ok, result = parse_blueprint(document.getElementById("blueprint-input").value)
    if not ok:
        _blueprint_status(result)
        return
    _ghost["steps"], _ghost["rules"], _ghost["mutators"] = result["steps"], result["rules"], result["mutators"]
    _blueprint_status("Blueprint loaded as a ghost below. Nothing has changed in your game yet.")
    update_blueprint_ghost()


def on_blueprint_ghost_click(event):
    action = _target_attr(event, "data-action")
    if action == "clear":
        _ghost["steps"], _ghost["rules"], _ghost["mutators"] = [], [], []
    elif action == "add-step":
        raw = _target_attr(event, "data-step")
        index = int(raw) if raw and raw.isdigit() else -1
        if 0 <= index < len(_ghost["steps"]):
            _add_build_step(_ghost["steps"][index])
    elif action == "add-all":
        for text in _ghost["steps"]:
            if text not in {step["text"] for step in build_plan}:
                _add_build_step(text)
    elif action == "adopt-rules":
        room = DOCTRINE_MAX_RULES - len(doctrine_rules)
        have = {tuple(sorted(rule.items())) for rule in doctrine_rules}
        added = 0
        for rule in _ghost["rules"]:
            if added < room and tuple(sorted(rule.items())) not in have:
                doctrine_rules.append(dict(rule))
                added += 1
        if added:
            _doctrine_reset_runtime()
        _blueprint_status(f"Added {added} rule(s) to your Doctrines. Rules above your limit wait until it is raised.")
    elif action == "use-mutators":
        mutators_next[:] = list(_ghost["mutators"])
        _blueprint_status("Your mutator picks for the next run now match the blueprint.")
    update_blueprint_ghost()
    update_build_plan_display()
    update_doctrine_display()


def on_comet_click(event=None):
    catch_comet()
    update_comet_strip()
    update_observatory_display()


def on_toggle_observatory(event=None):
    runstate.observatory_open = not runstate.observatory_open
    update_observatory_display()


def on_observatory_click(event):
    action = _target_attr(event, "data-action")
    if action == "survey":
        survey_region()
    elif action == "claim":
        claim_point(_target_attr(event, "data-point"))
    elif action == "partner":
        partner_point(_target_attr(event, "data-point"))
    elif action == "contest":
        contest_point(_target_attr(event, "data-point"))
    update_observatory_display()


# the panel
def on_toggle_capsules(event=None):
    runstate.capsules_open = not runstate.capsules_open
    update_capsules_display()


def on_capsules_click(event):
    action = _target_attr(event, "data-action")
    if action == "freeze":
        field = _capsule_refs.get("name")
        if freeze_capsule(field.value if field is not None else "") is not None and field is not None:
            field.value = ""  # ready for the next name
    else:
        try:
            capsule_id = int(_target_attr(event, "data-capsule"))
        except (TypeError, ValueError):
            capsule_id = None
        if action == "replay":
            capsule_replay(capsule_id)
        elif action == "diff":
            capsule_diff(capsule_id)
        elif action == "delete":
            delete_capsule(capsule_id)
    update_capsules_display()


def on_toggle_scarcity(event=None):
    runstate.scarcity_open = not runstate.scarcity_open
    update_scarcity_display(force=True)


def on_scarcity_click(event):
    action = _target_attr(event, "data-action")
    value = _target_attr(event, "data-value")
    date_text = _target_attr(event, "data-date")
    if action == "play" and date_text:
        start_scarcity_run(date_text)
    elif action == "leave":
        leave_scarcity_run()
    elif action == "pick" and date_text:
        today = _today_utc()
        if today and challenges.playable(date_text, today):
            runstate._scarcity_selected = date_text
    elif action == "month" and value in ("-1", "1") and runstate._scarcity_month is not None:
        today = _today_utc() or challenges.EPOCH
        target = challenges.shift_month(*runstate._scarcity_month, int(value))
        if challenges.month_of(challenges.EPOCH) <= target <= challenges.month_of(today):
            runstate._scarcity_month = target
    elif action == "ghost-choice" and value in ("none", "best", "par", "friend") and runstate._scarcity is None:
        runstate._scarcity_ghost_choice = value
    elif action == "friend-ghost" and date_text and runstate._scarcity is None:
        field = _scarcity_refs.get("friend")
        ok, message = make_friend_ghost(getattr(field, "value", ""), date_text)
        runstate._scarcity_notice = message
        if ok:
            runstate._scarcity_ghost_choice = "friend"
    update_scarcity_display(force=True)


def on_scarcity_leave(event=None):
    leave_scarcity_run()


# the speedrun splits panel gains the ghost section (built once; the rows below it update in place)
def on_splits_click(event):
    action = _target_attr(event, "data-action")
    if action == "ghost-toggle":
        _write_local_storage_item(GHOST_ON_KEY, "off" if ghost_enabled() else "on")
        _refresh_ghost_strip()
        update_splits_display(force=True)
