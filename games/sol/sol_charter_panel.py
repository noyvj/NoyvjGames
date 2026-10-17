"""The Mission Board and Megaproject panels."""

import math

from js import document

import sol_runstate as runstate
from sol_charter import (
    MEGAPROJECTS, MISSIONS, MISSION_BY_ID, MISSION_REROLL_COST, MISSION_SLOTS, STAMP_STAR, _charter_refs,
    _mission_candidates, _mission_label_world, _ring, megaproject_percent, megaproject_progress,
    megaproject_sent, mission_progress, mission_slots, mission_stamps, reroll_source, stamps_for,
)
from sol_codex import _build_codex_section, _codex_hints, _world_available, codex_found
from sol_headless import _build_stress_section
from sol_rules import PLANETS, PLANET_DISPLAY_NAMES, _prestige_available, planet_state
from sol_runmods import ANOMALIES, ANOMALY_BY_ID, anomalies_seen, megaprojects_built
from sol_util import _make_button, _make_text, _overview_planets


def _charter_structure_signature():
    return (tuple(mission_slots), tuple(mission_stamps), tuple(sorted(anomalies_seen)),
            tuple(_overview_planets()), tuple(megaprojects_built), tuple(codex_found), tuple(sorted(_codex_hints)),
            runstate._stress_run_id, runstate.stress_best_margin, _prestige_available(),
            tuple((pid, tuple(sorted(v.items()))) for pid, v in sorted(megaproject_progress.items())))


def _build_charter():
    panel = document.getElementById("charter-panel")
    panel.innerHTML = ""
    _charter_refs.clear()
    panel.appendChild(_make_text("stats-panel-heading", "Charter"))
    panel.appendChild(_make_text(
        "chains-intro",
        "Optional objectives. Finish a mission and the Charter is stamped for good: a small permanent yield "
        "bonus on that world, shown on its Overview card. Nothing here is timed or random.",
    ))
    panel.appendChild(_make_text("stats-panel-heading", "Mission Board"))
    for m_id in mission_slots:
        mission = MISSION_BY_ID[m_id]
        card = document.createElement("div")
        card.className = "chain-card"
        card.appendChild(_make_text("chain-card-name", f"{mission['label']}"))
        card.appendChild(_make_text("chain-card-detail", f"World: {_mission_label_world(mission)}"))
        meter = document.createElement("div")
        meter.className = "meter overview-meter"
        fill = document.createElement("div")
        fill.className = "meter-fill"
        meter.appendChild(fill)
        card.appendChild(meter)
        text = _make_text("chain-card-count", "")
        card.appendChild(text)
        reroll = _make_button("Swap for another mission", {"data-action": "reroll", "data-mission": m_id}, None)
        card.appendChild(reroll)
        panel.appendChild(card)
        _charter_refs[m_id] = {"fill": fill, "text": text, "reroll": reroll}
    if len(mission_slots) < MISSION_SLOTS:
        panel.appendChild(_make_text(
            "chains-intro", "More missions are posted as you unlock worlds and finish these."))
    _build_megaproject_section(panel)
    _build_codex_section(panel)
    _build_stress_section(panel)
    _charter_refs["_stamps"] = _make_text("chain-card-count", "")
    panel.appendChild(_make_text("stats-panel-heading", "Stamps"))
    panel.appendChild(_charter_refs["_stamps"])
    panel.appendChild(_make_text("stats-panel-heading", "Anomalies seen"))
    names = [ANOMALY_BY_ID[a]["label"] if a in anomalies_seen else "?" for a in (e["id"] for e in ANOMALIES)]
    panel.appendChild(_make_text(
        "chain-card-detail", f"{len(anomalies_seen)} of {len(ANOMALIES)}: " + ", ".join(names)))


