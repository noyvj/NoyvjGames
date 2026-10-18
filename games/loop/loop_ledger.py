"""Cycle ledger table and notes (H-10/H-28), Past Chains archive and its graph (H-1)."""

import html
import math

from js import document

import loop_runstate as runstate
from loop_bridge import _copy_to_clipboard
from loop_career import career_counts
from loop_rules import ALL_GOODS, LEDGER_COLUMNS, LEDGER_MAX, PAST_CHAINS_MAX, PAST_CURVE_POINTS, clean_note


# ===========================================================================
# H-10 / H-28 (the cycle ledger and notes) and H-1 (Past Chains). Pure functions of state plus
# one module-level list, so they are directly testable.
# ===========================================================================
past_chains = []  # finished (reset) chains, oldest first; survives Start New Chain like the career

LEDGER_SORTS = {
    "newest": ("Newest first", lambda row: -row["cycle"]),
    "oldest": ("Oldest first", lambda row: row["cycle"]),
    "extraction": ("Most new extraction", lambda row: (-row["extraction"], row["cycle"])),
    "net": ("Biggest net gain", lambda row: (-ledger_net(row), row["cycle"])),
    "damage": ("Highest damage", lambda row: (-row["damage"], row["cycle"])),
}


def ledger_funds_in(row):
    return row["revenue"] + row["export"]


def ledger_funds_out(row):
    return (row["spent"] or 0.0) + row["extraction_cost"]


def ledger_net(row):
    return ledger_funds_in(row) - row["extraction_cost"]


def sorted_ledger():
    return sorted(runstate.chain.ledger, key=LEDGER_SORTS.get(runstate.ledger_sort, LEDGER_SORTS["newest"])[1])


def ledger_csv():
    """H-10: every ledger row as CSV text (header first)."""
    def cell(value):
        text = str(value)
        return '"' + text.replace('"', '""') + '"' if any(c in text for c in ',"\n') else text

    lines = [",".join((
        "cycle", "funds_in", "funds_out", "net", "spent_on_investments", "extraction_cost", "repair_units",
        "reuse_units", "recycle_units", "trade_units", "new_extraction_units", "damage_percent",
        "price_multiplier", "partners", "note",
    ))]
    for row in runstate.chain.ledger:
        spent = "" if row["spent"] is None else row["spent"]
        lines.append(",".join(cell(v) for v in (
            row["cycle"], round(ledger_funds_in(row), 1), round(ledger_funds_out(row), 1), round(ledger_net(row), 1),
            spent, row["extraction_cost"], row["repair"], row["reuse"], row["recycle"], row["trade"],
            row["extraction"], row["damage"], row["multiplier"], row["partners"] or "-", row["note"],
        )))
    return "\n".join(lines)


LEDGER_ROWS_SHOWN = 40


def ledger_table_html():
    rows = sorted_ledger()
    if not rows:
        return '<p class="comparison-message">No cycles yet. Each Advance Cycle adds a row here.</p>'
    shown = rows[:LEDGER_ROWS_SHOWN]
    head = (
        "<tr><th>Cycle</th><th>In</th><th>Out</th><th>Net</th><th>Repair</th><th>Reuse</th><th>Recycle</th>"
        "<th>Trade</th><th>New extr.</th><th>Damage</th><th>Price x</th><th>Partners</th><th>Note</th></tr>"
    )
    body = []
    for row in shown:
        body.append(
            "<tr>"
            f"<td>{row['cycle']}</td><td>{ledger_funds_in(row):.0f}</td><td>{ledger_funds_out(row):.0f}</td>"
            f"<td>{ledger_net(row):.0f}</td><td>{row['repair']:.0f}</td><td>{row['reuse']:.0f}</td>"
            f"<td>{row['recycle']:.0f}</td><td>{row['trade']:.0f}</td><td>{row['extraction']:.0f}</td>"
            f"<td>{row['damage']:.0f}%</td><td>{row['multiplier']:.2f}</td><td>{html.escape(row['partners'] or '-')}</td>"
            f"<td>{html.escape(row['note'])}</td></tr>"
        )
    more = ""
    if len(rows) > len(shown):
        more = f'<p class="comparison-message">Showing {len(shown)} of {len(rows)} cycles; the CSV has them all.</p>'
    return (
        '<div class="ledger-scroll"><table class="ledger-table"><caption class="sr-only">Cycle ledger</caption>'
        f"<thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>{more}"
    )


