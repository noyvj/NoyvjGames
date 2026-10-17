"""Build-order planner, the prestige tree, the epilogue and win display, sandbox and close-call tracking."""

from js import document

import sol_runstate as runstate
from sol_achievements import achievement_ids_earned
from sol_econ import (
    update_ecology_display, update_generator_display, update_research_display, update_sky_city_display,
    update_trade_display,
)
from sol_rules import (
    BUILD_PLAN_MAX_LEN, BUILD_PLAN_MAX_STEPS, GAS_GIANT_BODIES, PLANETS, PRESTIGE_BONUS_PER_LEVEL,
    PRESTIGE_TIER_LABELS, PRESTIGE_TREE, TERRAFORM_MAX, _prestige_available, build_plan, planet_state,
    prestige_points_available,
)
from sol_runmods import _apply_era, _build_mutator_cards, era_for_level, mutator_glyphs, mutator_rules_text
from sol_statsview import _lifetime_playtime_seconds
from sol_story import ACHIEVEMENTS
from sol_util import _dom_id, _format_duration, _make_button, _make_text


def update_win_display():
    # Milestone 11: the win condition is recomputed fresh every call rather
    # than tracked with a separate "achieved" flag -- simpler than keeping a
    # flag in sync, and necessary now that terraform_progress CAN regress
    # again: A18's "reset this world" and A1's prestige both zero a
    # planet's terraform_progress back out on purpose. The banner is a
    # sibling of every per-planet view in the HTML (not inside any of
    # them), so it stays visible regardless of current_planet and isn't
    # touched by _hide_all_views().
    complete = runstate._scarcity is None and all(planet_state[p]["terraform_progress"] >= TERRAFORM_MAX for p in PLANETS)
    document.getElementById("win-banner").hidden = not complete

    readout = document.getElementById("prestige-level-readout")
    if runstate.prestige_level > 0:
        readout.innerText = (
            f"Prestige Level {runstate.prestige_level} — "
            f"+{round(PRESTIGE_BONUS_PER_LEVEL * runstate.prestige_level * 100)}% resource yield"
        )
    else:
        readout.innerText = "Prestige into a New Game+ for a permanent resource bonus."

    # A2: prestige badge next to the title. A24: the exact bonus next to each
    # world's resource label, where the gains actually show up.
    badge = document.getElementById("prestige-badge")
    badge.hidden = runstate.prestige_level <= 0
    badge.innerText = (
        f"{era_for_level(runstate.prestige_level)['label']} \u00b7 Prestige {runstate.prestige_level}{mutator_glyphs(runstate.mutators_run)}"
        if runstate.prestige_level > 0 else ""
    )
    _apply_era()
    badge.title = ("Your current Prestige level" + mutator_rules_text(runstate.mutators_run)) if runstate.prestige_level > 0 else ""
    bonus_text = f"+{round(PRESTIGE_BONUS_PER_LEVEL * runstate.prestige_level * 100)}% Prestige bonus on yields"
    for planet in PLANETS:
        tag = document.getElementById(_dom_id(planet, "prestige-bonus"))
        tag.hidden = runstate.prestige_level <= 0
        tag.innerText = bonus_text if runstate.prestige_level > 0 else ""

    sandbox_button = document.getElementById("sandbox-toggle-button")
    sandbox_button.hidden = not complete
    sandbox_button.innerText = "🧪 Sandbox: On" if runstate.sandbox_mode else "🧪 Sandbox: Off"
    document.getElementById("epilogue-button").hidden = not complete
    update_prestige_tree_display(rebuild=False)


# --- A13: build-order planner ---


def _add_build_step(text):
    text = str(text).strip()[:BUILD_PLAN_MAX_LEN]
    if not text or len(build_plan) >= BUILD_PLAN_MAX_STEPS:
        return False
    build_plan.append({"text": text, "done": False})
    return True


def build_plan_tsv():
    """A-24: the plan as tab-separated rows (step number, text, done) that
    paste straight into a spreadsheet; tabs and line breaks inside a step are
    flattened to spaces so every step stays on its own row."""
    rows = ["Step\tWhat\tDone"]
    for number, step in enumerate(build_plan, start=1):
        text = " ".join(step["text"].replace("\t", " ").split())
        rows.append(f"{number}\t{text}\t{'yes' if step['done'] else 'no'}")
    return "\n".join(rows)


def update_build_plan_display():
    toggle = document.getElementById("build-plan-toggle-button")
    panel = document.getElementById("build-plan-panel")
    done = sum(1 for step in build_plan if step["done"])
    label = f"📝 Build Plan ({done}/{len(build_plan)})" if build_plan else "📝 Build Plan"
    toggle.innerText = "Hide Build Plan" if runstate.build_plan_open else label
    panel.hidden = not runstate.build_plan_open
    if not runstate.build_plan_open:
        return
    listing = document.getElementById("build-plan-list")
    listing.innerHTML = ""
    if not build_plan:
        listing.appendChild(_make_text("build-plan-empty", "No steps yet. Add your own, or start from the suggested opening."))
    for index, step in enumerate(build_plan):
        row = document.createElement("div")
        row.className = "build-plan-row" + (" build-plan-row--done" if step["done"] else "")
        row.appendChild(
            _make_button("☑" if step["done"] else "☐", {"data-action": "toggle", "data-step": str(index)},
                         "Tick this step off")
        )
        row.appendChild(_make_text("build-plan-text", step["text"], "span"))
        row.appendChild(
            _make_button("✕", {"data-action": "remove", "data-step": str(index)}, "Remove this step")
        )
        listing.appendChild(row)


