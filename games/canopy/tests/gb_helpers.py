"""Shared helpers for the GB batch 1 tests (golden seedling, Tend, Heart Tree,
names, undo, rare wildlife, tiers, weather, chain bloom, Almanac, Perfect
Season)."""


def make_mature(m, index, state=None):
    """Sets a main-forest plot to a fully mature standing plot."""
    plot = m.plots[index]
    plot.state = state or m.PRESERVED
    plot.ticks_intact = m.MATURITY_TICKS
    plot.value = 100.0
    plot.mature_celebrated = False
    return plot


def ring_around(m, centre):
    """Indices of the 8 plots around `centre` on the current grid."""
    return m._neighbour_indices(centre)


def tile(env, index):
    return env.elements[f"plot-{index}"]


def tile_marks(env, index):
    return [child.className for child in tile(env, index).children]


def toast_text(env):
    return env.elements["achievement-toast"].innerText


def log_kinds(m):
    return [entry["kind"] for entry in m.forest_log]


def decline_requests(env, index, times):
    """Raises `times` clear requests aimed at `index` and declines each."""
    m = env.module
    for _ in range(times):
        m.pending_stakeholder_request = {"plot_index": index, "reason": "housing", "kind": "clear"}
        env.decline_stakeholder()


def advance_to(env, target_tick):
    """Ticks the game until forest_tick == target_tick."""
    while env.module.forest_tick < target_tick:
        env.tick()


class FakeChangeEvent:
    def __init__(self, value):
        self.target = type("T", (), {"value": value})()
