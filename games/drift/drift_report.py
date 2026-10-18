"""The Region Report (data, text, HTML, copy, print) and the band-rise confetti."""

from js import document

import drift_runstate as runstate
from drift_assist import render_assist
from drift_messages import CODA_LEGACY_CHOICES
from drift_model_region import region
from drift_rules import (
    ACCELERATED_SEVERITY_MULTIPLIER, CAPACITY_LABEL, CAPACITY_PER_INVESTMENT, CAPACITY_TYPES, COUNCIL_BY_ID,
    INVEST_COST, POLICIES, subscore_arrow,
)
from drift_settings import _saved_at_ms, render_confirm_threshold, render_glossary, render_save_nudge
from drift_tiers import BAND_ORDER, band_rank, current_tier_id, render_tier_panel, tier_name
from drift_trendgraph import wellbeing_band, wellbeing_curve
from drift_visuals import _pulse


# ---- I-4: Region Report (printable card and copy-as-text) ---------------------------------------------


def _first_purchase_round():
    """The first round with any purchase, or None. Only trusted while the ledger still starts at round 1."""
    if not region.ledger or region.ledger[0]["round"] != 1:
        return None
    for row in region.ledger:
        if row["spent"] > 0:
            return row["round"]
    return None


def _strain_peak():
    strain = region.strain_log
    if not strain or max(strain) <= 0:
        return None
    index = strain.index(max(strain))
    return region.round_number - len(strain) + index, max(strain)


def region_report_data():
    r = region
    score = r.wellbeing_score()
    tier_id = current_tier_id()
    options = []
    if r.calendar_enabled:
        options.append("Crisis Calendar")
    if r.accelerated_severity_enabled:
        options.append(f"Accelerated Severity ({ACCELERATED_SEVERITY_MULTIPLIER:.0f}x)")
    if r.crisis_start_enabled:
        options.append("Crisis Start")
    key_rounds = []
    first = _first_purchase_round()
    key_rounds.append(("First purchase", f"round {first}" if first is not None else "not recorded"))
    key_rounds.append(("Net-positive turning point", f"round {r.net_positive_round}" if r.net_positive_round else "not yet"))
    key_rounds.append(("Thriving reached", f"round {r.thriving_round}" if r.thriving_round else "not yet"))
    if r.second_wave_status is None:
        wave = "not triggered"
    elif r.second_wave_status == "done":
        wave = f"began round {r.second_wave_start_round}, {r.second_wave_result}" if r.second_wave_start_round else f"over, {r.second_wave_result}"
    else:
        wave = r.second_wave_status
    key_rounds.append(("Second wave", wave))
    peak = _strain_peak()
    key_rounds.append(("Strain peak", f"{peak[1] * 100:.0f}% in round {peak[0]}" if peak else "none (strain stayed at zero)"))
    subscores = []
    for key, label in (("service", "Service quality"), ("economy", "Economic health"), ("cohesion", "Social cohesion")):
        values = [e.get(key, 0.0) for e in r.subscore_log if isinstance(e, dict)]
        subscores.append({
            "label": label, "now": {"service": r.service_quality(), "economy": r.economic_health(), "cohesion": r.social_cohesion()}[key],
            "first": values[0] if values else None, "arrow": subscore_arrow(r.subscore_log, key),
            "curve": wellbeing_curve(values, 20),
        })
    spent = dict(r.spend_by_type)
    derived = not any(spent[t] for t in CAPACITY_TYPES)
    roi_rows = []
    for t in CAPACITY_TYPES:
        funds_spent = r.capacity[t] / CAPACITY_PER_INVESTMENT[t] * INVEST_COST[t] if derived else spent[t]
        if t == "services":
            ret = (
                f"{r.cumulative_integration_contribution / r.cumulative_services_investment:.2f} funds back per fund"
                if r.cumulative_services_investment > 0 else "nothing returned yet"
            )
        else:
            ret = "no direct return; holds strain down"
        roi_rows.append({"label": CAPACITY_LABEL[t], "spent": funds_spent, "capacity": r.capacity[t], "return": ret})
    policy_levels = ", ".join(f"{POLICIES[p]['label']} {r.policy_level[p]}" for p in POLICIES if r.policy_level[p]) or "none funded"
    roi_rows.append({"label": "Policies", "spent": spent["policy"], "capacity": None, "return": policy_levels})
    roi = r.investment_roi()
    return {
        "name": r.region_name or "Unnamed region",
        "rounds": max(0, r.round_number - 1),
        "tier": tier_name(tier_id),
        "options": options,
        "assisted": runstate.assisted_run,
        "band": wellbeing_band(score),
        "score": score,
        "strain_level": r.strain_level(),
        "key_rounds": key_rounds,
        "subscores": subscores,
        "roi_rows": roi_rows,
        "roi_total": roi,
        "council": [COUNCIL_BY_ID[pid]["name"] for pid in r.council_picks],
        "coda": r.coda_legacy_choice,
        "curve": wellbeing_curve(r.wellbeing_log),
    }


