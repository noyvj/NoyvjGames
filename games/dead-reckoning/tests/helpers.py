"""Small builders shared by the tests."""


def whole_sea_current(set_deg, drift, **extra):
    zone = {"id": "z", "rect": [-100, -100, 100, 100], "set": set_deg, "drift_range": [drift, drift],
            "true_set": set_deg, "true_drift": drift}
    zone.update(extra)
    return zone