def _row_number(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and low <= value <= high


def ledger_to_save():
    """Compact JSON-safe form: one list per row, in LEDGER_COLUMNS order."""
    return [[row[name] for name in LEDGER_COLUMNS] for row in runstate.chain.ledger]


def ledger_from_save(raw):
    """Validated rows from a saved ledger; anything malformed is dropped, never repaired by guessing."""
    rows = []
    if not isinstance(raw, list):
        return rows
    for item in raw[-LEDGER_MAX:]:
        if not (isinstance(item, (list, tuple)) and len(item) == len(LEDGER_COLUMNS)):
            continue
        row = dict(zip(LEDGER_COLUMNS, item))
        cycle = row["cycle"]
        if not (isinstance(cycle, int) and not isinstance(cycle, bool) and 1 <= cycle <= 1_000_000):
            continue
        if row["spent"] is not None and not _row_number(row["spent"], 0, 1e9):
            continue
        if not all(_row_number(row[k], 0, 1e9) for k in (
            "revenue", "export", "extraction_cost", "repair", "reuse", "recycle", "trade", "extraction",
        )):
            continue
        if not (_row_number(row["damage"], 0, 100) and _row_number(row["multiplier"], 0, 100)):
            continue
        if not _row_number(row["funds_after"], 0, 1e12):
            continue
        partners = row["partners"]
        if not (isinstance(partners, str) and len(partners) <= 3 and set(partners) <= set("TRO")):
            continue
        if not isinstance(row["note"], str):
            continue
        row["note"] = clean_note(row["note"])
        rows.append(row)
    return rows


def past_chain_record():
    """H-1: a compact record of the chain that is ending (None if it never ran a cycle)."""
    if runstate.chain.cycle_number <= 1:
        return None
    log = runstate.chain.circular_fraction_log
    step = max(1, math.ceil(len(log) / PAST_CURVE_POINTS))
    curve = [round(f, 2) for f in log[::step]]
    record = {
        "category": runstate.chain.picked_category,
        "cycles": runstate.chain.cycle_number - 1,
        "closed": runstate.chain.first_loop_closed_cycle,
        "extracted": round(runstate.chain.total_extracted, 1),
        "score": round(runstate.chain.score(), 1),
        "repair": runstate.chain.circularity_investment["repair"],
        "reuse": runstate.chain.circularity_investment["reuse"],
        "recycle": runstate.chain.circularity_investment["recycle"],
        "trade": runstate.chain.trade_link_investment + runstate.chain.regional_trade_investment + runstate.chain.overseas_trade_investment,
        "curve": curve,
    }
    if runstate.chain.assist_used:
        record["assisted"] = True  # H-8: tagged, and left out of the mastery records
    return record


def archive_chain():
    """H-1: files the current chain in the Past Chains list (call just before a reset)."""
    record = past_chain_record()
    if record is None:
        return False
    career_counts["cycles"] += record["cycles"]  # H-12: the finished chain joins the career totals
    if record["closed"] is not None:
        career_counts["chains_closed"] += 1
    past_chains.append(record)
    del past_chains[:-PAST_CHAINS_MAX]
    return True


def past_chains_from_save(raw):
    records = []
    if not isinstance(raw, list):
        return records
    for item in raw[-PAST_CHAINS_MAX:]:
        if not isinstance(item, dict):
            continue
        cycles, closed = item.get("cycles"), item.get("closed")
        counts = [item.get(k) for k in ("repair", "reuse", "recycle", "trade")]
        curve = item.get("curve")
        if not (isinstance(cycles, int) and not isinstance(cycles, bool) and 1 <= cycles <= 1_000_000):
            continue
        if closed is not None and not (isinstance(closed, int) and not isinstance(closed, bool) and 1 <= closed <= 1_000_000):
            continue
        if item.get("category") not in ALL_GOODS:
            continue
        if not all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 1_000_000 for c in counts):
            continue
        if not (_row_number(item.get("extracted"), 0, 1e12) and _row_number(item.get("score"), -1e12, 1e12)):
            continue
        if not (isinstance(curve, list) and 0 < len(curve) <= PAST_CURVE_POINTS and all(_row_number(v, 0, 1) for v in curve)):
            continue
        record = {
            "category": item["category"], "cycles": cycles, "closed": closed,
            "extracted": float(item["extracted"]), "score": float(item["score"]),
            "repair": counts[0], "reuse": counts[1], "recycle": counts[2], "trade": counts[3],
            "curve": [float(v) for v in curve],
        }
        if item.get("assisted") is True:
            record["assisted"] = True
        records.append(record)
    return records


