"""The Harbor Ledger table."""

from js import document

import tide_runstate as runstate
from tide_coasts import heritage_sites
from tide_rules import ADAPTATION_TIERS, LEDGER_COLUMNS, LEDGER_KEYS, TICKER_FILTERS, TIER_BADGES


def ticker_category(message):
    """D-17: classifies a ticker message from its wording, so older saves
    (which stored plain strings) filter exactly like new ones."""
    text = message.lower()
    if "⛈" in message or "storm surge in season" in text:
        return "storm"
    if (
        text.startswith(("monitoring report", "checkpoint", "replaying", "managed retreat"))
        or "people had to leave" in text
        or "founded" in text
        or any(site["name"].lower() in text for site in heritage_sites())
    ):
        return "chronicle"
    if any(word in text for word in ("fish", "acidity", "stock", "yield")):
        return "fish"
    if any(word in text for word in ("diversif", "economy", "income", "funds", "tourism", "aquaculture")):
        return "economy"
    if any(word in text for word in ("sea", "flood", "tile", "coast", "tier", "adaptation", "damage", "seawall", "tide")):
        return "sea"
    return "other"


def filtered_ticker_history(category=None, search=None):
    """D-17: the full history, narrowed by chip and by a case-insensitive
    text search. Returns a new list; the stored history is never changed."""
    category = runstate.ticker_filter if category is None else category
    search = runstate.ticker_search if search is None else search
    needle = (search or "").strip().lower()
    messages = []
    for message in runstate.state.ticker_full_history:
        if category != "all" and ticker_category(message) != category:
            continue
        if needle and needle not in message.lower():
            continue
        messages.append(message)
    return messages


def render_ticker_history():
    """D5: the full, uncapped-within-TICKER_FULL_HISTORY_LIMIT ticker log
    behind an expandable panel, alongside (not instead of) the short live
    ticker rendered separately above. D-17: chips and a search box narrow
    this history (the short live ticker is deliberately never filtered)."""
    history_el = document.getElementById("ticker-history-list")
    if history_el is None:
        return
    for key, _label in TICKER_FILTERS:
        chip = document.getElementById(f"ticker-filter-{key}")
        if chip is not None:
            chip.setAttribute("aria-pressed", "true" if key == runstate.ticker_filter else "false")
            if key == runstate.ticker_filter:
                chip.classList.add("selected")
            else:
                chip.classList.remove("selected")
    messages = filtered_ticker_history()
    status_el = document.getElementById("ticker-filter-status")
    if status_el is not None:
        filtering = runstate.ticker_filter != "all" or runstate.ticker_search.strip()
        status_el.innerText = (
            f"Showing {len(messages)} of {len(runstate.state.ticker_full_history)} message(s)."
            if filtering and runstate.state.ticker_full_history
            else ""
        )
    if not runstate.state.ticker_full_history:
        history_el.innerHTML = "No notable changes yet."
    elif not messages:
        history_el.innerHTML = "No messages match this filter."
    else:
        history_el.innerHTML = "<br>".join(messages)


def _make_ticker_filter_handler(key):
    def handler(event=None):
        runstate.ticker_filter = key
        render_ticker_history()
    return handler


# ---- D-17: chips and search for the short live ticker -----------------------------


def filtered_live_ticker(category=None, search=None):
    category = runstate.live_ticker_filter if category is None else category
    needle = (runstate.live_ticker_search if search is None else search or "").strip().lower()
    messages = []
    for message in runstate.state.ticker_log:
        if category != "all" and ticker_category(message) != category:
            continue
        if needle and needle not in message.lower():
            continue
        messages.append(message)
    return messages


def live_ticker_filtering():
    return runstate.live_ticker_filter != "all" or bool(runstate.live_ticker_search.strip())


def live_filter_label():
    if not live_ticker_filtering():
        return "Filter this list"
    parts = []
    if runstate.live_ticker_filter != "all":
        parts.append(next(label for key, label in TICKER_FILTERS if key == runstate.live_ticker_filter))
    if runstate.live_ticker_search.strip():
        parts.append("search")
    return "Filter this list (on: " + " + ".join(parts) + ")"


