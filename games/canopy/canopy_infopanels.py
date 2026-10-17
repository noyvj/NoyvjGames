"""The What's New changelog, the example playthrough and The Real Story info page."""

import json

import info_page
from js import document

import canopy_runstate as runstate
from canopy_rules import (
    BASE_ACCRUAL, DEGRADE_PER_CLEAR, GROWTH_PER_TICK, MATURITY_TICKS, MIN_PRODUCTIVITY_MULTIPLIER,
    RECOVERY_TICKS,
)


# ===========================================================================
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)
# ===========================================================================
# Same static-JSON-asset loading contract as ACHIEVEMENTS above (and SOL's
# reference integration): the boot script fetches changelog.json and hands
# it to Python as a window global before this module runs; the pytest
# harness's fake `js` has no such attribute, so this falls through to
# reading the file straight off disk. A flat, hand-written list of
# highlights pulled from this game's own CLAUDE.md milestone table and
# build notes — not a full duplicate of the dev logs, just a quick
# "what's new" view.
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CHANGELOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Same defensive posture as ACHIEVEMENTS above: the changelog is additive,
# not core to gameplay, so any loading failure degrades to "no changelog"
# instead of crashing the whole module import.
try:
    CHANGELOG = json.loads(_read_changelog_json())["changelog"]
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide What's New" if runstate.changelog_open else "\U0001F4CB What's New"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    # changelog.json is authored newest-first already, so no re-sort needed
    # here — same "trust the JSON's own order" posture ACHIEVEMENTS takes.
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
# B29: a guided, narrated example of a strong preserve/clear balance. Every
# number is computed from the game's own constants by `example_playthrough()`
# (never hand-typed), using the base rules only (no seasons, legacy, grants or
# specializations), so it stays correct if a constant is retuned. It compares
# three ways of running the same 10 plots over the same 120 ticks.
# ===========================================================================
EXAMPLE_PLOTS = 10
EXAMPLE_TICKS = 120
EXAMPLE_HARVESTED_PLOTS = 2


def _example_growth(ticks, clear_count=0):
    """Value a plot gains over `ticks` accruing ticks at a given soil quality."""
    productivity = max(MIN_PRODUCTIVITY_MULTIPLIER, 1 - DEGRADE_PER_CLEAR * clear_count)
    return sum(BASE_ACCRUAL * productivity * (1 + t * GROWTH_PER_TICK) for t in range(1, ticks + 1))


def _example_clearing_plot_total(period, horizon):
    """One plot cleared and replanted the moment it has accrued `period` ticks."""
    total, clock, clears = 0.0, 0, 0
    while clock + period <= horizon:
        total += _example_growth(period, clears)
        clock += period + RECOVERY_TICKS
        clears += 1
    accruing_left = max(0, horizon - clock)
    return total + _example_growth(accruing_left, clears), clears


