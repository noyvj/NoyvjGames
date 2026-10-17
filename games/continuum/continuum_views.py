"""The City Views panel (dashboard, map, flow) and the civic insights/challenges render."""

from js import document
from pyodide.ffi import create_proxy

import challenges
import explain
import geography
import heritage
import naming
import statlog
import techdebt
import trajectory
import views

import continuum_runstate as runstate
from continuum_base import _geo_seed, _resting, current_effects, year_and_season
from continuum_extras import _extra_dashboard_sections
from continuum_founders import format_play_time, play_seconds, settlement_name
from continuum_peers import render_peers
from continuum_techdebt import _debt_hazard

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# ===========================================================================
# K2/K8/K10/K21a small readouts, K11 civic challenges, K19/K13/K25 charts.
# All read-only views of state (challenge start/abandon aside), all inside
# collapsed panels or single status lines -- nothing here adds a screen.
# ===========================================================================


# ===========================================================================
# K1/K24/K28: the optional City Views panel (dashboard, civic map, flow
# diagram). Session-only display state, never saved; built by views.py.
# ===========================================================================
VIEW_TABS = ("dashboard", "map", "flow")


def on_toggle_views(event=None):
    runstate.views_panel_open = not runstate.views_panel_open
    update_views_panel(current_effects())


def _make_views_tab_handler(tab):
    def handler(event=None):
        runstate.views_tab = tab
        update_views_panel(current_effects())
    return handler


def update_views_panel(effects=None):
    toggle = document.getElementById("views-toggle-button")
    panel = document.getElementById("views-panel")
    toggle.innerText = "Hide City Views" if runstate.views_panel_open else "📊 City Views"
    panel.hidden = not runstate.views_panel_open
    if not runstate.views_panel_open:
        return
    effects = current_effects() if effects is None else effects
    for tab in VIEW_TABS:
        document.getElementById(f"views-tab-{tab}-button").setAttribute(
            "aria-pressed", "true" if tab == runstate.views_tab else "false"
        )
        document.getElementById(f"views-{tab}").hidden = tab != runstate.views_tab
    if runstate.views_tab == "dashboard":
        container = document.getElementById("views-dashboard")
        container.innerHTML = ""
        done, total, _percent = tree_completion()
        # K-27/K-16: sparklines, deltas and the "why did that change" hover
        # come from the per-season stat history. A Look Back shows a past
        # snapshot, which that history does not describe, so they are left out.
        history = statlog.rows(runstate.campaign.ui) if runstate.campaign.revisiting is None else []
        container.className = "views-dashboard views-dashboard--spark" if history else "views-dashboard"
        sections = views.dashboard(
            runstate.state, effects, (done, total), techdebt.get(runstate.campaign.ui) if runstate.campaign.revisiting is None else None
        )
        if runstate.campaign.revisiting is None:
            sections = sections + _extra_dashboard_sections()
        for section in sections:
            block = document.createElement("div")
            block.className = "views-dash-section"
            heading = document.createElement("h3")
            heading.className = "summary-eras-heading"
            heading.innerText = section["title"]
            block.appendChild(heading)
            for label, value in section["rows"]:
                block.appendChild(_dashboard_row(label, value, history, effects))
            container.appendChild(block)
    elif runstate.views_tab == "map":
        hazard = _debt_hazard()
        sites = [] if _resting() else heritage.sites_before(runstate.state.era, runstate.campaign.ui)
        document.getElementById("views-map-svg").innerHTML = views.civic_map_svg(runstate.state, hazard, sites) + geography.map_svg(
            geography.generate(_geo_seed())
        )
        document.getElementById("views-map-caption").innerText = views.map_caption(runstate.state, hazard)
    else:
        document.getElementById("views-flow-svg").innerHTML = views.flow_svg(runstate.state, runstate.state.last_report)
        document.getElementById("views-flow-caption").innerText = views.flow_caption(runstate.state.last_report)


def _dashboard_row(label, value, history, effects):
    """One dashboard row: label, K-27 sparkline, value, K-16 delta + hover waterfall."""
    row = document.createElement("p")
    row.className = "views-dash-row"
    name = document.createElement("span")
    name.className = "views-dash-name"
    name.innerText = label
    row.appendChild(name)
    key = views.spark_key(label)
    if key and history:
        kind_format = lambda v: statlog.format_value(key, v)  # noqa: E731
        svg = views.sparkline_svg(statlog.series(history, key, views.SPARK_SEASONS), label, kind_format)
        if svg:
            spark = document.createElement("span")
            spark.className = "views-dash-spark"
            spark.innerHTML = svg
            row.appendChild(spark)
    number = document.createElement("span")
    number.className = "views-dash-value"
    number.innerText = value
    row.appendChild(number)
    if key and len(history) >= 2:
        change = explain.delta(history, key)
        if change is not None:
            delta_text = statlog.format_delta(key, change)
            chip = document.createElement("span")
            chip.className = "views-dash-delta"
            chip.innerText = delta_text
            chip.setAttribute("title", "Change over the last completed season")
            row.appendChild(chip)
            explained = explain.explain(key, history, runstate.state.last_report, effects)
            if explained is not None and explained["factors"]:
                row.className = "views-dash-row views-dash-row--why"
                row.setAttribute("tabindex", "0")
                row.setAttribute("role", "group")
                row.setAttribute(
                    "aria-label",
                    f"{label}: {value}. Last season {delta_text}. Why: " + "; ".join(explain.waterfall_lines(explained)),
                )
                row.appendChild(_why_popover(explained))
    return row


