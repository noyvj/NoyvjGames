"""The invest step size, the event codex and the lifetime statistics panel."""

from js import document, localStorage

import aftermath_runstate as runstate
from aftermath_bonuses import growth_button_label
from aftermath_panels import REAL_WORLD_EXAMPLES, REAL_WORLD_READ_DATE
from aftermath_pastruns import CATEGORY_ICON
from aftermath_persist import _storage_write, run_log_history
from aftermath_rules import (
    DEFAULT_SCENARIO, EVENT_CATEGORY, EVENT_ICON, EVENT_LABEL, RESILIENCE_COST, SCENARIOS, entry_mitigation,
    flawless_count,
)


# ===========================================================================
# Round-3 additions (planning/TODO.md "GE + E. Aftermath", 2026-10-07):
# E-12 Disaster Codex, E-1 lifetime statistics, E-15 x1/x5/Max steps,
# GE-18 undo, GE-15 Flawless Defense (rules live in RunState above),
# GE-13 prevented-damage popup, E-23 knowledge itemisation, E-24 copy run
# summary, E-27 live tab title, E-5 (partial) aria-live announcements.
# None of this changes a rule that existed before except the Flawless
# Defense bonus point.
# ===========================================================================

# ---- E-15: invest step size (x1 / x5 / Max), remembered per browser -------
INVEST_STEP_STORAGE_KEY = "aftermath-invest-step"
INVEST_STEPS = (1, 5, "max")


def load_invest_step():
    raw = localStorage.getItem(INVEST_STEP_STORAGE_KEY)
    if raw == "max":
        return "max"
    if raw in ("1", "5"):
        return int(raw)
    return 1


runstate.invest_step = load_invest_step()


def set_invest_step(value):
    if value not in INVEST_STEPS:
        return False
    runstate.invest_step = value
    _storage_write(INVEST_STEP_STORAGE_KEY, str(value))
    return True


def step_label(step):
    return "Max" if step == "max" else f"x{step}"


def resilience_button_label(run_state, step):
    units = run_state.step_units("resilience", step)
    if step == 1 or units < 1:
        return f"Invest in Resilience ({RESILIENCE_COST})"
    return f"Invest in Resilience x{units} ({RESILIENCE_COST * units})"


def growth_step_label(run_state, step):
    units = run_state.step_units("growth", step)
    if step == 1 or units < 1:
        return growth_button_label(run_state.growth_capacity)
    return growth_button_label(run_state.growth_capacity, units)


# ---- E-12 / E-1: records across every run -------------------------------
def lifetime_event_records():
    """Every event faced that a log remembers: all completed runs'
    event_logs plus the run in progress (a finished run is already in
    run_log_history once it pays out)."""
    records = []
    for entry in run_log_history:
        if not isinstance(entry, dict):
            continue
        for event in entry.get("event_log", []) or []:
            if isinstance(event, dict) and event.get("type") in EVENT_LABEL:
                records.append(event)
    if not runstate.run.is_complete():
        records.extend(e for e in runstate.run.event_log if e.get("type") in EVENT_LABEL)
    return records


def codex_entries():
    """E-12: one row per event type, in EVENT_LABEL order."""
    records = lifetime_event_records()
    in_progress = {}
    if not runstate.run.is_complete():
        for event in runstate.run.event_log:
            in_progress[event["type"]] = in_progress.get(event["type"], 0) + 1
    rows = []
    for event_type in EVENT_LABEL:
        mine = [e for e in records if e["type"] == event_type]
        faced = max(
            len(mine),
            int(runstate.legacy_event_counts.get(event_type, 0)) + in_progress.get(event_type, 0),
        )
        if faced == 0 and event_type in runstate.legacy_events:
            faced = 1
        row = {
            "type": event_type,
            "label": EVENT_LABEL[event_type],
            "icon": EVENT_ICON[event_type],
            "category": EVENT_CATEGORY[event_type],
            "faced": faced,
            "logged": len(mine),
            "avg_damage": None,
            "best_mitigation": None,
            "lowest_damage": None,
            "worst_damage": None,
            "flawless": 0,
            "example": REAL_WORLD_EXAMPLES.get(event_type) if faced else None,
        }
        if mine:
            damages = [e["damage"] for e in mine]
            row["avg_damage"] = sum(damages) / len(damages)
            row["lowest_damage"] = min(damages)
            row["worst_damage"] = max(damages)
            row["best_mitigation"] = max(entry_mitigation(e) or 0.0 for e in mine)
            row["flawless"] = flawless_count(mine)
        rows.append(row)
    return rows


def codex_completion():
    rows = codex_entries()
    return sum(1 for row in rows if row["faced"] > 0), len(rows)


def codex_summary_text():
    done, total = codex_completion()
    if done >= total:
        return f"Codex complete: all {total} kinds of shock recorded."
    return f"{done} of {total} kinds of shock recorded. Face each kind to fill its page and unlock its real-world note."


