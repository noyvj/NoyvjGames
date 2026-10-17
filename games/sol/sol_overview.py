"""The multi-planet overview dashboard."""

import math

from js import document

import sol_runstate as runstate
from sol_charter import MEGAPROJECTS, STAMP_STAR, _ring, megaproject_percent, stamps_for
from sol_codex import WORLD_NOTES
from sol_econ import production_multiplier
from sol_observatory import rival_pressure
from sol_rules import (
    GAS_GIANT_BODIES, GOVERNOR_PERSONALITY_LABELS, GOVERNOR_PERSONALITY_TIPS, PLANETS, PLANET_DISPLAY_NAMES,
    SPECIALIZATION_LABELS, SPECIALIZATION_TIPS, _specialization, planet_state, specialization_eligible,
)
from sol_util import _make_button, _make_text, _overview_planets


# --- A9: multi-planet overview dashboard (+ A7 personalities, A23 specializations) ---
_overview_refs = {}


def _overview_structure_signature():
    return (
        runstate.current_planet,
        tuple(
            (
                p,
                planet_state[p].get("governor_personality", "default"),
                planet_state[p].get("specialization"),
                specialization_eligible(p),
            )
            for p in _overview_planets()
        ),
    )


def _build_overview():
    panel = document.getElementById("overview-panel")
    panel.innerHTML = ""
    _overview_refs.clear()

    summary = _make_text("overview-summary", "")
    panel.appendChild(summary)
    _overview_refs["_summary"] = summary
    panel.appendChild(_make_text(
        "overview-card-note",
        "Field notes: a few worlds end their note with an odd sentence. Somebody should try doing what it says."))
    # A-14: one progress ring per megaproject, so the whole system's effort shows at a glance.
    rings = document.createElement("div")
    rings.className = "overview-rings"
    rings.setAttribute("aria-label", "Megaproject progress")
    _overview_refs["_rings"] = {}
    for project in MEGAPROJECTS:
        cell = document.createElement("span")
        cell.className = "overview-ring-cell"
        ring = _ring(megaproject_percent(project["id"]))
        cell.appendChild(ring)
        cell.appendChild(_make_text("overview-ring-name", project["label"], "span"))
        rings.appendChild(cell)
        _overview_refs["_rings"][project["id"]] = ring
    panel.appendChild(rings)

    for planet in _overview_planets():
        state = planet_state[planet]
        card = document.createElement("div")
        card.className = "overview-card" + (" overview-card--current" if planet == runstate.current_planet else "")

        title = _make_text(
            "overview-card-title",
            PLANET_DISPLAY_NAMES.get(planet, planet) + (" (you are here)" if planet == runstate.current_planet else ""),
        )
        card.appendChild(title)
        if planet in WORLD_NOTES:
            card.appendChild(_make_text("overview-card-note", WORLD_NOTES[planet]))
        stats = _make_text("overview-card-stats", "")
        card.appendChild(stats)

        eco_row = document.createElement("div")
        eco_row.className = "overview-bar-row"
        eco_label = _make_text("overview-bar-label", "Ecology", "span")
        eco_meter = document.createElement("div")
        eco_meter.className = "meter overview-meter"
        eco_fill = document.createElement("div")
        eco_fill.className = "meter-fill"
        eco_meter.appendChild(eco_fill)
        eco_row.appendChild(eco_label)
        eco_row.appendChild(eco_meter)
        card.appendChild(eco_row)

        tf_row = document.createElement("div")
        tf_row.className = "overview-bar-row"
        tf_label = _make_text("overview-bar-label", "Terraform", "span")
        tf_meter = document.createElement("div")
        tf_meter.className = "meter overview-meter"
        tf_fill = document.createElement("div")
        tf_fill.className = "meter-fill terraform-fill"
        tf_meter.appendChild(tf_fill)
        tf_row.appendChild(tf_label)
        tf_row.appendChild(tf_meter)
        card.appendChild(tf_row)

        extras = _make_text("overview-card-extras", "")
        card.appendChild(extras)

        actions = document.createElement("div")
        actions.className = "overview-actions"
        if planet != runstate.current_planet:
            actions.appendChild(
                _make_button("Travel here", {"data-action": "travel", "data-planet": planet},
                             "Fly to this world without going back through Earth.")
            )
        card.appendChild(actions)

        personality_row = document.createElement("div")
        personality_row.className = "overview-actions"
        personality_row.appendChild(_make_text("overview-actions-label", "Governor:", "span"))
        current_personality = state.get("governor_personality", "default")
        for key, label in GOVERNOR_PERSONALITY_LABELS.items():
            personality_row.appendChild(
                _make_button(label, {"data-action": "personality", "data-planet": planet, "data-value": key},
                             GOVERNOR_PERSONALITY_TIPS[key], selected=(key == current_personality))
            )
        card.appendChild(personality_row)

        if specialization_eligible(planet):
            spec_row = document.createElement("div")
            spec_row.className = "overview-actions"
            spec_row.appendChild(_make_text("overview-actions-label", "Focus:", "span"))
            for key, label in SPECIALIZATION_LABELS.items():
                spec_row.appendChild(
                    _make_button(label, {"data-action": "specialize", "data-planet": planet, "data-value": key},
                                 SPECIALIZATION_TIPS[key], selected=(state.get("specialization") == key))
                )
            card.appendChild(spec_row)

        panel.appendChild(card)
        _overview_refs[planet] = {"stats": stats, "eco": eco_fill, "tf": tf_fill, "extras": extras}