def _why_popover(explained):
    """The K-16 small waterfall: a signed line and a floating bar per factor."""
    pop = document.createElement("span")
    pop.className = "why-pop"
    pop.setAttribute("role", "tooltip")
    title = document.createElement("span")
    title.className = "why-title"
    title.innerText = f"Why {explained['label'].lower()} changed last season"
    pop.appendChild(title)
    for step in explain.waterfall_geometry(explained):
        line = document.createElement("span")
        line.className = "why-line why-line--net" if step["kind"] == "net" else "why-line"
        text = document.createElement("span")
        text.className = "why-name"
        text.innerText = step["label"]
        track = document.createElement("span")
        track.className = "why-track"
        bar = document.createElement("span")
        bar.className = f"why-bar why-bar--{step['kind']}"
        bar.style.left = f"{step['left']}%"
        bar.style.width = f"{step['width']}%"
        track.appendChild(bar)
        amount = document.createElement("span")
        amount.className = "why-amount"
        amount.innerText = explain.amount_text(step["amount"], explained["unit"])
        line.appendChild(text)
        line.appendChild(track)
        line.appendChild(amount)
        pop.appendChild(line)
    return pop


def tree_completion():
    """K21a: (researched, total, percent) over the whole tree."""
    total = len(runstate.tree.nodes)
    done = len(runstate.tree.researched)
    return done, total, (100 * done // total if total else 0)


_challenge_button_proxies = {}


def _make_start_challenge_handler(cid):
    def handler(event=None):
        if runstate.campaign.revisiting is not None:
            return
        if challenges.start(runstate.state, current_effects(), cid):
            render()
    return handler


def on_abandon_challenge(event=None):
    if challenges.abandon(runstate.state):
        render()


def render_insights(effects):
    year, season_name = year_and_season(runstate.state.season)
    document.getElementById("founded-display").innerText = naming.with_name(
        settlement_name(), f"Founded Year 1 · now Year {year}, {season_name}"
    )
    index = trajectory.current_output_index(runstate.state)
    document.getElementById("efficiency-display").innerText = (
        "Output per person: -" if index is None else f"Output per person: {index:.1f}x subsistence"
    )
    document.getElementById("calm-streak-display").innerText = (
        f"Calm seasons in a row: {runstate.state.calm_streak}"
    )
    document.getElementById("play-time-display").innerText = f"Time played: {format_play_time(play_seconds())}"
    done, total, percent = tree_completion()
    document.getElementById("research-completion-display").innerText = (
        f"Tree: {done} of {total} discoveries ({percent}%)"
    )

    # --- K11 civic challenges -------------------------------------------
    active_line = challenges.status_text(runstate.state)
    document.getElementById("challenges-summary").innerText = (
        "Civic Challenges (1 active)" if active_line else "Civic Challenges (optional)"
    )
    status = document.getElementById("challenge-status-display")
    status.innerText = active_line or f"Challenges met: {challenges.total_completed(runstate.state)}"
    container = document.getElementById("challenge-list")
    container.innerHTML = ""
    live = set()
    if active_line:
        row = document.createElement("div")
        row.className = "row challenge-row"
        button = document.createElement("button")
        button.id = "challenge-abandon-button"
        button.className = "secondary"
        button.innerText = "Abandon challenge"
        proxy = create_proxy(on_abandon_challenge)
        stale = _challenge_button_proxies.get("abandon")
        if stale is not None:
            stale.destroy()
        _challenge_button_proxies["abandon"] = proxy
        live.add("abandon")
        button.addEventListener("click", proxy)
        row.appendChild(button)
        container.appendChild(row)
    elif runstate.campaign.revisiting is None:
        for cid in challenges.offered(runstate.state, effects):
            spec = challenges.CHALLENGES[cid]
            row = document.createElement("div")
            row.className = "row challenge-row"
            top = document.createElement("div")
            top.className = "row-top"
            name = document.createElement("span")
            name.className = "row-name"
            name.innerText = f"{spec['label']} ({spec['seasons']} seasons)"
            top.appendChild(name)
            row.appendChild(top)
            blurb = document.createElement("p")
            blurb.className = "row-blurb"
            blurb.innerText = (
                f"{spec['blurb']} Reward: +{challenges.reward_for(runstate.state.era):.0f} knowledge."
            )
            row.appendChild(blurb)
            actions = document.createElement("div")
            actions.className = "row-actions"
            button = document.createElement("button")
            button.id = f"challenge-start-{cid}-button"
            button.className = "secondary"
            button.innerText = "Accept"
            proxy = create_proxy(_make_start_challenge_handler(cid))
            stale = _challenge_button_proxies.get(cid)
            if stale is not None:
                stale.destroy()
            _challenge_button_proxies[cid] = proxy
            live.add(cid)
            button.addEventListener("click", proxy)
            actions.appendChild(button)
            row.appendChild(actions)
            container.appendChild(row)
    for key in list(_challenge_button_proxies):
        if key not in live:
            _challenge_button_proxies.pop(key).destroy()

    # --- K19/K13/K25 charts ---------------------------------------------
    points = runstate.state.trajectory
    document.getElementById("trajectory-graph").innerHTML = trajectory.trajectory_svg(points)
    document.getElementById("livability-scatter").innerHTML = trajectory.scatter_svg(points)
    document.getElementById("trajectory-summary").innerText = trajectory.summary_line(points)
    document.getElementById("trajectory-source").innerText = trajectory.SOURCE_NOTE
    render_peers()