def event_source_hint(event_type):
    """FY-3: where an event type can be met, when it is not in the Classic
    schedule -- so the Codex can say how to fill a page that the default
    run never fills. Empty for a type the Classic mix already contains."""
    if event_type in SCENARIOS[DEFAULT_SCENARIO]["schedule"]:
        return ""
    names = [data["label"] for data in SCENARIOS.values() if event_type in data["schedule"]]
    if not names:
        return ""
    return " It only arrives in the " + " or ".join(names) + " scenario" + ("s" if len(names) > 1 else "") + ", chosen before a run's first event."


def codex_stats_text(row):
    if row["faced"] == 0:
        return f"Not faced yet. Weather a {row['label']} to record it and unlock its real-world note.{event_source_hint(row['type'])}"
    if row["avg_damage"] is None:
        return f"Faced x{row['faced']}. Damage details are recorded for runs completed since the run log began."
    flawless = f" · Flawless Defense x{row['flawless']}" if row["flawless"] else ""
    return (
        f"Faced x{row['faced']} · average damage {row['avg_damage']:.0f} · "
        f"lowest {row['lowest_damage']:.0f}, worst {row['worst_damage']:.0f} · "
        f"best mitigation {row['best_mitigation'] * 100:.0f}%{flawless}"
    )


def render_codex_panel():
    toggle = document.getElementById("codex-toggle-button")
    panel = document.getElementById("codex-panel")
    done, total = codex_completion()
    toggle.innerText = "Hide Disaster Codex" if runstate.codex_open else f"📖 Disaster Codex ({done}/{total})"
    panel.hidden = not runstate.codex_open
    if not runstate.codex_open:
        return
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "codex-heading"
    heading.innerText = "Disaster Codex"
    panel.appendChild(heading)
    summary = document.createElement("p")
    summary.className = "comparison-message codex-summary"
    summary.innerText = codex_summary_text()
    panel.appendChild(summary)
    for row in codex_entries():
        card = document.createElement("div")
        card.className = "codex-card" + ("" if row["faced"] else " codex-card--locked")
        title = document.createElement("p")
        title.className = f"codex-title event-category--{row['category']}"
        title.innerText = f"{row['icon']} {row['label']}" + (" ✓" if row["faced"] else " 🔒")
        card.appendChild(title)
        stats = document.createElement("p")
        stats.className = "codex-stats"
        stats.innerText = codex_stats_text(row)
        card.appendChild(stats)
        example = row["example"]
        if example:
            note = document.createElement("p")
            note.className = "codex-note"
            note.innerText = f"In the real world: {example['title']}. {example['text']}"
            card.appendChild(note)
            link = document.createElement("a")
            link.className = "real-world-source"
            link.href = example["url"]
            link.target = "_blank"
            link.rel = "noopener noreferrer"
            link.innerText = f"Source: {example['source']} (read {example.get('read', REAL_WORLD_READ_DATE)})"
            card.appendChild(link)
        panel.appendChild(card)


# ---- E-1: lifetime statistics, from run_log_history -----------------------
STAT_BANDS = (("0-1 skills", 0, 1), ("2-3 skills", 2, 3), ("4+ skills", 4, 999))
STATS_KP_ROWS = 15


def lifetime_stats():
    logs = [entry for entry in run_log_history if isinstance(entry, dict)]
    category_damage = {c: 0.0 for c in ("weather", "non-weather", "social", "health")}
    per_type = {}
    for entry in logs:
        for event in entry.get("event_log", []) or []:
            if not isinstance(event, dict) or event.get("type") not in EVENT_LABEL:
                continue
            event_type = event["type"]
            category_damage[EVENT_CATEGORY[event_type]] += event.get("damage", 0.0)
            per_type.setdefault(event_type, []).append(event)
    matchups = []
    for event_type, events in per_type.items():
        mitigations = [entry_mitigation(e) or 0.0 for e in events]
        matchups.append(
            {
                "type": event_type,
                "count": len(events),
                "avg_mitigation": sum(mitigations) / len(mitigations),
                "avg_damage": sum(e["damage"] for e in events) / len(events),
            }
        )
    matchups.sort(key=lambda m: (-m["avg_mitigation"], m["type"]))
    kp_rows = []
    running = 0
    for entry in logs:
        earned = int(entry.get("knowledge_earned", 0) or 0)
        running += earned
        kp_rows.append({"run_number": entry.get("run_number"), "earned": earned, "total": running})
    bands = []
    for label, low, high in STAT_BANDS:
        scores = [
            entry.get("score", 0.0)
            for entry in logs
            if isinstance(entry.get("skill_strength"), int) and low <= entry["skill_strength"] <= high
        ]
        bands.append({"label": label, "runs": len(scores), "avg_score": (sum(scores) / len(scores)) if scores else None})
    return {
        "runs": len(logs),
        "category_damage": category_damage,
        "matchups": matchups,
        "kp_rows": kp_rows,
        "bands": bands,
        "flawless": sum(
            flawless_count([ev for ev in (e.get("event_log", []) or []) if isinstance(ev, dict)]) for e in logs
        ),
    }


