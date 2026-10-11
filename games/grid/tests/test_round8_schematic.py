"""Round-8 pass: the single-line schematic (C-11)."""
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
STYLE = (GAME_DIR / "style.css").read_text()


def _widths(svg):
    return [float(m) for m in re.findall(r'stroke-width="([\d.]+)" stroke-dasharray="6 4"', svg)]


def test_empty_grid_has_no_generators_and_says_so(game_env):
    g = game_env.module
    g.render()
    svg = game_env.elements["schematic-graphic"].innerHTML
    assert "<svg" in svg and "sch-flow" not in svg
    assert "Nothing is generating yet" in game_env.elements["schematic-caption"].innerText
    assert "No battery storage yet" in game_env.elements["schematic-caption"].innerText
    assert "SHORT by 100" in svg


def test_every_standing_generator_gets_a_box_and_a_flow(game_env):
    g = game_env.module
    game_env.state.plant_counts.update({"coal": 2, "solar": 3, "wind": 1})
    rows = g.schematic_rows()
    assert [r[0] for r in rows] == ["coal", "solar", "wind"]
    svg = g.schematic_svg()
    assert "Coal x2" in svg and "Solar x3" in svg and "Wind x1" in svg and "Gas x" not in svg
    assert svg.count("sch-flow") == 4  # three generators plus the bus-to-demand line


def test_flow_thickness_follows_what_each_plant_delivers(game_env):
    g = game_env.module
    game_env.state.plant_counts.update({"coal": 4, "wind": 1})
    rows = dict((t, d) for t, _n, d in g.schematic_rows())
    assert rows["coal"] > rows["wind"]
    assert abs(sum(rows.values()) - min(game_env.state.total_capacity(), game_env.state.demand)) < 1e-6  # delivered never exceeds demand
    widths = _widths(g.schematic_svg())
    assert widths[0] > widths[1]
    assert all(g.SCHEMATIC_MIN_FLOW <= wd <= g.SCHEMATIC_MAX_FLOW for wd in widths)
    # a surplus does not make a flow thicker than the demand allows
    game_env.state.plant_counts["coal"] = 40
    assert max(_widths(g.schematic_svg())) <= g.SCHEMATIC_MAX_FLOW


def test_demand_block_says_met_or_short_in_words(game_env):
    g = game_env.module
    game_env.state.plant_counts["coal"] = 3
    assert "SHORT by 40" in g.schematic_svg() and "short by 40" in g.schematic_caption()
    game_env.state.plant_counts["coal"] = 6
    svg = g.schematic_svg()
    assert ">MET<" in svg and "SHORT" not in svg and "fully supplied" in g.schematic_caption()


def test_battery_tank_fills_with_stored_energy(game_env):
    g = game_env.module
    game_env.state.plant_counts.update({"coal": 6, "battery": 2})
    game_env.state.stored_energy = 0.0
    empty = g.schematic_svg()
    assert "0 of" in empty
    game_env.state.stored_energy = game_env.state.storage_cap() / 2
    half = g.schematic_svg()
    assert half != empty and 'fill="#4fa8dd" />' in half
    assert f"{game_env.state.stored_energy:.0f} of {game_env.state.storage_cap():.0f}" in half
    game_env.state.plant_counts["battery"] = 0
    assert "none built" in g.schematic_svg()


def test_picture_is_self_contained_for_the_image_export(game_env):
    g = game_env.module
    game_env.state.plant_counts.update({"solar": 2, "gas": 1})
    svg = g.schematic_svg()
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert "class=" in svg and "style=" not in svg  # colours and widths are attributes, not the page style sheet
    for cls in set(re.findall(r'class="([^"]+)"', svg)):
        assert cls in ("schematic-svg", "sch-flow")
    assert 'role="img"' in svg and "<title>" in svg
    assert "Solar 2 units delivering" in svg  # the words are inside the picture's own label


def test_it_follows_the_game_and_is_not_saved(game_env):
    g = game_env.module
    game_env.state.plant_counts["coal"] = 2
    game_env.advance_round()
    assert "Round 2" in game_env.elements["schematic-graphic"].innerHTML
    assert "schematic" not in " ".join(g.get_state().keys())


def test_flow_animation_is_page_only_and_off_under_reduced_motion():
    assert ".sch-flow { animation: sch-dash 0.8s linear 4; }" in STYLE
    assert "@media (prefers-reduced-motion: reduce) { .sch-flow { animation: none; } }" in STYLE
    assert 'html[data-reduced-motion="true"] .sch-flow { animation: none; }' in STYLE


def test_save_button_and_its_script_exist_on_both_pages():
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text()
        assert 'id="schematic-save-button"' in html and "grid-schematic.png" in html and 'id="schematic-panel"' in html
