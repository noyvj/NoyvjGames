"""Round-4 readouts (2026-10-11): phone HUD round and band (I-22), sub-score sparklines (I-26),
pending-by-age pipeline (I-23)."""

from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _advance(game_env, rounds):
    for _ in range(rounds):
        game_env.advance_round()


# --- I-22: HUD ----------------------------------------------------------------

def test_hud_sources_carry_the_round_and_the_band(game_env):
    game_env.module.render()
    assert game_env.elements["hud-round-display"].innerText == "R1 💰 300"
    assert game_env.elements["hud-strain-display"].innerText == "0% stable"
    text = game_env.elements["hud-wellbeing-display"].innerText
    assert text.split()[0].isdigit() and text.split()[-1] in ("Struggling", "Managing", "Thriving", "Region")
    _advance(game_env, 3)
    assert game_env.elements["hud-round-display"].innerText.startswith("R4 💰 ")


def test_hud_band_name_changes_with_the_score(game_env):
    region = game_env.region
    region.funds = 5000.0  # economic health 100
    region.total_arrivals = 10.0
    region.integrated_population = 10.0  # cohesion 100
    game_env.module.render()
    assert game_env.elements["hud-wellbeing-display"].innerText.endswith("Model Region")


def test_the_page_mirrors_those_two_sources_in_the_sticky_bar():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert '{ selector: "#hud-round-display", label: "" }' in html
    assert '{ selector: "#hud-strain-display", label: "Strain" }' in html
    assert '{ selector: "#hud-wellbeing-display", label: "Wellbeing" }' in html
    for hud_id in ("hud-round-display", "hud-strain-display", "hud-wellbeing-display"):
        assert f'id="{hud_id}" hidden' in html


# --- I-26: sparklines ---------------------------------------------------------

def test_no_sparkline_before_two_rounds(game_env):
    assert game_env.module.sparkline_svg([]) == ""
    assert game_env.module.sparkline_svg([50.0]) == ""


def test_sparkline_keeps_only_the_last_twenty_rounds(game_env):
    svg = game_env.module.sparkline_svg(list(range(50)))
    points = svg.split('points="')[1].split('"')[0].split()
    assert len(points) == 20


def test_sparkline_uses_the_fixed_zero_to_hundred_scale(game_env):
    svg = game_env.module.sparkline_svg([0, 100])
    low, high = (p.split(",") for p in svg.split('points="')[1].split('"')[0].split())
    assert float(low[1]) > float(high[1])  # 0 draws lower than 100
    flat = game_env.module.sparkline_svg([50, 50, 50])
    ys = {p.split(",")[1] for p in flat.split('points="')[1].split('"')[0].split()}
    assert len(ys) == 1


def test_sparkline_clamps_out_of_range_values(game_env):
    svg = game_env.module.sparkline_svg([-50, 500])
    for point in svg.split('points="')[1].split('"')[0].split():
        assert 0 <= float(point.split(",")[1]) <= game_env.module.SPARKLINE_HEIGHT


def test_each_gauge_gets_a_sparkline_after_two_rounds(game_env):
    game_env.module.render()
    assert game_env.elements["service-quality-spark"].innerHTML == ""
    _advance(game_env, 3)
    for spark in ("service-quality-spark", "economic-health-spark", "social-cohesion-spark"):
        assert "<polyline" in game_env.elements[spark].innerHTML


def test_sparkline_survives_a_malformed_log_entry(game_env):
    game_env.region.subscore_log = [{"service": 40}, "junk", {"service": 60}]
    assert "<polyline" in game_env.module.subscore_sparkline(game_env.region.subscore_log, "service")


# --- I-23: pending pipeline ---------------------------------------------------

def test_bands_sum_to_the_pending_population(game_env):
    region = game_env.region
    region.arrivals_log = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    region.total_arrivals = 60.0
    region.integrated_population = 12.0
    bands = game_env.module.pending_age_bands(region)
    assert abs(sum(bands.values()) - region.pending_population()) < 1e-9


def test_the_newest_arrivals_are_the_ones_still_waiting(game_env):
    region = game_env.region
    region.arrivals_log = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    region.total_arrivals = 60.0
    region.integrated_population = 40.0  # 20 pending: the last two rounds
    bands = game_env.module.pending_age_bands(region)
    assert bands == {"new": 10.0, "recent": 10.0, "old": 0.0}


def test_a_deep_backlog_lands_in_the_oldest_band(game_env):
    region = game_env.region
    region.arrivals_log = [5.0] * 8
    region.total_arrivals = 40.0
    region.integrated_population = 0.0
    bands = game_env.module.pending_age_bands(region)
    assert bands["new"] == 5.0 and bands["recent"] == 10.0 and bands["old"] == 25.0


def test_a_crisis_start_backlog_counts_as_old(game_env):
    game_env.region.set_crisis_start(True)
    bands = game_env.module.pending_age_bands(game_env.region)
    assert bands["old"] == game_env.module.CRISIS_START_ARRIVALS and bands["new"] == 0.0


def test_no_log_and_no_pending_gives_zero_bands(game_env):
    assert game_env.module.pending_age_bands(game_env.region) == {"new": 0.0, "recent": 0.0, "old": 0.0}
    assert game_env.module.pending_pipeline_text({"new": 0.0, "recent": 0.0, "old": 0.0}) == "Nobody is waiting for integration."


def test_render_draws_proportional_segments_and_a_text_equivalent(game_env):
    region = game_env.region
    region.arrivals_log = [10.0] * 5
    region.total_arrivals = 50.0
    region.integrated_population = 10.0  # 40 pending: 10 new, 20 recent, 10 old
    game_env.module.render()
    assert game_env.elements["pending-pipeline"].hidden is False
    assert game_env.elements["pending-band-new"].style.width == "25.0%"
    assert game_env.elements["pending-band-recent"].style.width == "50.0%"
    assert game_env.elements["pending-band-old"].style.width == "25.0%"
    text = game_env.elements["pending-pipeline-text"].innerText
    assert "10 from the latest round" in text and "20 who have waited 2 to 3" in text and "10 who have waited 4 or more" in text


def test_the_bar_hides_when_nobody_waits(game_env):
    game_env.module.render()
    assert game_env.elements["pending-pipeline"].hidden is True
    assert "Nobody" in game_env.elements["pending-pipeline-text"].innerText


def test_readouts_add_nothing_to_the_save(game_env):
    game_env.advance_round()
    state = game_env.module.get_state()
    assert not [k for k in state if "pending_band" in k or "spark" in k or k.startswith("hud")]
