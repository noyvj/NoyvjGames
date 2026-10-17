"""The What's New, community comparison, climate scientist and info panels, plus the compare-history list."""

import json

import info_page
from js import document

import thaw_runstate as runstate
from thaw_bridge import _escape, _num, _read_local_storage_item, _write_local_storage_item
from thaw_mechanics import run_unranked, unranked_note
from thaw_model import region


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Arctic permafrost holds thousands of years of stored carbon and "
        "methane, and as it thaws that store starts releasing — a "
        "feedback loop where warming causes more warming. But real "
        "climate scientists describe it as a dimmer switch, not an "
        "on/off switch: every bit of avoided warming keeps more "
        "permafrost frozen. That framing is the backbone of Thaw's whole "
        "design."
    ),
    "mechanic_tie_in": (
        "Thaw's tipping-point moment is grounded in real observed "
        "evidence of accelerating Arctic methane emissions, not a purely "
        "speculative mechanic."
    ),
    "sources": [
        {
            "label": "MIT Climate Portal — Is methane release from the Arctic unstoppable?",
            "url": "https://climate.mit.edu/ask-mit/methane-release-arctic-unstoppable",
            "note": "The clearest source for Thaw's hope angle — frames the feedback loop as a dimmer switch, not an on/off switch.",
        },
        {
            "label": "Nature Climate Change — Seasonal increase of methane emissions linked to warming in Siberian tundra",
            "url": "https://www.nature.com/articles/s41558-022-01512-4",
            "note": "Real observational evidence (not just modeling) of the feedback loop already measurably happening.",
        },
        {
            "label": "WWF Arctic — Thawing permafrost",
            "url": "https://www.arcticwwf.org/the-circle/stories/thawing-permafrost/",
            "note": "An accessible explainer connecting permafrost thaw to real Arctic communities' lived experience.",
        },
        {
            "label": "PMC/NCBI — 21st-century modeled permafrost carbon emissions accelerated by abrupt thaw beneath lakes",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6093858/",
            "note": "A more technical source on abrupt (not just gradual) thaw mechanisms, tying to Thaw's tipping-point moment.",
        },
    ],
}


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, runstate.info_page_open)


# ===========================================================================
# K16 (planning/TODO.md "What's New" changelog, site-wide goal): a small
# in-game "what's new" panel, same shape as the achievements catalog above
# -- a flat JSON list fetched into the Pyodide boot sequence and handed to
# Python as a window global (see index.html), rendered into a
# hidden-until-opened panel. Unlike achievements.json this catalog isn't a
# set of checkable conditions -- it's just curated highlight text -- so
# there's no earned/unearned state, only a newest-first list.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as _read_achievements_json(): the boot script
    fetches changelog.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off disk,
    keeping the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no changelog" rather than crashing this module's whole
# import -- same defensive shape as ACHIEVEMENTS above, since a "what's
# new" panel is additive, not core to Thaw's gameplay.
try:
    CHANGELOG = sorted(json.loads(_read_changelog_json()), key=lambda entry: entry["date"], reverse=True)
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if runstate.changelog_open else f"\U0001f4cb What's New ({len(CHANGELOG)})"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    if not CHANGELOG:
        empty = document.createElement("p")
        empty.innerText = "Nothing logged yet."
        panel.appendChild(empty)
        return

    for entry in CHANGELOG:
        row = document.createElement("div")
        row.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-entry-date"
        date.innerText = entry["date"]
        row.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-entry-text"
        text.innerText = entry["entry"]
        row.appendChild(text)

        panel.appendChild(row)


# ===========================================================================
# G11 -- community "average acceleration factor" comparison
# (planning/TODO.md, needs Z1). Follows Grid's C15 architecture exactly
# (games/grid/game.py/index.html): a Python-side optional JS hook call,
# guarded so it's a safe no-op outside a real browser (the pytest fake-DOM
# harness's `js` module never provides `window` by default), and the real
# fetch()/percentile-phrasing lives entirely in index.html's own inline
# <script>. Region A only -- this game's Pass 3 note already scoped the
# primary intervention lever to Region A, not the B/C comparison regions
# or D's auto-played worst case, and that same scoping applies here.
#
# "region.average_acceleration_factor" is registered in app/stats.py's
# per-game STATS_FIELDS whitelist for "thaw" (added alongside this
# feature), so GET /stats/games/thaw/percentile?field=region.average_
# acceleration_factor is live once the backend is deployed with it.
# ===========================================================================
COMMUNITY_COMPARE_FALLBACK = "Community comparison isn't available yet."


def update_community_compare_panel():
    toggle = document.getElementById("community-compare-toggle-button")
    panel = document.getElementById("community-compare-panel")
    toggle.innerText = (
        "Hide Community Comparison" if runstate.community_compare_open else "\U0001F30D Community Comparison"
    )
    panel.hidden = not runstate.community_compare_open
    if not runstate.community_compare_open:
        return
    if run_unranked():  # FY-32: custom rules never reach the shared percentile
        panel.innerHTML = (
            f'<p id="community-compare-display" class="comparison-message">{_escape(unranked_note())}</p>'
            + compare_history_html()
        )
        return
    panel.innerHTML = (
        f'<p id="community-compare-display" class="comparison-message">{COMMUNITY_COMPARE_FALLBACK}</p>'
        + compare_history_html()  # G-30
    )
    _request_community_comparison()


