"""Dead Reckoning -- the engine's single entry point (the Lexis / Signal pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes
back. `get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md).
Milestone 2 only knows how to draw the demo chart with a hard-coded plan.
"""

import json

import render
import sim
from charts import DEMO_CHART

DEMO_PLAN = [{"heading": 20, "speed": 5.0, "hours": 2.5}, {"heading": 62, "speed": 5.0, "hours": 2.0}]


def _demo_view():
    chart = DEMO_CHART
    legs = sim.clean_legs(chart, DEMO_PLAN)
    est = sim.estimate(chart, legs, allow=True)
    return {"phase": "plan", "chart": {"id": chart["id"], "name": chart["name"]},
            "svg": render.render_chart(chart, est=est, marks=render.plan_marks(legs, est)),
            "notes": render.chart_notes(chart)}


def handle(request_json):
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    if action in ("open", None):
        return json.dumps(_demo_view())
    return json.dumps({"error": "unknown action %r" % (action,)})


def get_state():
    return {"schema": 1}


def load_state(data):
    return None
