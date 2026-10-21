from .pagefiles import page_text
import json


def test_line_loss_standard(game_env):
    result = game_env.module.line_loss(110, 500, 100)
    assert result["sent_mw"] == 55.0
    assert result["loss_mw"] == 1.25
    assert round(result["percent"], 2) == 2.27


def test_line_loss_low_voltage(game_env):
    result = game_env.module.line_loss(11, 500, 100)
    assert round(result["percent"], 1) == 22.7


def test_line_loss_high_voltage(game_env):
    result = game_env.module.line_loss(220, 500, 100)
    assert round(result["percent"], 2) == 1.14


def test_line_loss_zero_distance(game_env):
    result = game_env.module.line_loss(110, 500, 0)
    assert result["percent"] == 0.0


def test_line_loss_zero_voltage(game_env):
    result = game_env.module.line_loss(0, 500, 100)
    assert result == {"sent_mw": 0.0, "loss_mw": 0.0, "percent": 0.0}


def test_bench_markup_in_page():
    text = page_text("index.html")
    for id_ in ("bench-panel", "bench-voltage", "bench-current", "bench-distance", "bench-readout"):
        assert f'id="{id_}"' in text, f"Missing element id={id_} in index.html"


def test_bench_panel_in_pc_zones():
    from pathlib import Path
    pc_config_path = Path(__file__).resolve().parent.parent / "pc-config.json"
    with open(pc_config_path) as f:
        config = json.load(f)
    side_ids = config["zones"]["side"]
    assert "#bench-panel" in side_ids, "Missing #bench-panel in pc-config.json zones.side"


def test_bench_text_session():
    from grid_views import BENCH_SESSION, bench_text

    # Reset session to ensure deterministic results
    BENCH_SESSION["tries"] = 0
    BENCH_SESSION["best"] = None

    res1 = bench_text(110, 500, 100)
    assert res1 == (
        "Sending 55.0 MW at 110 kV and 500 A over 100 km loses 1.25 MW (2.3%) as heat. "
        "Settings tried: 1. Lowest loss found: 2.3%. Lower loss needs a higher voltage, less current or a shorter line."
    )

    res2 = bench_text(11, 500, 100)
    assert "(22.7%)" in res2
    assert "Settings tried: 2." in res2
    assert "Lowest loss found: 2.3%." in res2

    # Clean up after test to avoid polluting other tests
    BENCH_SESSION["tries"] = 0
    BENCH_SESSION["best"] = None