def _refresh_overview_values():
    planets = _overview_planets()
    summary = _overview_refs.get("_summary")
    if summary is not None:
        avg_tf = sum(planet_state[p]["terraform_progress"] for p in planets) / len(planets)
        gens = sum(planet_state[p]["generator_count"] for p in planets)
        summary.innerText = (
            f"{len(planets)}/{len(PLANETS)} worlds unlocked · {gens} generators total · "
            f"average terraforming {round(avg_tf)}%"
        )
    for pid, ring in _overview_refs.get("_rings", {}).items():
        percent = megaproject_percent(pid)
        ring.style.background = (
            f"conic-gradient(var(--mega-ring-fill, #6fb3ff) {percent * 3.6}deg, var(--mega-ring-rest, #2a3350) 0)")
        ring.innerText = f"{round(percent)}%"
        ring.setAttribute("aria-label", f"{round(percent)} percent built")
    for planet in planets:
        refs = _overview_refs.get(planet)
        if refs is None:
            continue
        state = planet_state[planet]
        cfg = PLANETS[planet]
        refs["stats"].innerText = (
            f"{cfg['resource_name']}: {math.floor(state['resource_count'] + 1e-9)} · "
            f"{state['generator_count']} generators · {state['recycler_count']} Recyclers"
        )
        refs["eco"].style.width = f"{state['ecology_health']}%"
        refs["tf"].style.width = f"{state['terraform_progress']}%"
        routes = sum(state["trade_routes"].values())
        bits = [
            f"Ecology {round(state['ecology_health'])}%",
            f"Terraform {round(state['terraform_progress'])}%",
            f"Output {round(production_multiplier(planet) * 100)}%",
            f"{routes} trade route(s)",
        ]
        if planet in GAS_GIANT_BODIES:
            bits.append(f"{state.get('sky_city_count', 0)} Sky City(ies)")
        spec = _specialization(planet)
        if spec:
            bits.append(f"Focus: {SPECIALIZATION_LABELS[spec]}")
        pressure = rival_pressure(planet)
        if pressure:
            bits.append(f"Rival pressure: trade restores {round(pressure * 100)}% less (a Focus shields this world)")
        stamps = stamps_for(planet)
        if stamps:
            bits.append(f"Charter stamps: {STAMP_STAR * stamps} (+{stamps}% yield)")
        refs["extras"].innerText = " · ".join(bits)


def update_overview_display():
    toggle = document.getElementById("overview-toggle-button")
    panel = document.getElementById("overview-panel")
    toggle.innerText = "Hide Overview" if runstate.overview_open else "🌍 Overview"
    panel.hidden = not runstate.overview_open
    if not runstate.overview_open:
        runstate._overview_signature = None
        return
    signature = _overview_structure_signature()
    if signature != runstate._overview_signature:
        _build_overview()
        runstate._overview_signature = signature
    _refresh_overview_values()