def _stat_row(label, fraction, value_text):
    row = document.createElement("div")
    row.className = "stat-row"
    label_el = document.createElement("span")
    label_el.className = "stat-label"
    label_el.innerText = label
    row.appendChild(label_el)
    track = document.createElement("span")
    track.className = "stat-bar"
    track.setAttribute("aria-hidden", "true")
    fill = document.createElement("span")
    fill.className = "stat-bar-fill"
    fill.style.width = f"{max(0.0, min(1.0, fraction)) * 100:.0f}%"
    track.appendChild(fill)
    row.appendChild(track)
    value_el = document.createElement("span")
    value_el.className = "stat-value"
    value_el.innerText = value_text
    row.appendChild(value_el)
    return row


def _stat_heading(panel, text):
    heading = document.createElement("h3")
    heading.className = "stat-heading"
    heading.innerText = text
    panel.appendChild(heading)


def render_stats_panel():
    toggle = document.getElementById("stats-toggle-button")
    panel = document.getElementById("stats-panel")
    toggle.innerText = "Hide Lifetime Stats" if runstate.stats_open else "📊 Lifetime Stats"
    panel.hidden = not runstate.stats_open
    if not runstate.stats_open:
        return
    stats = lifetime_stats()
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "stats-heading"
    heading.innerText = "Lifetime Stats"
    panel.appendChild(heading)
    if not stats["runs"]:
        empty = document.createElement("p")
        empty.innerText = "No completed runs with a log yet. Finish a run and this page fills in."
        panel.appendChild(empty)
        return
    intro = document.createElement("p")
    intro.className = "comparison-message"
    intro.innerText = (
        f"Built from {stats['runs']} completed run{'s' if stats['runs'] != 1 else ''}. "
        "Every bar has its numbers written beside it."
    )
    panel.appendChild(intro)

    _stat_heading(panel, "Damage taken by category")
    total = sum(stats["category_damage"].values()) or 1.0
    for category, amount in stats["category_damage"].items():
        if category == "health" and amount <= 0:
            continue  # FY-3: the health category only exists in the Heat season scenario
        panel.appendChild(
            _stat_row(f"{CATEGORY_ICON[category]} {category.capitalize()}", amount / total,
                      f"{amount:.0f} damage ({amount / total * 100:.0f}%)")
        )

    _stat_heading(panel, "Average mitigation by event type")
    for item in stats["matchups"]:
        panel.appendChild(
            _stat_row(f"{EVENT_ICON[item['type']]} {EVENT_LABEL[item['type']]}", item["avg_mitigation"],
                      f"{item['avg_mitigation'] * 100:.0f}% prevented (avg {item['avg_damage']:.0f} damage, {item['count']} faced)")
        )
    if len(stats["matchups"]) >= 2:
        best, worst = stats["matchups"][0], stats["matchups"][-1]
        line = document.createElement("p")
        line.className = "stat-matchup"
        if best["avg_mitigation"] - worst["avg_mitigation"] < 0.005:
            line.innerText = "Every matchup is level so far: the same share of damage prevented against every kind of shock."
        else:
            line.innerText = (
                f"Best matchup: {EVENT_LABEL[best['type']]} ({best['avg_mitigation'] * 100:.0f}% prevented). "
                f"Worst matchup: {EVENT_LABEL[worst['type']]} ({worst['avg_mitigation'] * 100:.0f}% prevented)."
            )
        panel.appendChild(line)

    _stat_heading(panel, "Knowledge points over time")
    rows = stats["kp_rows"][-STATS_KP_ROWS:]
    most = max([r["earned"] for r in rows] + [1])
    for item in rows:
        panel.appendChild(
            _stat_row(f"Run {item['run_number']}", item["earned"] / most, f"+{item['earned']} (total {item['total']})")
        )
    if len(stats["kp_rows"]) > len(rows):
        note = document.createElement("p")
        note.className = "comparison-message"
        note.innerText = f"Showing the last {len(rows)} of {len(stats['kp_rows'])} runs."
        panel.appendChild(note)

    _stat_heading(panel, "Average score by skill strength")
    scored = [b["avg_score"] for b in stats["bands"] if b["avg_score"] is not None]
    top = max(scored + [1.0])
    for band in stats["bands"]:
        if band["avg_score"] is None:
            panel.appendChild(_stat_row(band["label"], 0.0, "no runs yet"))
        else:
            panel.appendChild(
                _stat_row(band["label"], band["avg_score"] / top,
                          f"{band['avg_score']:.0f} average over {band['runs']} run{'s' if band['runs'] != 1 else ''}")
            )
    note = document.createElement("p")
    note.className = "comparison-message"
    note.innerText = "Skill strength is recorded for runs completed from this update on; older runs are not in these bands."
    panel.appendChild(note)

    flawless = document.createElement("p")
    flawless.className = "stat-matchup"
    flawless.innerText = f"Flawless Defenses so far: {stats['flawless']}."
    panel.appendChild(flawless)