# --- A1 / A3: prestige tree panel ---


def _node_unlockable(node):
    return (
        node["id"] not in runstate.prestige_nodes
        and runstate.prestige_level >= node["min_level"]
        and prestige_points_available() >= node["cost"]
    )


def update_prestige_tree_display(rebuild=True):
    toggle = document.getElementById("prestige-tree-toggle-button")
    panel = document.getElementById("prestige-tree-panel")
    # A-3: the mutator picks are made here, so the panel is also open to a player who is about to prestige.
    toggle.hidden = runstate.prestige_level <= 0 and not _prestige_available()
    available = prestige_points_available()
    toggle.innerText = "Hide Prestige Tree" if runstate.prestige_tree_open else f"🌳 Prestige Tree ({available})"
    panel.hidden = not (runstate.prestige_tree_open and not toggle.hidden)
    if panel.hidden or not rebuild:
        return
    panel.innerHTML = ""
    panel.appendChild(
        _make_text(
            "prestige-tree-points",
            f"Prestige Points: {available} available ({runstate.prestige_points_earned} earned). "
            "Each prestige earns 1; unlocks are permanent and survive every prestige.",
        )
    )
    _build_mutator_cards(panel)
    for tier in (1, 2, 3):
        panel.appendChild(_make_text("stats-panel-heading", PRESTIGE_TIER_LABELS[tier]))
        for node in [n for n in PRESTIGE_TREE if n["tier"] == tier]:
            unlocked = node["id"] in runstate.prestige_nodes
            card = document.createElement("div")
            card.className = "prestige-node" + (" prestige-node--unlocked" if unlocked else "")
            card.appendChild(_make_text("prestige-node-name", f"{node['label']} ({node['cost']} pt)"))
            card.appendChild(_make_text("prestige-node-desc", node["desc"]))
            if unlocked:
                card.appendChild(_make_text("prestige-node-status", "Unlocked"))
                if node["id"] == "ng_challenge":
                    card.appendChild(
                        _make_button(
                            "Challenge: On" if runstate.ng_challenge_active else "Challenge: Off",
                            {"data-action": "challenge"},
                            "Applies at the moment you next Prestige, and to the run after it.",
                            selected=runstate.ng_challenge_active,
                        )
                    )
            elif runstate.prestige_level < node["min_level"]:
                card.appendChild(
                    _make_text("prestige-node-status", f"Locked: reach Prestige Level {node['min_level']}")
                )
            else:
                card.appendChild(
                    _make_button(f"Unlock ({node['cost']} pt)", {"data-action": "unlock", "data-node": node["id"]},
                                 None, disabled=not _node_unlockable(node))
                )
            panel.appendChild(card)


def _refresh_all_cost_displays():
    for planet in PLANETS:
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        if planet in GAS_GIANT_BODIES:
            update_sky_city_display(planet)
    update_research_display()


# --- A15: sandbox mode + A27: epilogue ---


def update_epilogue_display():
    panel = document.getElementById("epilogue-panel")
    panel.hidden = not (runstate.epilogue_open and _prestige_available())
    if panel.hidden:
        return
    body = document.getElementById("epilogue-body")
    body.innerHTML = ""
    paragraphs = [
        "The last survey drones report in. On every world you touched, the air holds, the water runs, "
        "and the ledgers finally balance against the ground they were drawn from.",
        f"It took {_format_duration(_lifetime_playtime_seconds())} of simulated time, "
        f"{runstate.total_manual_clicks} hand-mined loads, and {runstate.lifetime_generators_built} machines that never tired.",
        f"{len(runstate.visited_bodies)} of {len(PLANETS)} worlds saw your boots, and {len(achievement_ids_earned())} of "
        f"{len(ACHIEVEMENTS)} milestones are in the log.",
        "Nothing here has to end. The sandbox stays open, and a New Game+ waits for anyone who wants to do it "
        "all again a little better.",
    ]
    if runstate.prestige_level > 0:
        paragraphs.insert(3, f"You have started over {runstate.prestige_level} time(s) already, and each run left the system tidier.")
    if runstate.megaprojects_all_ever:
        paragraphs.insert(1, (
            "And above it all hang the four great works: the Orbital Mirror, the Ring Habitat, the Dyson Sail "
            "and the Deep Core Tap, built with something from every world. Seen from Pluto, the inner system "
            "is one slow, patient light."))
    for text in paragraphs:
        body.appendChild(_make_text("epilogue-paragraph", text))
