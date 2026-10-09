"""Station Medic -- helpers the chapter files use to write shifts compactly."""


def P(crew, truth, say, traits=""):
    """A patient: a crew id, the true condition id(s), what they say on arrival, and any chart-note ids."""
    return {"crew": crew, "truth": truth, "say": say, "traits": traits}


def S(sid, title, intro, pool, stock, patients, tests="", beds=0, robots=0, maxc=1):
    """A shift. `stock` is a dict of shelf id to count; the scans and treatments in play follow from it and `tests`."""
    return {"id": sid, "title": title, "intro": intro, "pool": pool, "stock": stock, "patients": patients,
            "tests": tests, "beds": beds, "robots": robots, "maxc": maxc}
