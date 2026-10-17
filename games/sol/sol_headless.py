"""Headless runs on a copy (Doctrine dry run, Ecology Stress Test, Blueprint Swap) and the Doctrines panel."""

import copy

import export_progress
from js import document

import sol_runstate as runstate
from sol_doctrines import (
    DOCTRINE_ACTIONS, DOCTRINE_CONDITIONS, DRY_RUN_TICKS, _clean_doctrine_rules, _doctrine_draft,
    _doctrine_refs, doctrine_rule_limit, doctrine_rule_text, doctrine_rules, doctrines_unlocked,
)
from sol_rules import (
    BUILD_PLAN_MAX_LEN, BUILD_PLAN_MAX_STEPS, ECOLOGY_MAX, LOW_ECOLOGY_THRESHOLD, PLANETS,
    PLANET_DISPLAY_NAMES, TICK_INTERVAL_MS, _prestige_available, build_plan, planet_state,
)
from sol_runmods import MUTATOR_BY_ID, _clean_mutators, _stress_factors, mutators_next
from sol_sim import _incoming_trade_restore, _simulate_planet, governor_step
from sol_util import _make_button, _make_text, _overview_planets


def _run_headless(ticks, on_tick=None, all_governed=False):
    """Runs `ticks` of simulate plus Governor (and Doctrines) on a copy of the numbers: the DOM is never touched
    and every number is put back in a `finally`. `on_tick(i)` is called after each tick. With `all_governed`
    nobody is standing anywhere, so the Governor runs every world (and the sandbox is off). Returns the
    per-rule fire counts of the run."""
    snapshot = (
        copy.deepcopy(planet_state), runstate.governor_purchase_count, runstate.governor_tick_count, runstate.lifetime_generators_built,
        runstate.lifetime_recyclers_built, runstate.lifetime_trade_routes_built, runstate.lifetime_resources_generated_by_automation,
        runstate.any_generator_ever_built, dict(runstate._doctrine_fired_counts), dict(runstate._doctrine_last_fired),
        dict(runstate._doctrine_relief_ready), runstate.total_ticks, runstate.current_planet, runstate.sandbox_mode, runstate._active_anomaly,
    )
    runstate._doctrine_fired_counts = {}
    runstate._dry_run = True
    try:
        if all_governed:
            runstate.current_planet, runstate.sandbox_mode, runstate._active_anomaly = "Deep space", False, None
        for index in range(ticks):
            runstate.total_ticks += 1
            incoming = {p: _incoming_trade_restore(p) for p in PLANETS}
            for planet in PLANETS:
                _simulate_planet(planet, incoming[planet])
            governor_step()
            if on_tick is not None:
                on_tick(index)
        counts = dict(runstate._doctrine_fired_counts)
    finally:
        runstate._dry_run = False
        _stress_factors.clear()
        (saved_state, runstate.governor_purchase_count, runstate.governor_tick_count, runstate.lifetime_generators_built,
         runstate.lifetime_recyclers_built, runstate.lifetime_trade_routes_built, runstate.lifetime_resources_generated_by_automation,
         runstate.any_generator_ever_built, runstate._doctrine_fired_counts, runstate._doctrine_last_fired, runstate._doctrine_relief_ready,
         runstate.total_ticks, runstate.current_planet, runstate.sandbox_mode, runstate._active_anomaly) = snapshot
        for planet, values in saved_state.items():
            planet_state[planet].clear()
            planet_state[planet].update(values)
    return counts


def doctrine_dry_run():
    """A-8: runs the rules for DRY_RUN_TICKS on a copy of the numbers. Returns (total fires, per-rule counts)."""
    counts = _run_headless(DRY_RUN_TICKS)
    return sum(counts.values()), counts


def _doctrine_structure_signature():
    return (doctrines_unlocked(), doctrine_rule_limit(), tuple(tuple(sorted(r.items())) for r in doctrine_rules),
            tuple(sorted(_doctrine_draft.items())), tuple(_overview_planets()), runstate._doctrine_dry_text, runstate.current_planet)


def _doctrine_pill(text, attrs, selected):
    return _make_button(text, attrs, None, selected=selected)