def render_live_ticker():
    """The short live ticker, narrowed by its own chip and search when a player turns one on."""
    ticker_el = document.getElementById("ticker-log")
    if ticker_el is not None:
        messages = filtered_live_ticker()
        if not runstate.state.ticker_log:
            ticker_el.innerHTML = "No notable changes yet."
        elif not messages:
            ticker_el.innerHTML = "No recent message matches this filter."
        else:
            ticker_el.innerHTML = "<br>".join(messages)
    for key, _label in TICKER_FILTERS:
        chip = document.getElementById(f"live-filter-{key}")
        if chip is not None:
            on = key == runstate.live_ticker_filter
            chip.setAttribute("aria-pressed", "true" if on else "false")
            if on:
                chip.classList.add("selected")
            else:
                chip.classList.remove("selected")
    summary = document.getElementById("live-filter-summary")
    if summary is not None:
        summary.innerText = live_filter_label()
    status = document.getElementById("live-filter-status")
    if status is not None:
        hidden = len(runstate.state.ticker_log) - len(filtered_live_ticker())
        if not (live_ticker_filtering() and runstate.state.ticker_log):
            status.innerText = ""
        elif hidden > 0:
            status.innerText = (
                f"Filtered: {hidden} of the last {len(runstate.state.ticker_log)} message(s) are hidden. "
                "Choose All and clear the search to see everything."
            )
        else:
            status.innerText = "Filtered: every recent message matches."


def _make_live_filter_handler(key):
    def handler(event=None):
        runstate.live_ticker_filter = key
        render_live_ticker()
    return handler


# ---- D-1 Harbor Ledger ----------------------------------------------
LEDGER_CHART_WIDTH = 80
LEDGER_CHART_HEIGHT = 22


def _ledger_chart_svg(key):
    series = runstate.state.ledger_series(key)
    if len(series) < 2:
        return ""
    low, high = min(series), max(series)
    span = high - low
    step = LEDGER_CHART_WIDTH / (len(series) - 1)
    points = []
    for i, value in enumerate(series):
        y = LEDGER_CHART_HEIGHT / 2 if span <= 1e-9 else (
            LEDGER_CHART_HEIGHT - 2 - (value - low) / span * (LEDGER_CHART_HEIGHT - 4)
        )
        points.append(f"{i * step:.1f},{y:.1f}")
    label = dict(LEDGER_COLUMNS)[key]
    return (
        f'<svg viewBox="0 0 {LEDGER_CHART_WIDTH} {LEDGER_CHART_HEIGHT}" class="ledger-chart" '
        f'role="img" aria-label="{label} by season, from {series[0]:.4g} to {series[-1]:.4g}">'
        f'<polyline points="{" ".join(points)}" fill="none" stroke="currentColor" stroke-width="1.6" />'
        f"</svg>"
    )


def _ledger_cell(key, entry):
    value = entry[key]
    if key == "funds" or key == "damage":
        return f"{value:.0f}"
    if key == "acidity":
        return f"{value:.1f}"
    if key == "fish_yield":
        return f"{value * 100:.0f}%"
    if key == "tier":
        index = max(0, min(int(value), len(ADAPTATION_TIERS) - 1))
        return f"{TIER_BADGES[index]} {index}"
    return str(value)


def ledger_rows_html():
    rows = []
    for entry in runstate.state.sorted_ledger(runstate.ledger_sort_key, runstate.ledger_sort_descending):
        cells = "".join(f"<td>{_ledger_cell(key, entry)}</td>" for key in LEDGER_KEYS)
        rows.append(f"<tr>{cells}</tr>")
    return "".join(rows)


def render_ledger():
    toggle = document.getElementById("ledger-toggle-button")
    panel = document.getElementById("ledger-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Harbor Ledger" if runstate.ledger_open else "📒 Harbor Ledger"
    panel.hidden = not runstate.ledger_open
    if not runstate.ledger_open:
        return
    for key, label in LEDGER_COLUMNS:
        button = document.getElementById(f"ledger-sort-{key}")
        header = document.getElementById(f"ledger-th-{key}")
        active = key == runstate.ledger_sort_key
        if button is not None:
            button.innerText = label + (" ▼" if active and runstate.ledger_sort_descending else " ▲" if active else "")
        if header is not None:
            header.setAttribute(
                "aria-sort",
                ("descending" if runstate.ledger_sort_descending else "ascending") if active else "none",
            )
        chart = document.getElementById(f"ledger-chart-{key}")
        if chart is not None:
            chart.innerHTML = "" if key == "season" else _ledger_chart_svg(key)
    body = document.getElementById("ledger-body")
    if body is not None:
        body.innerHTML = ledger_rows_html()
    summary = document.getElementById("ledger-summary")
    if summary is not None:
        summary.innerText = runstate.state.ledger_summary_text(runstate.ledger_sort_key, runstate.ledger_sort_descending)


def _make_ledger_sort_handler(key):
    def handler(event=None):
        if key == runstate.ledger_sort_key:
            runstate.ledger_sort_descending = not runstate.ledger_sort_descending
        else:
            runstate.ledger_sort_key = key
            runstate.ledger_sort_descending = True
        render_ledger()
    return handler