def _refresh_charter_values():
    for m_id in mission_slots:
        refs = _charter_refs.get(m_id)
        if refs is None:
            continue
        mission = MISSION_BY_ID[m_id]
        current = mission_progress(mission)
        pct = 100.0 * current / mission["target"]
        refs["fill"].style.width = f"{pct}%"
        shown = math.floor(current + 1e-9) if mission["target"] >= 100 else round(current)
        refs["text"].innerText = f"{shown} of {mission['target']}"
        source = reroll_source()
        refs["reroll"].disabled = source is None or not _mission_candidates()
        refs["reroll"].innerText = (
            f"Swap for another mission ({source[1]} {PLANETS[source[0]]['resource_name']})" if source
            else f"Swap for another mission (needs {MISSION_REROLL_COST} of any resource)"
        )
    _refresh_megaproject_values()
    stamps = _charter_refs.get("_stamps")
    if stamps is not None:
        per_world = [f"{PLANET_DISPLAY_NAMES.get(p, p)} {STAMP_STAR * stamps_for(p)}" for p in PLANETS if stamps_for(p)]
        if stamps_for("all"):
            per_world.append("System " + STAMP_STAR * stamps_for("all"))
        stamps.innerText = f"{len(mission_stamps)} of {len(MISSIONS)} stamps" + (
            ": " + ", ".join(per_world) if per_world else ". Finish a mission to earn the first.")


def update_charter_display():
    toggle = document.getElementById("charter-toggle-button")
    panel = document.getElementById("charter-panel")
    count = f" ({len(mission_stamps)}/{len(MISSIONS)})"
    toggle.innerText = ("Hide Charter" if runstate.charter_open else "\U0001f4dc Charter") + count
    panel.hidden = not runstate.charter_open
    if not runstate.charter_open:
        runstate._charter_signature = None
        return
    signature = _charter_structure_signature()
    if signature != runstate._charter_signature:
        _build_charter()
        runstate._charter_signature = signature
    _refresh_charter_values()


def _build_megaproject_section(panel):
    panel.appendChild(_make_text("stats-panel-heading", f"Megaprojects ({len(megaprojects_built)}/{len(MEGAPROJECTS)} built this run)"))
    panel.appendChild(_make_text(
        "chains-intro",
        "Each work needs resources from several worlds at once. Send what a world has banked and the ring fills; "
        "a finished work keeps its perk for the rest of the run. Build all four for a secret ending line.",
    ))
    for project in MEGAPROJECTS:
        pid = project["id"]
        built = pid in megaprojects_built
        card = document.createElement("div")
        card.className = "chain-card chain-card--found" if built else "chain-card"
        head = document.createElement("div")
        head.className = "mega-head"
        ring = _ring(megaproject_percent(pid))
        head.appendChild(ring)
        title = document.createElement("div")
        title.appendChild(_make_text("chain-card-name", project["label"] + (" (built)" if built else "")))
        title.appendChild(_make_text("chain-card-detail", "Perk: " + project["perk"]))
        head.appendChild(title)
        card.appendChild(head)
        refs = {"ring": ring, "lines": {}}
        if not built:
            for planet, amount in project["needs"]:
                row = document.createElement("div")
                row.className = "mega-line"
                text = _make_text("chain-card-count", "")
                row.appendChild(text)
                button = _make_button("Send what you can",
                                      {"data-action": "send", "data-project": pid, "data-planet": planet}, None)
                row.appendChild(button)
                card.appendChild(row)
                refs["lines"][planet] = (text, button)
        panel.appendChild(card)
        _charter_refs["mega:" + pid] = refs


def _refresh_megaproject_values():
    for project in MEGAPROJECTS:
        pid = project["id"]
        refs = _charter_refs.get("mega:" + pid)
        if refs is None:
            continue
        percent = megaproject_percent(pid)
        refs["ring"].style.background = (
            f"conic-gradient(var(--mega-ring-fill, #6fb3ff) {percent * 3.6}deg, var(--mega-ring-rest, #2a3350) 0)")
        refs["ring"].innerText = f"{round(percent)}%"
        refs["ring"].setAttribute("aria-label", f"{round(percent)} percent built")
        for planet, amount in project["needs"]:
            line = refs["lines"].get(planet)
            if line is None:
                continue
            text, button = line
            name = PLANET_DISPLAY_NAMES.get(planet, planet)
            sent = megaproject_sent(pid, planet)
            resource = PLANETS[planet]["resource_name"]
            if _world_available(planet):
                banked = math.floor(planet_state[planet]["resource_count"] + 1e-9)
                text.innerText = f"{resource} from {name}: {math.floor(sent)} of {amount} sent ({banked} banked)"
                button.disabled = banked < 1 or sent >= amount
            else:
                text.innerText = f"{resource} from {name}: {math.floor(sent)} of {amount} sent (reach {name} first)"
                button.disabled = True