def _build_doctrine_panel():
    panel = document.getElementById("doctrine-panel")
    panel.innerHTML = ""
    _doctrine_refs.clear()
    panel.appendChild(_make_text("stats-panel-heading", f"Governor Doctrines ({len(doctrine_rules)}/{doctrine_rule_limit()} rules)"))
    panel.appendChild(_make_text(
        "chains-intro",
        "If/then rules for worlds you are not standing on, checked in order every tick. They are kept in a save and "
        "sleep until Automation Basics is researched again after a prestige. Standing Orders in the Prestige "
        "Tree raises the limit from 3 to 5."))
    for index, rule in enumerate(doctrine_rules):
        card = document.createElement("div")
        card.className = "chain-card chain-card--found"
        card.appendChild(_make_text("chain-card-name", f"{index + 1}. {doctrine_rule_text(rule)}"))
        fired = _make_text("chain-card-count", "")
        card.appendChild(fired)
        if rule["planet"] == runstate.current_planet:
            card.appendChild(_make_text("chain-card-detail", "You are standing here, so the Governor is not running this rule right now."))
        if index >= doctrine_rule_limit():
            card.appendChild(_make_text("chain-card-detail", "Over the limit, so this rule is not running."))
        card.appendChild(_make_button("Remove", {"data-action": "remove", "data-value": str(index)}, None))
        panel.appendChild(card)
        _doctrine_refs[index] = fired
    if not doctrine_rules:
        panel.appendChild(_make_text("chains-intro", "No rules yet. Build one below."))
    panel.appendChild(_make_text("stats-panel-heading", "New rule"))
    row = document.createElement("div")
    row.className = "overview-actions"
    row.appendChild(_make_text("overview-actions-label", "World:", "span"))
    for planet in _overview_planets():
        row.appendChild(_doctrine_pill(PLANET_DISPLAY_NAMES.get(planet, planet),
                                       {"data-action": "draft-planet", "data-value": planet},
                                       _doctrine_draft["planet"] == planet))
    panel.appendChild(row)
    row = document.createElement("div")
    row.className = "overview-actions"
    row.appendChild(_make_text("overview-actions-label", "When:", "span"))
    resource = PLANETS[_doctrine_draft["planet"]]["resource_name"] if _doctrine_draft["planet"] in PLANETS else "stock"
    for cond, spec in DOCTRINE_CONDITIONS.items():
        for level in spec["levels"]:
            label = spec["label"].format(level=f"{level:,}", resource=resource)
            row.appendChild(_doctrine_pill(label[0].upper() + label[1:],
                                           {"data-action": "draft-cond", "data-value": f"{cond}:{level}"},
                                           _doctrine_draft["cond"] == cond and _doctrine_draft["level"] == level))
    panel.appendChild(row)
    row = document.createElement("div")
    row.className = "overview-actions"
    row.appendChild(_make_text("overview-actions-label", "Then:", "span"))
    for key, text in DOCTRINE_ACTIONS.items():
        row.appendChild(_doctrine_pill(text[0].upper() + text[1:], {"data-action": "draft-action", "data-value": key},
                                       _doctrine_draft["action"] == key))
    panel.appendChild(row)
    panel.appendChild(_make_text("chain-card-detail", "Preview: " + doctrine_rule_text(_doctrine_draft)))
    actions = document.createElement("div")
    actions.className = "overview-actions"
    actions.appendChild(_make_button("Add rule", {"data-action": "add"}, None,
                                     disabled=len(doctrine_rules) >= doctrine_rule_limit()))
    actions.appendChild(_make_button(f"Try for {DRY_RUN_TICKS} ticks", {"data-action": "dry-run"},
                                     "Runs your rules on a copy of the numbers and says how often each would fire. Nothing real changes."))
    panel.appendChild(actions)
    if runstate._doctrine_dry_text:
        dry = _make_text("chain-card-count", runstate._doctrine_dry_text)
        dry.setAttribute("role", "status")
        panel.appendChild(dry)


def update_doctrine_display():
    toggle = document.getElementById("doctrine-toggle-button")
    panel = document.getElementById("doctrine-panel")
    toggle.hidden = not doctrines_unlocked()
    toggle.innerText = "Hide Doctrines" if runstate.doctrine_open else f"\U0001f4d0 Doctrines ({len(doctrine_rules)}/{doctrine_rule_limit()})"
    panel.hidden = not (runstate.doctrine_open and doctrines_unlocked())
    if panel.hidden:
        runstate._doctrine_signature = None
        return
    signature = _doctrine_structure_signature()
    if signature != runstate._doctrine_signature:
        _build_doctrine_panel()
        runstate._doctrine_signature = signature
    for index, element in _doctrine_refs.items():
        n = runstate._doctrine_fired_counts.get(index, 0)
        element.innerText = f"Fired {n} time{'s' if n != 1 else ''} this session"


