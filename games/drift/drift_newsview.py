"""The local news line, the trend graph panel, and the tab title."""

from js import document

import drift_runstate as runstate
from drift_messages import _simulate_control_region
from drift_model_region import region
from drift_trendgraph import (
    TREND_LAYER_DEFAULT, TREND_LAYER_ORDER, TREND_RANGES, trend_events, trend_graph_svg, trend_legend_text,
)
from drift_visuals import _set_pressed


# ---- GI-20: the optional town-news ticker -----------------------------------------------------------------
# One warm line of local news under the region name, off by default (Settings > Town news, a per-browser
# display preference handled by settings.js). The humour is about institutions and small civic things
# (benches, timetables, biscuits), never about the people who arrive. The headline is a pure function of the
# region's state, so it is deterministic and never random.
NEWS_HEADLINES = {
    "stable": [
        "Council spends six hours debating where the new bench should go; the bench is, by all accounts, lovely.",
        "Library extends its evening hours; the reading room now needs a second kettle.",
        "Bus route 4 gets a timetable that matches the buses. Residents are cautiously delighted.",
        "Community garden waiting list shortens as volunteers dig two more beds.",
        "Market stall holders agree on a shared awning after only three meetings.",
        "School choir adds a verse in a fifth language; the concert is already sold out.",
        "Planning office reports its first-ever empty inbox, then refills it with coffee.",
        "Town hall repaints the noticeboard; the lost-umbrella shelf is declared a historic collection.",
        "New crossing painted outside the clinic; the zebra is, inevitably, praised.",
        "A street party grows to three streets and one very large pot of soup.",
        "The bakery's sign now says fresh in four languages and still warm in six.",
        "Parks team plants forty trees and, as agreed, names none of them.",
    ],
    "strained": [
        "Council extends clinic hours as demand grows; extra chairs ordered for the waiting room.",
        "Language classes fill up; the library lends its quiet room for the overflow.",
        "Housing office adds a Saturday shift and a second stapler.",
        "Volunteers stack chairs, sort donations and invent a surprisingly efficient queue-and-tea system.",
        "Transit authority adds two evening buses and promises to look at the timetable again.",
        "Town hall corridor gets a map; residents call it the best-kept secret in local government.",
        "Neighbourhood association holds an open evening on how to find the right office first time.",
        "Teachers share lesson plans across schools; the staff room runs out of biscuits, then restocks.",
        "Mayor thanks everyone who has lent a spare table this week.",
        "Council funds a second interpreter desk after residents asked for one. Applause is minuted.",
    ],
    "critical": [
        "Emergency meeting runs late; every seat taken, every offer of help written down.",
        "Services stretched but holding: clinics, schools and volunteers sharing space this week.",
        "Council asks for patience and promises a plan by Friday; neighbours bring dinner to the planning office.",
        "The sports hall opens as a temporary hub; a rota of helpers keeps the lights on.",
        "Agencies meet daily to match housing, classes and jobs; progress is posted on the door.",
        "Mutual-aid network doubles its volunteers; coordinators say the hard part is the shift handover.",
        "Funding appeal launched; the first donation is a box of folding tables.",
        "Engineers inspect the stretched water mains and schedule repairs ahead of winter.",
    ],
}
NEWS_NET_POSITIVE = "Finance office reports that integration is now paying for itself; the treasurer is seen smiling at a spreadsheet."
NEWS_THRIVING = "The region is named a good place to start again; the committee is mostly proud of the bus timetable."
NEWS_SECOND_WAVE = "Halls open and rotas fill as the region prepares for a larger arrival; the kettle count is up."


def news_headline(region_state):
    """The headline for the region's current round: a milestone line the round after one happens, the
    second-wave line while it runs, otherwise the pool for the strain level, one line per round in turn."""
    last_done = region_state.round_number - 1
    if region_state.net_positive_round is not None and region_state.net_positive_round == last_done:
        return NEWS_NET_POSITIVE
    if region_state.thriving_round is not None and region_state.thriving_round == last_done:
        return NEWS_THRIVING
    if region_state.second_wave_status in ("warned", "active"):
        return NEWS_SECOND_WAVE
    pool = NEWS_HEADLINES.get(region_state.strain_level(), NEWS_HEADLINES["stable"])
    return pool[(region_state.round_number - 1) % len(pool)]


# ---- I-24: live tab title ----------------------------------------------------
trend_layers = dict(TREND_LAYER_DEFAULT)


def render_trend_graph():
    control_wellbeing = None
    if region.round_number > 2:
        control_wellbeing = _simulate_control_region(
            region.round_number, region.accelerated_severity_enabled, region.calendar_enabled
        ).wellbeing_log
    trend_svg = trend_graph_svg(
        region.strain_log, region.wellbeing_log, control_wellbeing,
        first_round=region.round_number - len(region.strain_log),
        layers=trend_layers,
        events=trend_events(region) if trend_layers["events"] else [],
        roi_history=region.roi_log,
        view_rounds=TREND_RANGES[runstate.trend_range],
    )
    document.getElementById("trend-graph").innerHTML = trend_svg
    document.getElementById("trend-graph-message").innerText = (
        "" if trend_svg else "Not enough rounds yet to show a trend."
    )
    document.getElementById("trend-legend").innerText = trend_legend_text(trend_layers)
    for key in TREND_RANGES:
        button = document.getElementById(f"trend-range-{key}-button")
        _set_pressed(button, key == runstate.trend_range)
    for key in TREND_LAYER_ORDER:
        _set_pressed(document.getElementById(f"trend-layer-{key}-button"), trend_layers[key])


def tab_title():
    name = f" - {region.region_name}" if region.region_name else ""
    return f"Drift - R{region.round_number} - {region.strain_level().capitalize()}{name}"
