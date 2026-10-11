"""Round-7 pass: the supply-against-demand needle gauge (GC-28)."""
from .test_career import _play
from .test_round7_trend import _tick


def test_empty_grid_pins_the_needle_left_in_the_short_zone(game_env):
    g = game_env.module
    game_env.module.render()
    reading = g.gauge_reading()
    assert reading["zone"] == "short" and reading["angle"] == -90
    assert game_env.elements["needle-gauge-needle"].style.transform == "rotate(-90.0deg)"
    assert "short (0% of demand), so revenue is capped" in game_env.elements["needle-gauge-caption"].innerText


def test_matched_zone_reads_with_a_tick(game_env):
    g = game_env.module
    game_env.state.plant_counts["nuclear"] = 1  # exactly demand 100
    g.render()
    reading = g.gauge_reading()
    assert reading["zone"] == "matched" and abs(reading["angle"] - 30) < 1e-9
    assert game_env.elements["needle-gauge-caption"].innerText.startswith("✓ ")
    assert "matched (100% of demand)" in game_env.elements["needle-gauge-caption"].innerText
    assert game_env.elements["needle-gauge"].classList.contains("needle-gauge--matched")
    assert not game_env.elements["needle-gauge"].classList.contains("needle-gauge--short")


def test_spare_capacity_and_the_end_stop(game_env):
    g = game_env.module
    game_env.state.plant_counts["nuclear"] = 3
    assert g.gauge_reading()["zone"] == "spare"
    assert g.gauge_reading()["angle"] == 90  # clamped at 1.5 times demand


def test_needle_angle_grows_with_coverage(game_env):
    g = game_env.module
    angles = []
    for count in (0, 2, 4, 5, 6):
        game_env.state.plant_counts["coal"] = count  # 20 each
        angles.append(g.gauge_reading()["angle"])
    assert angles == sorted(angles) and len(set(angles)) == 5


def test_a_brownout_round_cuts_the_reading_and_says_so(game_env):
    g = game_env.module
    game_env.state.plant_counts["nuclear"] = 1
    game_env.state.last_event = {"type": "brownout", "severity": 0.5, "revenue_loss": 10}
    reading = g.gauge_reading()
    assert reading["cut"] is True and reading["zone"] == "short" and reading["ratio"] < 1.0
    g.render()
    assert "a disruption cut delivery" in game_env.elements["needle-gauge-caption"].innerText
    assert game_env.elements["needle-gauge"].classList.contains("needle-gauge--cut")
    game_env.state.last_event = None
    g.render()
    assert not game_env.elements["needle-gauge"].classList.contains("needle-gauge--cut")


def test_effects_checkbox_marks_the_gauge_still(game_env):
    g = game_env.module
    g.render()
    assert not game_env.elements["needle-gauge"].classList.contains("needle-gauge--still")
    _tick(game_env, "pref-gauge-effects", False)
    assert game_env.elements["needle-gauge"].classList.contains("needle-gauge--still")
    assert g.prefs["gauge_effects"] is False
    _tick(game_env, "pref-gauge-effects", True)
    assert not game_env.elements["needle-gauge"].classList.contains("needle-gauge--still")


def test_gauge_uses_the_chosen_number_format(game_env):
    g = game_env.module
    g.prefs["number_format"] = "compact"
    game_env.state.plant_counts["nuclear"] = 15
    game_env.state.demand = 1200
    assert "Supply 1.5k against demand 1.2k" in g.gauge_text(g.gauge_reading())


def test_gauge_follows_play_and_never_touches_the_save(game_env):
    g = game_env.module
    game_env.state.plant_counts["coal"] = 6
    _play(game_env, 3)
    before = g.get_state()
    g.render()
    assert g.get_state() == before and "needle" not in " ".join(before)
    assert game_env.elements["needle-gauge-graphic"].title == game_env.elements["needle-gauge-caption"].innerText.lstrip("✓ ")