# --- A-27 / A-28: Ecology Stress Test ------------------------------------------
# An optional endgame arena, open once every world is terraformed. It runs on a
# copy of your numbers (nothing real changes, no achievements or boards are
# touched): for three minutes of game time a cascade of anomalies hits every world
# (decay x1.5, then x2 with trade restore halved, then x2.5), nobody is standing
# anywhere, and only your Governor settings and Doctrines act. The line is an
# average ecology of STRESS_LINE% across all eight worlds; the score is how far
# above the line the worst moment stayed (negative = it dipped under). A-28: a
# strip per world of 12 blocks (the lowest ecology in each 15 seconds), height
# plus "!" under 10% and "x" at 0%, so it reads without colour.
STRESS_TICKS = 1800
STRESS_SAMPLE_EVERY = 150
STRESS_LINE = 40.0
STRESS_PHASES = [(0, {"decay": 1.5}), (600, {"decay": 2.0, "trade": 0.5}), (1200, {"decay": 2.5, "trade": 0.5})]
STRESS_BLOCKS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


def stress_block(ecology):
    if ecology <= 0:
        return "x"
    if ecology < LOW_ECOLOGY_THRESHOLD:
        return "!"
    return STRESS_BLOCKS[min(len(STRESS_BLOCKS) - 1, int(ecology / (ECOLOGY_MAX / len(STRESS_BLOCKS))))]


