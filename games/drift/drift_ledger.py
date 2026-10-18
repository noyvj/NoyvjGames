"""The Round Ledger: rows, sort and filter, CSV copy and the round recap line."""

from js import document

import drift_runstate as runstate
from drift_model_region import region
from drift_rules import LEDGER_FIELDS, LEDGER_MAX_ENTRIES, STRAIN_LEVEL_THRESHOLDS


# ===========================================================================
# Round-3 batch (2026-10-07): the Round Ledger and recap line (I-8, I-17), the
# undo family (I-15 Reset this round, GI-18 Rewind Token), Play 5 rounds
# (GI-30), the Region Collection (GI-15 personality titles, GI-22 civic
# milestones) and a live tab title (I-24). None of it changes a rule or a
# number in a run: the ledger and collection only record, undo only restores
# an earlier state, and Play 5 rounds is five ordinary Advance Rounds.
# ===========================================================================

# ---- I-8 / I-17: Round Ledger ---------------------------------------------
LEDGER_SORTS = {
    "round_desc": ("Newest first", lambda r: (-r["round"],)),
    "round_asc": ("Oldest first", lambda r: (r["round"],)),
    "strain": ("Highest strain", lambda r: (-r["strain"], -r["round"])),
    "wellbeing": ("Highest wellbeing", lambda r: (-r["wellbeing"], -r["round"])),
    "arrivals": ("Most arrivals", lambda r: (-r["arrivals"], -r["round"])),
    "spent": ("Most spent", lambda r: (-r["spent"], -r["round"])),
}
LEDGER_FILTERS = {
    "all": ("All rounds", lambda r: True),
    "purchases": ("Rounds with purchases", lambda r: r["spent"] > 0),
    "no_purchases": ("Rounds with no purchases", lambda r: r["spent"] <= 0),
    "strained": ("Strained or critical", lambda r: r["strain"] >= STRAIN_LEVEL_THRESHOLDS[1][0]),
    "auto": ("Rounds from Play 5 rounds", lambda r: r["auto"]),
}


def strain_label(fraction):
    label = STRAIN_LEVEL_THRESHOLDS[0][1]
    for threshold, name in STRAIN_LEVEL_THRESHOLDS:
        if fraction >= threshold:
            label = name
    return label


def ledger_rows(sort_key="round_desc", filter_key="all"):
    """The ledger rows after filtering and sorting (copies, newest first by default)."""
    keep = LEDGER_FILTERS.get(filter_key, LEDGER_FILTERS["all"])[1]
    order = LEDGER_SORTS.get(sort_key, LEDGER_SORTS["round_desc"])[1]
    return sorted((dict(row) for row in region.ledger if keep(row)), key=order)


def ledger_csv():
    """CSV text of the whole ledger, oldest round first (strain as a percentage)."""
    header = ["strain_pct" if name == "strain" else name for name in LEDGER_FIELDS]
    lines = [",".join(header)]
    for row in region.ledger:
        cells = []
        for name in LEDGER_FIELDS:
            value = row[name]
            if name == "auto":
                cells.append("yes" if value else "no")
            elif name == "strain":
                cells.append(f"{value * 100:.1f}")
            elif name == "round":
                cells.append(str(int(value)))
            else:
                cells.append(f"{value:.2f}")
        lines.append(",".join(cells))
    return "\n".join(lines)


def round_recap_message(row, previous_strain=0.0):
    """I-17: one plain line about the round that just resolved."""
    delta = row["strain"] - previous_strain
    if abs(delta) < 0.02:
        trend = "steady"
    else:
        trend = "up" if delta > 0 else "down"
    cover = (
        f"{row['shortfall']:.0f} people beyond capacity"
        if row["shortfall"] >= 0.5
        else "capacity covered everyone"
    )
    return (
        f"Round {row['round']}: {row['arrivals']:.0f} arrived, {row['integrated_new']:.0f} integrated, "
        f"{cover}; strain {trend} at {row['strain'] * 100:.0f}% ({strain_label(row['strain'])}); "
        f"income {row['income']:.0f}, spent {row['spent']:.0f}."
    )


def latest_recap():
    if not region.ledger:
        return None
    previous = region.ledger[-2]["strain"] if len(region.ledger) > 1 else 0.0
    return round_recap_message(region.ledger[-1], previous)


def _ledger_table_html(rows):
    head = (
        "<tr><th>Rd</th><th>Spent (H/S/I/P)</th><th>Income</th><th>Arrived</th><th>Integr.</th>"
        "<th>Pending</th><th>Strain</th><th>Svc / Eco / Coh</th><th>Wellbeing</th><th>Funds</th></tr>"
    )
    body = []
    for r in rows:
        auto = " (auto)" if r["auto"] else ""
        body.append(
            f"<tr><td>{r['round']}{auto}</td>"
            f"<td>{r['spent']:.0f} ({r['housing']:.0f}/{r['services']:.0f}/{r['infrastructure']:.0f}/{r['policy']:.0f})</td>"
            f"<td>{r['income']:.0f}</td><td>{r['arrivals']:.0f}</td><td>{r['integrated_new']:.0f}</td>"
            f"<td>{r['pending']:.0f}</td><td>{r['strain'] * 100:.0f}% {strain_label(r['strain'])}</td>"
            f"<td>{r['service']:.0f} / {r['economy']:.0f} / {r['cohesion']:.0f}</td>"
            f"<td>{r['wellbeing']:.0f}</td><td>{r['funds']:.0f}</td></tr>"
        )
    return f"<table class=\"ledger-table\"><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"


def render_ledger():
    count = len(region.ledger)
    toggle = document.getElementById("ledger-toggle-button")
    toggle.innerText = "Hide Round Ledger" if runstate.ledger_open else f"📒 Round Ledger ({count})"
    panel = document.getElementById("ledger-panel")
    panel.hidden = not runstate.ledger_open
    if not runstate.ledger_open:
        return
    rows = ledger_rows(runstate.ledger_sort, runstate.ledger_filter)
    summary = document.getElementById("ledger-summary")
    if count == 0:
        summary.innerText = "No rounds resolved yet. Every Advance Round adds a row here."
        document.getElementById("ledger-table").innerHTML = ""
    else:
        total_spent = sum(r["spent"] for r in region.ledger)
        summary.innerText = (
            f"{count} round(s) recorded (the latest {LEDGER_MAX_ENTRIES} are kept), showing {len(rows)}. "
            f"Total spent: {total_spent:.0f}. H/S/I/P = Housing / Services / Infrastructure / Policy spending."
        )
        document.getElementById("ledger-table").innerHTML = _ledger_table_html(rows)
    document.getElementById("copy-ledger-csv-button").disabled = count == 0


def _copy_to_clipboard(text):
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    navigator = getattr(_js, "navigator", None)
    clipboard = getattr(navigator, "clipboard", None) if navigator is not None else None
    if clipboard is None:
        return False
    try:
        clipboard.writeText(text)
        return True
    except Exception:  # noqa: BLE001 -- a refused clipboard just falls back to the text box
        return False