def _request_community_comparison():
    """G11: asks the page's optional JS hook (window.thawCompare, see
    index.html) to fill #community-compare-display with a cross-player
    percentile of average_acceleration_factor. Absent hook (pytest, or a
    page without it) leaves the fallback text in place -- mirrors Grid's
    _request_comparison() exactly."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "thawCompare", None)
    if hook is not None:
        hook(float(region.average_acceleration_factor))


# G7: an optional "deeper data view" -- real published atmospheric methane
# data shown ALONGSIDE the in-game graph, not overlaid onto it (Thaw's
# rounds have no real calendar-time axis to align against a real dataset
# without implying false precision). Source: NOAA Global Monitoring
# Laboratory, "Trends in Atmospheric Methane (CH4)"
# (https://gml.noaa.gov/ccgg/trends_ch4/, accessed 2026-09-26, page's own
# "Last updated: Sep 05, 2026") -- the real annual increase in globally-
# averaged atmospheric methane, continuously measured since 1983. This is
# the TOTAL real-world growth rate (agriculture, wetlands, fossil-fuel
# leaks, and permafrost all contribute); it is not a permafrost-only
# figure, and the panel says so plainly rather than implying a 1:1 match
# with this game's own feedback-loop mechanic.
REAL_METHANE_GROWTH_PPB_PER_YEAR = [
    (1984, 12.89), (1985, 12.18), (1986, 12.90), (1987, 11.43), (1988, 10.74),
    (1989, 11.12), (1990, 8.71), (1991, 13.99), (1992, 2.43), (1993, 3.85),
    (1994, 7.30), (1995, 3.82), (1996, 2.47), (1997, 6.36), (1998, 12.13),
    (1999, 2.25), (2000, -1.34), (2001, -0.66), (2002, 3.17), (2003, 4.84),
    (2004, -4.72), (2005, 0.21), (2006, 1.85), (2007, 7.85), (2008, 6.52),
    (2009, 4.77), (2010, 5.03), (2011, 5.02), (2012, 5.01), (2013, 5.70),
    (2014, 12.69), (2015, 10.03), (2016, 7.13), (2017, 6.83), (2018, 8.72),
    (2019, 9.64), (2020, 14.78), (2021, 17.70), (2022, 13.01), (2023, 8.32),
    (2024, 7.91), (2025, 5.14),
]

CLIMATE_SCIENTIST_SOURCE_URL = "https://gml.noaa.gov/ccgg/trends_ch4/"
CLIMATE_SCIENTIST_FRAMING = (
    "Real-world atmospheric methane has been measured continuously since 1983 "
    "(NOAA's Global Monitoring Laboratory). The chart below is the real annual "
    "growth rate — how much the global average rose that year, in parts "
    "per billion. This is the TOTAL real-world increase from every source "
    "combined (agriculture, wetlands, fossil-fuel leaks, and permafrost thaw "
    "all contribute) — it is not a permafrost-only figure, and Thaw's own "
    "feedback-loop mechanic is a simplified stand-in for one piece of this "
    "larger, real picture, not a literal model of it. Notice the recent run: "
    "2020-2022 saw the three highest annual increases on record."
)

METHANE_CHART_WIDTH = 320
METHANE_CHART_HEIGHT = 90
METHANE_CHART_BASELINE_YEARS = 30  # 1984-2013, before the recent acceleration


def real_methane_growth_chart_svg():
    """A labeled real-data line chart -- deliberately a bigger, more
    legible sibling of mini_temp_graph_svg above (this one is meant to be
    read, not just glanced at for shape): year tick labels plus a dashed
    reference line at the pre-acceleration baseline average, so the
    recent run reads clearly against its own real historical range."""
    years = [y for y, _ in REAL_METHANE_GROWTH_PPB_PER_YEAR]
    values = [v for _, v in REAL_METHANE_GROWTH_PPB_PER_YEAR]
    n = len(values)
    lo, hi = min(values), max(values)
    span = hi - lo if hi - lo > 1e-9 else 1.0
    pad_top, pad_bottom = 10, 16
    plot_h = METHANE_CHART_HEIGHT - pad_top - pad_bottom
    xs = [i * (METHANE_CHART_WIDTH / (n - 1)) for i in range(n)]
    ys = [pad_top + plot_h - ((v - lo) / span) * plot_h for v in values]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))

    baseline = sum(values[:METHANE_CHART_BASELINE_YEARS]) / METHANE_CHART_BASELINE_YEARS
    baseline_y = pad_top + plot_h - ((baseline - lo) / span) * plot_h

    # The first/last ticks sit right at the SVG's own edges, so a centered
    # anchor there would clip half the label outside the viewBox -- anchor
    # those two to their own inside edge instead, interior ticks stay
    # centered on their point.
    tick_indices = sorted({0, 10, 20, 30, n - 1})
    ticks = []
    for i in tick_indices:
        if i == 0:
            anchor = "start"
        elif i == n - 1:
            anchor = "end"
        else:
            anchor = "middle"
        ticks.append(
            f'<text x="{xs[i]:.1f}" y="{METHANE_CHART_HEIGHT - 2}" '
            f'style="text-anchor:{anchor}" class="methane-chart-tick">{years[i]}</text>'
        )
    ticks = "".join(ticks)

    return (
        f'<svg viewBox="0 0 {METHANE_CHART_WIDTH} {METHANE_CHART_HEIGHT}" class="methane-chart-svg" '
        f'role="img" aria-label="Real annual growth in atmospheric methane, '
        f'1984 to 2025, in parts per billion per year">'
        f'<line x1="0" y1="{baseline_y:.1f}" x2="{METHANE_CHART_WIDTH}" y2="{baseline_y:.1f}" '
        f'class="methane-chart-baseline" />'
        f'<text x="2" y="{max(baseline_y - 2, 9):.1f}" class="methane-chart-baseline-label">'
        f"1984–2013 average</text>"
        f'<polyline points="{points}" class="methane-chart-line" />'
        f"{ticks}"
        f"</svg>"
    )


def render_climate_scientist():
    toggle = document.getElementById("climate-scientist-toggle-button")
    panel = document.getElementById("climate-scientist-panel")
    toggle.innerText = (
        "Hide Climate Scientist" if runstate.climate_scientist_open else "\U0001F52C Climate Scientist"
    )
    panel.hidden = not runstate.climate_scientist_open
    if not runstate.climate_scientist_open:
        return
    panel.innerHTML = (
        f'<p class="climate-scientist-framing">{CLIMATE_SCIENTIST_FRAMING}</p>'
        f"{real_methane_growth_chart_svg()}"
        f'<p class="climate-scientist-source">Source: '
        f'<a href="{CLIMATE_SCIENTIST_SOURCE_URL}" target="_blank" rel="noopener">'
        f"NOAA Global Monitoring Laboratory, Trends in Atmospheric Methane</a>.</p>"
    )


# ===========================================================================
# G-30: the last five community comparisons. Each time the Community Comparison panel gets a real
# percentile back (the page script calls record_compare_result), it is kept as one line in a short
# list in localStorage so a player can see how their standing moved over time. Per-browser, not saved.
# ===========================================================================
COMPARE_HISTORY_KEY = "thaw_compare_history_v1"
COMPARE_HISTORY_MAX = 5


def _clean_compare_entry(raw):
    if not isinstance(raw, dict):
        return None
    rnd, better, count, factor = raw.get("round"), raw.get("better_than"), raw.get("count"), raw.get("factor")
    ok = (
        _num(rnd, 1, 1000000) and int(rnd) == rnd
        and _num(better, 0, 100) and int(better) == better
        and _num(count, 1, 100000000) and int(count) == count
        and _num(factor, 0, 10000)
    )
    if not ok:
        return None
    return {"round": int(rnd), "better_than": int(better), "count": int(count), "factor": round(float(factor), 2)}


def load_compare_history():
    raw = _read_local_storage_item(COMPARE_HISTORY_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    entries = [e for e in (_clean_compare_entry(item) for item in data) if e is not None]
    return entries[-COMPARE_HISTORY_MAX:]


compare_history = load_compare_history()


def record_compare_result(better_than, count):
    """Keeps one comparison result (called by the page script after a successful percentile lookup).
    `better_than` is the percent of other saved regions whose warming accelerated MORE than Region A's.
    A repeat of the same round/percent/count is ignored; only the newest five stay."""
    entry = _clean_compare_entry({
        "round": region.round_number, "better_than": better_than, "count": count,
        "factor": region.average_acceleration_factor,
    })
    if entry is None:
        return False
    if compare_history and (
        (compare_history[-1]["round"], compare_history[-1]["better_than"], compare_history[-1]["count"])
        == (entry["round"], entry["better_than"], entry["count"])
    ):
        return False
    compare_history.append(entry)
    del compare_history[:-COMPARE_HISTORY_MAX]
    _write_local_storage_item(COMPARE_HISTORY_KEY, json.dumps(compare_history))
    if runstate.community_compare_open:
        update_community_compare_panel()
    return True


def compare_history_html():
    if not compare_history:
        return '<p class="comparison-message">Your last five comparisons will be listed here.</p>'
    rows = "".join(
        f"<li>Round {e['round']}: accelerated less than {e['better_than']}% of {e['count']} other saved "
        f"regions (average {e['factor']:.2f}x)</li>"
        for e in reversed(compare_history)
    )
    head = f'<p class="comparison-message">Your last {len(compare_history)} comparison(s), newest first:</p>'
    return head + f'<ol class="compare-history">{rows}</ol>'