def run_stress_test():
    """Runs the test. Returns the result dict, or None when the system is not fully terraformed yet."""
    if not _prestige_available():
        return None
    buckets = STRESS_TICKS // STRESS_SAMPLE_EVERY
    lows = {p: [100.0] * buckets for p in PLANETS}
    worst = [100.0]

    def sample(index):
        for phase_start, factors in STRESS_PHASES:
            if index >= phase_start:
                _stress_factors.clear()
                _stress_factors.update(factors)
        bucket = min(buckets - 1, index // STRESS_SAMPLE_EVERY)
        total = 0.0
        for planet in PLANETS:
            ecology = planet_state[planet]["ecology_health"]
            total += ecology
            lows[planet][bucket] = min(lows[planet][bucket], ecology)
        worst[0] = min(worst[0], total / len(PLANETS))

    _stress_factors.update(STRESS_PHASES[0][1])
    _run_headless(STRESS_TICKS, on_tick=sample, all_governed=True)
    margin = round(worst[0] - STRESS_LINE, 1)
    runstate._stress_last = {"margin": margin, "lowest": round(worst[0], 1), "rows": lows}
    if runstate.stress_best_margin is None or margin > runstate.stress_best_margin:
        runstate.stress_best_margin = margin
    runstate._stress_run_id += 1
    return runstate._stress_last


def _build_stress_section(panel):
    panel.appendChild(_make_text("stats-panel-heading", "Ecology Stress Test"))
    panel.appendChild(_make_text(
        "chains-intro",
        f"An optional endgame arena. For {STRESS_TICKS * TICK_INTERVAL_MS // 60000} minutes of game time a cascade of "
        "anomalies hits every world and only your Governor settings and Doctrines act: no clicking. The line is an "
        f"average ecology of {round(STRESS_LINE)}% across all worlds. It runs on a copy, so nothing in your game "
        "changes."))
    if runstate.stress_best_margin is not None:
        panel.appendChild(_make_text("chain-card-count", f"Best so far: {runstate.stress_best_margin:+.1f} points from the line."))
    ready = _prestige_available()
    panel.appendChild(_make_button("Run the stress test" if ready else "Opens when every world is terraformed",
                                   {"data-action": "stress"}, None, disabled=not ready))
    if runstate._stress_last is None:
        return
    verdict = "held the line" if runstate._stress_last["margin"] >= 0 else "dipped under the line"
    result = _make_text(
        "chain-card-count",
        f"Result: {verdict}. Worst average ecology {runstate._stress_last['lowest']}%, which is "
        f"{runstate._stress_last['margin']:+.1f} points from the line.")
    result.setAttribute("role", "status")
    panel.appendChild(result)
    panel.appendChild(_make_text(
        "chain-card-detail",
        "Each block is the lowest ecology in 15 seconds: taller is healthier, ! is under 10% (output penalty), x is 0%."))
    for planet in PLANETS:
        values = runstate._stress_last["rows"][planet]
        strip = "".join(stress_block(v) for v in values)
        panel.appendChild(_make_text(
            "stress-strip", f"{PLANET_DISPLAY_NAMES.get(planet, planet)}: {strip} lowest {round(min(values))}%"))


# --- A-23: Blueprint Swap ------------------------------------------------------
# One short text code holds a build plan (the step texts, never the ticks), the
# Doctrine rules and the mutator picks. Importing never changes anything by
# itself: the code shows up as a faint "ghost" list under the Build Plan, and each
# part is adopted with its own button (steps are added to the end of your plan,
# rules only up to your limit, mutator picks replace the picks for the next run).
# Local only: no backend, nothing is saved, the ghost is gone on reload.
BLUEPRINT_PREFIX = "SOLPLAN1:"
_ghost = {"steps": [], "rules": [], "mutators": []}


def blueprint_code():
    payload = {
        "p": [step["text"] for step in build_plan],
        "d": [dict(rule) for rule in doctrine_rules],
        "m": list(mutators_next),
    }
    return export_progress.encode_progress_code(payload, prefix=BLUEPRINT_PREFIX)


def parse_blueprint(code):
    """Returns (True, {"steps", "rules", "mutators"}) or (False, message). Never raises."""
    ok, payload = export_progress.decode_progress_code(
        (code or "").strip(), prefix=BLUEPRINT_PREFIX, bad_format_message="That does not look like a SOL blueprint code.")
    if not ok:
        return False, payload
    steps = []
    raw_steps = payload.get("p")
    if isinstance(raw_steps, list):
        for text in raw_steps[:BUILD_PLAN_MAX_STEPS]:
            if isinstance(text, str) and text.strip():
                steps.append(text.strip()[:BUILD_PLAN_MAX_LEN])
    rules = _clean_doctrine_rules(payload.get("d"))
    mutators = _clean_mutators(payload.get("m"))
    if not (steps or rules or mutators):
        return False, "That blueprint is empty."
    return True, {"steps": steps, "rules": rules, "mutators": mutators}


def _blueprint_status(text):
    document.getElementById("blueprint-status").innerText = text


def update_blueprint_ghost():
    box = document.getElementById("blueprint-ghost")
    box.innerHTML = ""
    if not (_ghost["steps"] or _ghost["rules"] or _ghost["mutators"]):
        box.hidden = True
        return
    box.hidden = False
    box.appendChild(_make_text("stats-panel-heading", "Ghost blueprint (not part of your game yet)"))
    mine = {step["text"] for step in build_plan}
    for index, text in enumerate(_ghost["steps"]):
        row = document.createElement("div")
        row.className = "build-plan-row build-plan-row--ghost"
        row.appendChild(_make_text("build-plan-text", ("\u2713 " if text in mine else "\u25cb ") + text, "span"))
        if text not in mine:
            row.appendChild(_make_button("Add to my plan", {"data-action": "add-step", "data-step": str(index)}, None))
        box.appendChild(row)
    if _ghost["steps"]:
        box.appendChild(_make_button("Add every step", {"data-action": "add-all"}, None))
    for rule in _ghost["rules"]:
        box.appendChild(_make_text("build-plan-text", "Rule: " + doctrine_rule_text(rule)))
    if _ghost["rules"]:
        box.appendChild(_make_button("Add these rules to my Doctrines", {"data-action": "adopt-rules"}, None))
    if _ghost["mutators"]:
        names = ", ".join(MUTATOR_BY_ID[m_id]["label"] for m_id in _ghost["mutators"])
        box.appendChild(_make_text("build-plan-text", f"Mutator picks: {names}"))
        box.appendChild(_make_button("Use these mutator picks", {"data-action": "use-mutators"}, None))
    box.appendChild(_make_button("Clear the ghost", {"data-action": "clear"}, None))