def region_report_text():
    d = region_report_data()
    lines = [
        f"Region Report: {d['name']}",
        f"Difficulty: {d['tier']}" + (f" ({', '.join(d['options'])})" if d["options"] else " (no options on)")
        + (", assisted run" if d["assisted"] else ""),
        f"After {d['rounds']} rounds: {d['band']}, wellbeing {d['score']:.0f}, strain {d['strain_level']}",
        f"Wellbeing curve: {d['curve']}",
        "Key rounds:",
    ]
    lines += [f"  {label}: {value}" for label, value in d["key_rounds"]]
    lines.append("Sub-scores (first logged round -> now):")
    for s in d["subscores"]:
        first = f"{s['first']:.0f}" if s["first"] is not None else "-"
        lines.append(f"  {s['label']}: {first} -> {s['now']:.0f} {s['arrow']} {s['curve']}".rstrip())
    lines.append("Spending and return:")
    for row in d["roi_rows"]:
        cap = f", capacity {row['capacity']:.0f}" if row["capacity"] is not None else ""
        lines.append(f"  {row['label']}: {row['spent']:.0f} funds{cap}; {row['return']}")
    if d["roi_total"] is not None:
        lines.append(f"  Overall: {d['roi_total']:.2f} funds contributed back per fund invested")
    if d["council"]:
        lines.append("Council programs: " + ", ".join(d["council"]))
    if d["coda"] in CODA_LEGACY_CHOICES:
        lines.append("Carried forward: " + CODA_LEGACY_CHOICES[d["coda"]].split(":")[0])
    return "\n".join(lines)


def region_report_html():
    d = region_report_data()
    diff = d["tier"] + (f" ({', '.join(d['options'])})" if d["options"] else "") + (" - assisted run" if d["assisted"] else "")
    key_rows = "".join(f"<tr><td>{label}</td><td>{value}</td></tr>" for label, value in d["key_rounds"])
    sub_parts = []
    for s in d["subscores"]:
        first = f"{s['first']:.0f}" if s["first"] is not None else "-"
        sub_parts.append(
            f"<tr><td>{s['label']}</td><td>{first}</td><td>{s['now']:.0f}</td><td>{s['arrow']}</td>"
            f"<td class=\"report-curve\">{s['curve']}</td></tr>"
        )
    sub_rows = "".join(sub_parts)
    roi_parts = []
    for row in d["roi_rows"]:
        capacity = "-" if row["capacity"] is None else f"{row['capacity']:.0f}"
        roi_parts.append(
            f"<tr><td>{row['label']}</td><td>{row['spent']:.0f}</td><td>{capacity}</td><td>{row['return']}</td></tr>"
        )
    roi_rows = "".join(roi_parts)
    extras = []
    if d["roi_total"] is not None:
        extras.append(f"<p>Overall: {d['roi_total']:.2f} funds contributed back per fund invested.</p>")
    if d["council"]:
        extras.append(f"<p>Council programs: {', '.join(d['council'])}.</p>")
    if d["coda"] in CODA_LEGACY_CHOICES:
        extras.append(f"<p>Carried forward: {CODA_LEGACY_CHOICES[d['coda']]}</p>")
    return (
        f"<h3 class=\"report-title\">Region Report: {_escape_html(d['name'])}</h3>"
        f"<p><strong>Difficulty:</strong> {diff}</p>"
        f"<p><strong>After {d['rounds']} rounds:</strong> {d['band']}, wellbeing {d['score']:.0f}, strain {d['strain_level']}.</p>"
        f"<p class=\"report-curve\" aria-label=\"Wellbeing curve\">Wellbeing curve: {d['curve']}</p>"
        f"<table class=\"ledger-table\"><caption>Key rounds</caption><tbody>{key_rows}</tbody></table>"
        "<table class=\"ledger-table\"><caption>Sub-score trends</caption>"
        f"<thead><tr><th>Score</th><th>First</th><th>Now</th><th>Trend</th><th>Last 20 rounds</th></tr></thead><tbody>{sub_rows}</tbody></table>"
        "<table class=\"ledger-table\"><caption>Spending and return</caption>"
        f"<thead><tr><th>Spent on</th><th>Funds</th><th>Capacity</th><th>Return</th></tr></thead><tbody>{roi_rows}</tbody></table>"
        + "".join(extras)
    )


def _escape_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_report():
    toggle = document.getElementById("report-toggle-button")
    toggle.innerText = "Hide Region Report" if runstate.report_open else "📄 Region Report"
    panel = document.getElementById("report-panel")
    panel.hidden = not runstate.report_open
    if not runstate.report_open:
        return
    document.getElementById("report-card").innerHTML = region_report_html()
    document.getElementById("report-copy-status").innerText = runstate.report_note_text


# ---- GI-29: band-change confetti -------------------------------------------------------------------------
BAND_CONFETTI_MS = 2600


def _celebrate_band_rise(band_before):
    """After an action that advanced rounds: if the wellbeing band went up, set the note and play the
    confetti (CSS only; Reduce Motion, the OS setting and Animation speed Off hide it). Returns the new
    band name, or None when it did not rise."""
    score = region.wellbeing_score()
    if band_rank(score) <= BAND_ORDER.index(band_before):
        return None
    band = wellbeing_band(score)
    runstate.band_note_text = f"Wellbeing rose into the {band} band."
    _pulse("band-confetti", "band-confetti--go", BAND_CONFETTI_MS)
    document.getElementById("band-change-note").innerText = runstate.band_note_text
    document.getElementById("band-change-note").hidden = False
    return band


def _clear_band_note():
    runstate.band_note_text = ""
    note = document.getElementById("band-change-note")
    note.innerText = ""
    note.hidden = True


def _after_load_batch3():
    """A loaded save counts as saved at its own round; the transient notes start clean."""
    runstate.save_baseline_round = region.round_number
    runstate.nudge_snooze_round = 0
    runstate._last_seen_saved_at = _saved_at_ms()
    runstate.tier_note_text = ""
    runstate.report_note_text = ""
    _clear_band_note()


# ---- wiring ----------------------------------------------------------------------------------------------
def render_batch3():
    render_tier_panel()
    render_assist()
    render_save_nudge()
    render_glossary()
    render_report()
    render_confirm_threshold()
