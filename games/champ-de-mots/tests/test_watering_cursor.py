"""L24 -- a static watering-can cursor while a plot is open for watering."""

from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def test_farm_gets_the_watering_class_only_while_a_plot_is_open(game_env):
    module = game_env.module
    farm = game_env.elements["farm"]
    assert not farm.classList.contains("farm--watering")
    plot = game_env.state.plots[0]
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    assert farm.classList.contains("farm--watering")
    module.close_practice()
    assert not farm.classList.contains("farm--watering")


def test_the_cursor_is_a_static_svg_rule_with_a_pointer_fallback_and_no_motion():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    rule = css[css.index(".farm--watering .plot:not(:disabled)"):]
    rule = rule[: rule.index("}")]
    assert 'cursor: url("data:image/svg+xml,' in rule and ", pointer" in rule
    assert "animation" not in rule and "transition" not in rule
