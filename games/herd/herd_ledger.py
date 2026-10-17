"""The Ranch Ledger (F-2) and the ghost of your best farm (Z-3e): filing a farm, the table, the chart and the ghost line.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import html
import json

import ghost as ghost_lib  # Z-3e: the shared best-farm ghost (shared/ghost.py)
from js import document

import herd_runstate as runstate
from herd_rules import METHANE_PENALTY_WEIGHT
from herd_util import _is_finite_number, _read_local_storage_item, _safe_int, _write_local_storage_item
from herd_model import rules_unranked
from herd_purchases import _confirm_dialog_ask
from herd_blind import blind_hidden


# ---- F-2 Ranch Ledger ---------------------------------------------------------------------
# One compact line per finished farm (a handover) or per farm the player files by hand, kept in this
# browser (localStorage), never in a save. A trend chart of score against the pure-growth baseline,
# filterable by mode.
LEDGER_STORAGE_KEY = "herd-ranch-ledger-v1"
LEDGER_MAX = 60
LEDGER_FILTERS = ("all", "plain", "seasons", "cap")
LEDGER_LEVERS = ("feed", "caps", "capture", "pivot", "genetics", "supply")
LEDGER_LEVER_SHORT = {"feed": "Feed", "caps": "Caps", "capture": "Capture", "pivot": "Pivot", "genetics": "Breeding", "supply": "Supply"}


def farm_mode():
    if runstate.farm.variation_enabled and runstate.farm.regional_cap_enabled:
        return "seasons and cap"
    if runstate.farm.variation_enabled:
        return "seasons"
    if runstate.farm.regional_cap_enabled:
        return "cap"
    return "plain"


def ledger_entry(finished=False):
    levers = dict(runstate.farm.decoupling_investment)
    levers["pivot"] = runstate.farm.plant_pivot_investment
    levers["genetics"] = runstate.farm.genetics_active + len(runstate.farm.genetics_pending)
    levers["supply"] = runstate.farm.supply_chain_investment
    return {
        "gen": runstate.generation, "round": runstate.farm.round_number, "funds": round(runstate.farm.funds, 1), "methane": round(runstate.farm.methane, 1),
        "score": round(runstate.farm.score(), 1), "base": round(runstate.farm.counterfactual_score(), 1), "herd": runstate.farm.herd_size,
        "poultry": runstate.farm.poultry_size, "mode": farm_mode(), "custom": bool(rules_unranked()), "done": bool(finished),
        "levers": {k: int(levers.get(k, 0)) for k in LEDGER_LEVERS},
    }


def _clean_ledger_entry(raw):
    """A usable ledger line from stored JSON, or None."""
    if not isinstance(raw, dict):
        return None
    numbers = {}
    for key in ("gen", "round", "funds", "methane", "score", "base", "herd", "poultry"):
        if not _is_finite_number(raw.get(key)):
            return None
        numbers[key] = float(raw[key])
    mode = raw.get("mode")
    if mode not in ("plain", "seasons", "cap", "seasons and cap"):
        return None
    levers = raw.get("levers")
    if not isinstance(levers, dict):
        return None
    clean_levers = {k: _safe_int(levers.get(k), 0) for k in LEDGER_LEVERS}
    return {
        "gen": max(1, int(numbers["gen"])), "round": max(1, int(numbers["round"])), "funds": numbers["funds"],
        "methane": max(0.0, numbers["methane"]), "score": numbers["score"], "base": numbers["base"],
        "herd": max(0, int(numbers["herd"])), "poultry": max(0, int(numbers["poultry"])), "mode": mode,
        "custom": raw.get("custom") is True, "done": raw.get("done") is True, "levers": clean_levers,
    }


def read_ledger():
    raw = _read_local_storage_item(LEDGER_STORAGE_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    entries = [e for e in (_clean_ledger_entry(item) for item in data) if e is not None]
    return entries[-LEDGER_MAX:]


def ledger_record(entry):
    """Files a line. Filing the same generation at the same round again replaces that line instead of repeating it."""
    entries = [e for e in read_ledger() if not (e["gen"] == entry["gen"] and e["round"] == entry["round"])]
    entries.append(entry)
    del entries[:-LEDGER_MAX]
    _write_local_storage_item(LEDGER_STORAGE_KEY, json.dumps(entries))
    return entries


# ---- Z-3e: the ghost of your best farm (shared/ghost.py) ---------------------------------------------------------------
# Two numbers per round are kept for the best farm filed in each farm mode: its score (funds minus the weighted methane,
# the number the whole game is about) and its methane (the line on the "Methane over time" chart, where the ghost is
# drawn). A farm is filed when it is handed over or filed in the Ranch Ledger, so the ghost is the best of those: the
# highest result against the pure-growth baseline, the latest on a tie, after at least GHOST_MIN_ROUNDS rounds. Kept per
# browser in its own localStorage key (like the ledger; the key exists only once a ghost does, saves are unchanged). Sandbox
# and custom-rules farms are never ranked, so they neither become a ghost nor race one. Blind runs show nothing until revealed.
GHOST_STORAGE_KEY = "herd-ghost-v1"
GHOST_PREF_KEY = "herd-ghost-on"
GHOST_MIN_ROUNDS = 4
GHOST_MODE_KEYS = ("plain", "seasons", "cap", "seasons_and_cap")


def _ghost_el(element_id):
    try:
        return document.getElementById(element_id)
    except KeyError:
        return None


def ghost_mode_key():
    return farm_mode().replace(" ", "_")


def ghost_eligible():
    return not rules_unranked()


def farm_series(source=None):
    """([score after each round played], [methane after each round]) for a farm, or None when it has played no round
    or its funds were not recorded for every round (a save from before the funds history)."""
    source = runstate.farm if source is None else source
    methane, funds = source.methane_history, source.funds_history
    if len(methane) < 2 or len(funds) != len(methane):
        return None
    scores, gases = [], []
    for i in range(1, len(methane)):
        if not _is_finite_number(funds[i]) or not _is_finite_number(methane[i]):
            return None
        scores.append(funds[i] - methane[i] * METHANE_PENALTY_WEIGHT)
        gases.append(methane[i])
    return scores, gases


def load_ghosts():
    """The stored best farms, {mode key: {"gen", "result", "score", "methane"}}; every trace goes through ghost.load
    and anything unreadable, unknown or hand-edited is dropped (no ghost, nothing breaks)."""
    raw = _read_local_storage_item(GHOST_STORAGE_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    out = {}
    if not isinstance(data, dict):
        return out
    for key in GHOST_MODE_KEYS:
        item = data.get(key)
        if not isinstance(item, dict):
            continue
        score_trace, methane_trace = ghost_lib.load(item.get("score")), ghost_lib.load(item.get("methane"))
        result = ghost_lib.clean_number(item.get("result"))
        if score_trace is None or methane_trace is None or result is None or score_trace["turns"] != methane_trace["turns"]:
            continue
        out[key] = {"gen": _safe_int(item.get("gen"), 1) or 1, "result": result, "score": score_trace, "methane": methane_trace}
    return out


def ghost_entry():
    return load_ghosts().get(ghost_mode_key())


def file_ghost():
    """Keep the farm being filed as the ghost for its mode when it is the best result so far there. True when kept."""
    series = farm_series()
    if not ghost_eligible() or series is None or len(series[0]) < GHOST_MIN_ROUNDS:
        return False
    label = f"Farm {runstate.generation}"
    traces = []
    for values in series:
        recorder = ghost_lib.Recorder()
        for value in values:
            recorder.record(value)
        traces.append(recorder.trace(label))
    result = ghost_lib.clean_number(runstate.farm.score() - runstate.farm.counterfactual_score())
    if traces[0] is None or traces[1] is None or result is None:
        return False
    ghosts = load_ghosts()
    key = ghost_mode_key()
    if key in ghosts and result < ghosts[key]["result"]:
        return False
    ghosts[key] = {"gen": runstate.generation, "result": result, "score": traces[0], "methane": traces[1]}
    _write_local_storage_item(GHOST_STORAGE_KEY, json.dumps(ghosts))
    return True


def ghost_enabled():
    return _read_local_storage_item(GHOST_PREF_KEY) != "0"


def _rounded_result(result, digits):
    """A ghost.compare result with its lead rounded the way the game shows its numbers; under half a unit is level."""
    if result is None or result["status"] not in ("ahead", "behind"):
        return result
    lead = round(result["lead"], digits)
    return dict(result, status="level", lead=0) if lead == 0 else dict(result, lead=lead)


def ghost_sentences():
    """(score sentence, methane sentence) from the shared wording for the farm being played against the stored ghost, or
    None when there is nothing to compare yet."""
    entry = ghost_entry()
    series = farm_series()
    if entry is None or series is None:
        return None
    who = f"your best farm ({entry['score']['label']})" if entry["score"]["label"] else "your best farm"
    score = ghost_lib.summary(_rounded_result(ghost_lib.compare(series[0], entry["score"]), 0), label=who)
    gas = ghost_lib.summary(_rounded_result(ghost_lib.compare(series[1], entry["methane"], higher_is_better=False), 1), label=who, unit=" methane")
    return score, gas


def ghost_note_text():
    """The sentence(s) under the methane chart; "" while a blind run is hidden."""
    if blind_hidden():
        return ""
    if not ghost_eligible():
        return "Ghost: not used on a practice sandbox or custom-rules farm, because those are never ranked."
    entry = ghost_entry()
    if entry is None:
        return (f"Ghost: hand a farm over, or file one in the Ranch Ledger after {GHOST_MIN_ROUNDS} or more rounds, and your best "
                "one is kept here to race, one score and one methane number per round.")
    sentences = ghost_sentences()
    if sentences is None:
        return (f"Ghost: your best {farm_mode()} farm ({entry['score']['label']}) ran {entry['score']['turns']} rounds. "
                "This farm is compared with it after every round.")
    if sentences[0] == sentences[1]:   # the ghost's run ended before this round: one sentence says it for both numbers
        return sentences[0].replace("ghost: ", "Ghost: ", 1) + "."
    return f"{sentences[0].replace('ghost: ', 'Ghost: ', 1)}. Methane (lower is better): {sentences[1].replace('ghost: ', '', 1)}."


def ghost_graph_data():
    """What the methane chart needs to draw the ghost, or None (switched off, blind, no ghost, no rounds yet)."""
    if blind_hidden() or not ghost_eligible() or not ghost_enabled():
        return None
    entry, sentences = ghost_entry(), ghost_sentences()
    if entry is None or sentences is None:
        return None
    return {"trace": entry["methane"], "sentence": ghost_note_text()}


def render_ghost():
    note, toggle_wrap, toggle = _ghost_el("ghost-note"), _ghost_el("ghost-toggle-wrap"), _ghost_el("ghost-toggle")
    has_entry = ghost_eligible() and ghost_entry() is not None and not blind_hidden()
    if toggle_wrap is not None:
        toggle_wrap.hidden = not has_entry
    if toggle is not None:
        toggle.checked = ghost_enabled()
    if note is not None:
        text = ghost_note_text() if ghost_enabled() else ""
        note.innerText = text
        note.hidden = not text


def ledger_matches(entry, which):
    if which == "all":
        return True
    if which == "plain":
        return entry["mode"] == "plain"
    return which in entry["mode"]


def ledger_rows(which=None):
    which = runstate.ledger_filter if which is None else which
    return [e for e in read_ledger() if ledger_matches(e, which)]


def ledger_levers_text(entry):
    parts = [f"{LEDGER_LEVER_SHORT[k]} {entry['levers'][k]}" for k in LEDGER_LEVERS if entry["levers"][k]]
    return ", ".join(parts) if parts else "none"


def ledger_table_html(rows):
    if not rows:
        return "<p class=\"comparison-message\">No farms filed here yet. A handover files the farm automatically; the button above files the one you are playing.</p>"
    head = (
        '<caption>Finished and filed farms, oldest first</caption><thead><tr><th scope="col">Gen</th>'
        '<th scope="col">Rounds</th><th scope="col">Funds</th><th scope="col">Methane</th><th scope="col">Score</th>'
        '<th scope="col">Vs baseline</th><th scope="col">Levers</th><th scope="col">Flock</th><th scope="col">Mode</th></tr></thead>'
    )
    body = ""
    for e in rows:
        note = " (custom rules, unranked)" if e["custom"] else ""
        body += (
            f'<tr><th scope="row">{e["gen"]}{"" if e["done"] else " (filed)"}</th><td>{e["round"] - 1}</td><td>{e["funds"]:.0f}</td>'
            f'<td>{e["methane"]:.0f}</td><td>{e["score"]:.0f}</td><td>{e["score"] - e["base"]:+.0f}</td>'
            f'<td>{html.escape(ledger_levers_text(e))}</td><td>{e["poultry"]}</td><td>{html.escape(e["mode"])}{note}</td></tr>'
        )
    return f'<table class="compare-table ledger-table">{head}<tbody>{body}</tbody></table>'


def ledger_chart_svg(rows):
    """Score minus the pure-growth baseline for each filed farm, in order: a line with a square at every
    point (the shape, not just the colour), a dashed zero line and the best point labelled."""
    if len(rows) < 2:
        return ""
    width, height, pad = 260, 80, 10
    values = [e["score"] - e["base"] for e in rows] + [0.0]
    low, high = min(values), max(values)
    span = (high - low) or 1.0

    def y_of(v):
        return height - pad - (height - 2 * pad) * ((v - low) / span)

    points = [(pad + (width - 2 * pad) * i / (len(rows) - 1), y_of(e["score"] - e["base"])) for i, e in enumerate(rows)]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    marks = "".join(f'<rect class="ledger-mark" x="{x - 2.5:.1f}" y="{y - 2.5:.1f}" width="5" height="5"/>' for x, y in points)
    label = f"Score against the pure-growth baseline for {len(rows)} filed farms; best {max(values):+.0f}."
    return (
        f'<svg viewBox="0 0 {width} {height}" class="ledger-chart-svg" role="img" aria-label="{label}"><title>{label}</title>'
        f'<line class="ledger-zero" x1="{pad}" x2="{width - pad}" y1="{y_of(0):.1f}" y2="{y_of(0):.1f}"/>'
        f'<polyline class="ledger-line" points="{path}"/>{marks}</svg>'
    )


def render_ledger():
    rows = ledger_rows()
    document.getElementById("ledger-table").innerHTML = ledger_table_html(rows)
    document.getElementById("ledger-chart").innerHTML = ledger_chart_svg(rows)
    total = len(read_ledger())
    best = max((e["score"] - e["base"] for e in read_ledger()), default=None)
    document.getElementById("ledger-summary").innerText = (
        "Nothing filed yet." if total == 0 else
        f"{total} farm{'s' if total != 1 else ''} filed in this browser; best result against the baseline: {best:+.0f}."
    )
    document.getElementById("ledger-clear-button").disabled = total == 0 or runstate.sandbox_active
    document.getElementById("ledger-add-button").disabled = runstate.sandbox_active


def on_ledger_filter(event=None):
    value = document.getElementById("ledger-filter").value
    runstate.ledger_filter = value if value in LEDGER_FILTERS else "all"
    render_ledger()


def _clear_ledger():
    if runstate.sandbox_active:
        return
    _write_local_storage_item(LEDGER_STORAGE_KEY, "[]")
    render_ledger()


def on_ledger_clear(event=None):
    _confirm_dialog_ask(
        action_id="herd-clear-ledger",
        message="Clear the Ranch Ledger? Every filed farm is removed from this browser. Your saves are not touched.",
        confirm_label="Clear ledger",
        on_confirm=_clear_ledger,
        allow_skip=False,
    )
