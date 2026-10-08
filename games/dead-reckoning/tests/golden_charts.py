"""Two small fixed charts whose SVG markup is pinned by string comparison (tests/golden/*.svg).
Regenerate after an intentional change to render.py with: python3 tools/make_golden.py"""

GOLDEN_A = {
    "id": "golden-a", "name": "Golden Water", "chapter": "open", "size": 10,
    "start": [1.0, 1.0], "dest": [9.0, 9.0], "arrival_radius": 1.0, "deadline": 6.0, "speeds": [3.0, 6.0],
    "land": [], "hazards": [{"id": "rock", "kind": "rock", "name": "Little Rock", "x": 5.0, "y": 5.0, "r": 0.5, "charted": True}],
    "currents": [], "landmarks": [],
}
GOLDEN_A_LEGS = [{"heading": 45, "speed": 5.0, "hours": 1.0}, {"heading": 90, "speed": 5.0, "hours": 1.0}]

GOLDEN_B = {
    "id": "golden-b", "name": "Golden Strait", "chapter": "wind", "size": 10,
    "start": [1.0, 5.0], "dest": [9.0, 5.0], "arrival_radius": 1.0, "deadline": 6.0, "speeds": [3.0, 6.0],
    "land": [{"id": "isle", "name": "Isle", "poly": [[4, 6], [6, 6], [6, 8], [4, 8]]}],
    "hazards": [{"id": "reef", "kind": "reef", "name": "Reef", "x": 5.0, "y": 3.0, "r": 0.8, "charted": True},
                {"id": "shoal", "kind": "shoal", "name": "Shoal", "x": 3.0, "y": 2.0, "r": 0.7, "charted": True},
                {"id": "hidden", "kind": "rock", "name": "Hidden", "x": 7.0, "y": 5.0, "r": 0.4, "charted": False}],
    "currents": [{"id": "z", "rect": [3, 0, 8, 6], "set": 90, "drift_range": [1.0, 2.0], "true_set": 90, "true_drift": 1.5}],
    "wind": {"from": 270, "range": [10, 15], "true": 12},
    "landmarks": [{"id": "lt", "name": "The Light", "kind": "lighthouse", "x": 2.0, "y": 8.0, "visible": 8.0}],
}
GOLDEN_B_LEGS = [{"heading": 80, "speed": 5.0, "hours": 1.5}]


def build():
    """The markup both goldens are made from."""
    from render import plan_marks, render_chart
    from sim import clean_legs, estimate
    out = {}
    for name, chart, legs in (("golden_a", GOLDEN_A, GOLDEN_A_LEGS), ("golden_b", GOLDEN_B, GOLDEN_B_LEGS)):
        legs = clean_legs(chart, legs)
        est = estimate(chart, legs, allow=True)
        out[name] = render_chart(chart, est=est, marks=plan_marks(legs, est), point=(6.0, 6.0))
    return out