def example_playthrough():
    """The narrated steps: a list of (title, text)."""
    patient_plot = _example_growth(EXAMPLE_TICKS)
    quick_plot, quick_clears = _example_clearing_plot_total(MATURITY_TICKS // 6, EXAMPLE_TICKS)
    kept = EXAMPLE_PLOTS - EXAMPLE_HARVESTED_PLOTS
    harvest_at = MATURITY_TICKS
    harvested_plot, _ = _example_clearing_plot_total(harvest_at, EXAMPLE_TICKS)
    balanced = kept * patient_plot + EXAMPLE_HARVESTED_PLOTS * harvested_plot
    quick_all = EXAMPLE_PLOTS * quick_plot
    never_clear = EXAMPLE_PLOTS * patient_plot
    return [
        (
            "1. Patience compounds",
            f"A plot left standing earns more each tick than the tick before: after 10 ticks it holds "
            f"{_example_growth(10):.0f}, after {MATURITY_TICKS} it holds {_example_growth(MATURITY_TICKS):.0f}, "
            f"after {EXAMPLE_TICKS} it holds {patient_plot:.0f}. Value grows faster than time, so the last "
            f"stretch of waiting is the best-paid.",
        ),
        (
            "2. Clearing is expensive",
            f"Clearing cashes a plot out, but it then sits bare and replanting for {RECOVERY_TICKS} ticks "
            f"earning nothing, and its soil permanently loses {DEGRADE_PER_CLEAR * 100:.0f}% productivity "
            f"per clear (never below {MIN_PRODUCTIVITY_MULTIPLIER * 100:.0f}%), and its wildlife is gone.",
        ),
        (
            "3. Clearing early backfires",
            f"Clearing every plot every {MATURITY_TICKS // 6} ticks makes {quick_clears} clears per plot and "
            f"totals about {quick_all:.0f} across {EXAMPLE_PLOTS} plots over {EXAMPLE_TICKS} ticks, "
            f"far less than not clearing at all ({never_clear:.0f}).",
        ),
        (
            "4. The balanced run",
            f"Keep {kept} plots standing the whole time and harvest just {EXAMPLE_HARVESTED_PLOTS} once each "
            f"they reach maturity (about tick {harvest_at}), then replant. That totals about {balanced:.0f}: "
            f"nearly all the value of never clearing, with cash in hand at the midpoint to spend on "
            f"community requests and specializations, and most of the forest still growing.",
        ),
        (
            "5. What to copy",
            "Preserve most plots, harvest a few at maturity rather than early, replant straight away, and "
            "spend the cash on the things that reward a standing forest. Clear the same plot repeatedly and "
            "its soil, not the market, becomes the limit.",
        ),
    ]


def on_toggle_example(event=None):
    runstate.example_open = not runstate.example_open
    update_example_display()


def update_example_display():
    toggle = document.getElementById("example-toggle-button")
    panel = document.getElementById("example-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide example playthrough" if runstate.example_open else "\U0001F4D6 Example playthrough"
    panel.hidden = not runstate.example_open
    if not runstate.example_open:
        return
    panel.innerHTML = ""
    intro = document.createElement("p")
    intro.className = "example-intro"
    intro.innerText = (
        f"A guided example of a strong preserve/clear balance: {EXAMPLE_PLOTS} plots over "
        f"{EXAMPLE_TICKS} ticks, base rules only (no seasons or bonuses). Numbers are worked out from "
        f"the game's own settings."
    )
    panel.appendChild(intro)
    for title, text in example_playthrough():
        row = document.createElement("div")
        row.className = "example-step"
        heading = document.createElement("p")
        heading.className = "example-step-title"
        heading.innerText = title
        row.appendChild(heading)
        body = document.createElement("p")
        body.className = "example-step-text"
        body.innerText = text
        row.appendChild(body)
        panel.appendChild(row)


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Standing forests are one of the world's largest active carbon "
        "sinks, and clearing them for quick income is one of the largest "
        "reversible sources of emissions — reversible because forests "
        "left alone, or given light assistance, can recover. Canopy's "
        "core tension, clear it now or let it compound, is a simplified "
        "stand-in for that real land-use tradeoff."
    ),
    "mechanic_tie_in": (
        "Canopy's replant-and-recover path loosely echoes real \"assisted "
        "natural regeneration\" — a genuinely cost-effective restoration "
        "approach, rather than costly full replanting from scratch."
    ),
    "sources": [
        {
            "label": "World Resources Institute — Forests in the IPCC Special Report on Land Use: 7 Things to Know",
            "url": "https://www.wri.org/insights/forests-ipcc-special-report-land-use-7-things-know",
            "note": "Explains why deforestation and forest carbon sinks are two sides of the same coin — maps directly to Canopy's clear/preserve tension.",
        },
        {
            "label": "World Resources Institute — How Effective Is Land At Removing Carbon Pollution? The IPCC Weighs In",
            "url": "https://www.wri.org/insights/how-effective-land-removing-carbon-pollution-ipcc-weighs",
            "note": "Real reforestation carbon-removal potential — grounds the \"replanting works, just slower\" hope angle in actual IPCC figures.",
        },
        {
            "label": "UNFCCC — Land Use, Land-Use Change and Forestry (LULUCF)",
            "url": "https://unfccc.int/topics/land-use/workstreams/land-use--land-use-change-and-forestry-lulucf",
            "note": "The formal policy framework for tracking forest carbon sinks internationally — why Canopy treats plots as carbon-relevant assets, not scenery.",
        },
        {
            "label": "Climate Change Resources — Deforestation & Reforestation",
            "url": "https://climatechangeresources.org/learn-more/science/reforestation-deforestation/",
            "note": "Accessible overview with links to real reforestation organizations, for players who want to go from facts to action.",
        },
    ],
}


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, runstate.info_page_open)


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()