def past_chain_line(index, record):
    label = ALL_GOODS[record["category"]]["label"]
    closed = f"closed the loop on cycle {record['closed']}" if record["closed"] else "never closed the loop"
    return (
        f"Chain {index}: {label}, {record['cycles']} cycle{'' if record['cycles'] == 1 else 's'}, {closed}; "
        f"{record['extracted']:.0f} units extracted, score {record['score']:.0f}; bought repair {record['repair']}, "
        f"reuse {record['reuse']}, recycling {record['recycle']}, trade {record['trade']}."
        + (" Assisted." if record.get("assisted") else "")
    )


PAST_DASHES = ("", "6 3", "2 3", "8 3 2 3", "1 4")


def past_chains_svg():
    """H-1: the last five finished chains' circular-share curves plus the chain in play, one SVG.
    Each line has its own dash pattern and a numbered label at its end, so it never relies on hue."""
    shown = past_chains[-5:]
    first_number = len(past_chains) - len(shown) + 1  # chains are numbered by their place in the list
    series = [(f"{first_number + i}", record["curve"], PAST_DASHES[i % len(PAST_DASHES)], False) for i, record in enumerate(shown)]
    if runstate.chain.circular_fraction_log:
        series.append(("now", [round(f, 2) for f in runstate.chain.circular_fraction_log], "", True))
    if runstate.ghost is not None:  # GH-28: a loaded friend's run, drawn dotted and labelled "ghost"
        series.append(("ghost", list(runstate.ghost["fractions"]), "1 3", "ghost"))
    if not series:
        return ""
    width, height, left, bottom, top, right = 320.0, 150.0, 30.0, 18.0, 8.0, 34.0
    longest = max(len(curve) for _l, curve, _d, _c in series)
    span = max(1, longest - 1)
    parts = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" class="past-chart" role="img" '
        'aria-label="Circular share by cycle for your last chains and the one in play">'
    ]
    for pct in (0, 50, 100):
        y = top + (height - top - bottom) * (1 - pct / 100)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" class="past-grid"/>')
        parts.append(f'<text x="{left - 4}" y="{y + 3:.1f}" text-anchor="end" class="past-axis">{pct}%</text>')
    for label, curve, dash, current in series:
        points = []
        for i, value in enumerate(curve):
            x = left + (width - left - right) * (i / span if span else 0)
            y = top + (height - top - bottom) * (1 - value)
            points.append(f"{x:.1f},{y:.1f}")
        is_ghost = current == "ghost"
        stroke_w = 3 if current is True else (2.4 if is_ghost else 1.6)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        extra_class = " past-line--now" if current is True else (" past-line--ghost" if is_ghost else "")
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" class="past-line{extra_class}" '
                     f'stroke-width="{stroke_w}"{dash_attr}/>')
        end_x, end_y = points[-1].split(",")
        parts.append(f'<text x="{float(end_x) + 3:.1f}" y="{float(end_y) + 3:.1f}" class="past-label">{html.escape(label)}</text>')
    parts.append(f'<text x="{left}" y="{height - 4}" class="past-axis">cycle 1</text>')
    parts.append(f'<text x="{width - right}" y="{height - 4}" text-anchor="end" class="past-axis">cycle {longest}</text>')
    parts.append("</svg>")
    return "".join(parts)


def render_ledger_and_past():
    document.getElementById("ledger-table").innerHTML = ledger_table_html()
    document.getElementById("ledger-sort-select").value = runstate.ledger_sort
    document.getElementById("past-chains-chart").innerHTML = past_chains_svg()
    lines = [past_chain_line(i + 1, r) for i, r in enumerate(past_chains)]
    document.getElementById("past-chains-list").innerHTML = "".join(f"<li>{html.escape(line)}</li>" for line in reversed(lines))
    empty = not past_chains
    document.getElementById("past-chains-empty").hidden = not empty


def on_copy_ledger(event=None):
    status = document.getElementById("ledger-copy-status")
    if _copy_to_clipboard(ledger_csv()):
        status.innerText = f"Copied {len(runstate.chain.ledger)} cycle{'' if len(runstate.chain.ledger) == 1 else 's'} as CSV."
    else:
        status.innerText = "Could not copy automatically. Select the table instead."
