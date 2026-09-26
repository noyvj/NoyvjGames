"""H25b/H29b: the opt-in rich SVG trade network and circular supply chain
map (planning/TODO.md, Per-game: Loop). The simple text/emoji versions (H25a/
H29a) stay the default; the visual views are a per-browser toggle that reads
only real ChainState numbers."""

import re
import sys
import types
import xml.etree.ElementTree as ET
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _ns(tag):
    return "{http://www.w3.org/2000/svg}" + tag


def _parse(markup):
    """The map markup must be well-formed XML (an unescaped label or a stray
    tag would render a broken SVG in a real browser)."""
    return ET.fromstring(f"<root>{markup}</root>")


def _stroke_widths(root, kind):
    out = []
    for g in root.iter(_ns("g")):
        if f"rf--{kind}" in g.get("class", "").split():
            for p in g.iter(_ns("path")):
                if p.get("class") == "rf-base":
                    out.append(float(p.get("stroke-width")))
    return out


def _flows(root):
    return [g for g in root.iter(_ns("g")) if "rich-flow" in g.get("class", "").split()]


def _nodes(root):
    return [g for g in root.iter(_ns("g")) if "rich-node" in g.get("class", "").split()]


def _bought(game_env):
    game_env.chain.funds = 5000
    for _ in range(2):
        game_env.invest_circularity("recycle")
    game_env.invest_circularity("reuse")
    game_env.invest_circularity("repair")
    for _ in range(2):
        game_env.invest_trade_link()
    game_env.invest_regional_trade()
    game_env.invest_overseas_trade()


def _install_hook(store, supported=True):
    hook = types.SimpleNamespace(
        supported=lambda: supported,
        get=lambda key: store.get(key),
        set=lambda key, value: store.__setitem__(key, value),
    )
    sys.modules["js"].window = types.SimpleNamespace(loopVisual=hook)


# --- default: simple stays the default --------------------------------------

def test_visual_views_are_off_by_default(game_env):
    for name in ("trade", "supply"):
        assert game_env.elements[f"{name}-visual"].hidden is True
        assert game_env.elements[f"{name}-visual-body"].innerHTML == ""
        assert game_env.elements[f"{name}-visual-toggle-button"].attributes["aria-pressed"] == "false"
    # The simple versions keep being rendered regardless.
    assert "Extract -> Manufacture" in game_env.elements["network-map-display"].innerText
    assert "Importing" in game_env.elements["trade-network-display"].innerText


def test_toggle_buttons_are_labelled_show_when_off(game_env):
    assert "Show visual network view" in game_env.elements["trade-visual-toggle-button"].innerText
    assert "Show visual supply chain view" in game_env.elements["supply-visual-toggle-button"].innerText


# --- toggling ----------------------------------------------------------------

def test_toggle_on_renders_svg_and_marks_pressed(game_env):
    game_env.elements["trade-visual-toggle-button"].dispatch("click", None)
    panel = game_env.elements["trade-visual"]
    assert panel.hidden is False
    assert "<svg" in game_env.elements["trade-visual-body"].innerHTML
    assert game_env.elements["trade-visual-toggle-button"].attributes["aria-pressed"] == "true"
    assert "Hide visual network view" in game_env.elements["trade-visual-toggle-button"].innerText
    assert game_env.elements["trade-network"].classList.contains("rich-trade-on")
    # The other view is untouched.
    assert game_env.elements["supply-visual"].hidden is True


def test_toggle_off_again_empties_the_panel(game_env):
    button = game_env.elements["supply-visual-toggle-button"]
    button.dispatch("click", None)
    assert "<svg" in game_env.elements["supply-visual-body"].innerHTML
    assert game_env.elements["network-map-panel"].classList.contains("rich-chain-on")
    button.dispatch("click", None)
    assert game_env.elements["supply-visual"].hidden is True
    assert game_env.elements["supply-visual-body"].innerHTML == ""
    assert not game_env.elements["network-map-panel"].classList.contains("rich-chain-on")


def test_visual_view_follows_state_changes(game_env):
    game_env.elements["trade-visual-toggle-button"].dispatch("click", None)
    before = game_env.elements["trade-visual-body"].innerHTML
    game_env.chain.funds = 500
    game_env.invest_trade_link()
    after = game_env.elements["trade-visual-body"].innerHTML
    assert before != after
    assert "Trade Link: 1 owned, importing 4 units per cycle" in after


def test_visual_toggle_does_not_touch_game_state_or_save(game_env):
    module = game_env.module
    state_before = module.get_state()
    game_env.elements["trade-visual-toggle-button"].dispatch("click", None)
    game_env.elements["supply-visual-toggle-button"].dispatch("click", None)
    assert module.get_state() == state_before
    assert "visual" not in str(module.get_state()).lower()


# --- real numbers -------------------------------------------------------------

def test_trade_map_shows_real_partner_units(game_env):
    _bought(game_env)
    module = game_env.module
    markup = module.trade_network_visual_html()
    root = _parse(markup)
    tips = " ".join(g.get("data-tip") for g in _flows(root) + _nodes(root))
    assert "Trade Link: 2 owned, importing 8 units per cycle" in tips
    assert "Regional Partner: 1 owned, importing 6 units per cycle" in tips
    assert "Overseas Consortium: 1 owned, importing 15 units per cycle" in tips
    assert f"{game_env.chain.internal_circular_supply():.0f} units per cycle" in tips
    # The partner flows sum to exactly the chain's real imported supply.
    assert sum(row[4] for row in module.trade_partner_flows()) == game_env.chain.imported_supply()


def test_flow_thickness_is_proportional_to_units(game_env):
    _bought(game_env)
    root = _parse(game_env.module.trade_network_visual_html())
    widths = sorted(_stroke_widths(root, "trade"))
    # 6 (regional) < 8 (link) < 15 (overseas): thicker for more units.
    assert widths[0] < widths[1] < widths[2]
    # And the stroke is an affine function of units over the largest flow.
    scale = max(game_env.chain.material_need(), 29, 17)
    expected = sorted(3.0 + 25.0 * u / scale for u in (6, 8, 15))
    for got, want in zip(widths, expected):
        assert abs(got - want) < 0.11


def test_node_size_grows_with_units(game_env):
    _bought(game_env)
    root = _parse(game_env.module.trade_network_visual_html())
    radii = {}
    for node in _nodes(root):
        tip = node.get("data-tip")
        circle = next(node.iter(_ns("circle")))
        radii[tip.split(":")[0]] = float(circle.get("r"))
    assert radii["Overseas Consortium"] > radii["Trade Link"] > radii["Regional Partner"]


def test_zero_state_renders_idle_flows_without_motion_or_nan(game_env):
    module = game_env.module
    for markup in (module.trade_network_visual_html(), module.supply_map_visual_html()):
        assert "nan" not in markup.lower()
        root = _parse(markup)
        idle = [g for g in _flows(root) if "rf--idle" in g.get("class", "").split()]
        assert idle
        for g in idle:
            assert not [p for p in g.iter(_ns("path")) if p.get("class") == "rf-dash"]
            assert not list(g.iter(_ns("polygon")))


def test_active_flows_carry_direction_overlay_and_arrowhead(game_env):
    _bought(game_env)
    root = _parse(game_env.module.supply_map_visual_html())
    active = [g for g in _flows(root) if "rf--idle" not in g.get("class", "").split()]
    assert len(active) >= 6
    for g in active:
        assert [p for p in g.iter(_ns("path")) if p.get("class") == "rf-dash"]
        assert list(g.iter(_ns("polygon")))


def test_supply_map_return_lanes_match_each_measure(game_env):
    _bought(game_env)
    module = game_env.module
    root = _parse(module.supply_map_visual_html())
    tips = {g.get("data-tip") for g in _flows(root)}
    for key, label, icon, owned, units in module.internal_measure_flows():
        assert any(t.startswith(f"{label}: {owned} owned, returning {units:.0f} units") for t in tips)
    assert abs(sum(r[4] for r in module.internal_measure_flows()) - game_env.chain.internal_circular_supply()) < 1e-9
    stage_tips = " ".join(n.get("data-tip") for n in _nodes(root))
    assert "Extract:" in stage_tips and "Manufacture:" in stage_tips
    assert "Use:" in stage_tips and "Discard:" in stage_tips


def test_focus_multipliers_and_challenge_mode_are_reflected(game_env):
    module = game_env.module
    game_env.chain.funds = 1000
    game_env.invest_circularity("recycle")
    game_env.chain.set_waste_focus("recycle")
    rows = {r[0]: r[4] for r in module.internal_measure_flows()}
    assert rows["recycle"] == 5.0 * 1.25
    game_env.chain.set_challenge_mode(True)
    assert "65%" in module.trade_network_visual_html()
    rows = {r[0]: r[4] for r in module.internal_measure_flows()}
    assert abs(rows["recycle"] - 5.0 * 1.25 * 0.65) < 1e-9


def test_culture_campaign_changes_the_needed_units(game_env):
    game_env.chain.funds = 1000
    game_env.chain.invest_culture()
    assert "needs 48" in game_env.module.trade_network_visual_html()


# --- accessibility / markup ---------------------------------------------------

def test_every_node_and_flow_is_focusable_and_labelled(game_env):
    _bought(game_env)
    module = game_env.module
    for markup in (module.trade_network_visual_html(), module.supply_map_visual_html()):
        root = _parse(markup)
        hits = [g for g in root.iter(_ns("g")) if "rich-hit" in g.get("class", "").split()]
        assert len(hits) >= 6
        for g in hits:
            assert g.get("tabindex") == "0"
            assert g.get("role") == "img"
            assert len(g.get("aria-label")) > 10
            assert g.get("data-tip") == g.get("aria-label")
        svg = next(root.iter(_ns("svg")))
        assert svg.get("role") == "group"
        assert "units per cycle" in svg.get("aria-label")
        assert svg.get("viewBox")


def test_legend_and_reduced_motion_note_are_present(game_env):
    module = game_env.module
    trade = module.trade_network_visual_html()
    chain_map = module.supply_map_visual_html()
    for markup in (trade, chain_map):
        assert 'class="rich-legend"' in markup
        assert "reduced motion" in markup
    assert "Repair returning to Manufacture" in chain_map
    assert "Imported from a trade partner" in trade


def test_labels_are_escaped(game_env):
    module = game_env.module
    assert module._esc('<b onclick="x">&') == "&lt;b onclick=&quot;x&quot;&gt;&amp;"


# --- preference storage and fallback -------------------------------------------

def test_choice_is_saved_through_the_page_hook(game_env):
    store = {}
    _install_hook(store)
    game_env.elements["trade-visual-toggle-button"].dispatch("click", None)
    assert store["loop-visual-trade"] == "1"
    game_env.elements["trade-visual-toggle-button"].dispatch("click", None)
    assert store["loop-visual-trade"] == "0"


def test_saved_choice_is_restored_on_load(game_env):
    module = game_env.module
    _install_hook({"loop-visual-trade": "1", "loop-visual-chain": "0"})
    module._load_visual_prefs()
    module.render()
    assert game_env.elements["trade-visual"].hidden is False
    assert "<svg" in game_env.elements["trade-visual-body"].innerHTML
    assert game_env.elements["supply-visual"].hidden is True


def test_unsupported_svg_keeps_simple_version_with_visible_note(game_env):
    _install_hook({}, supported=False)
    game_env.elements["trade-visual-toggle-button"].dispatch("click", None)
    assert game_env.elements["trade-visual"].hidden is False  # panel (with its note) shows
    assert game_env.elements["trade-visual-unsupported"].hidden is False
    assert game_env.elements["trade-visual-body"].innerHTML == ""
    assert not game_env.elements["trade-network"].classList.contains("rich-trade-on")
    assert "Importing" in game_env.elements["trade-network-display"].innerText


def test_broken_hook_never_breaks_the_game(game_env):
    def boom(*_args):
        raise RuntimeError("storage blocked")

    sys.modules["js"].window = types.SimpleNamespace(
        loopVisual=types.SimpleNamespace(supported=lambda: True, get=boom, set=boom)
    )
    game_env.module._load_visual_prefs()
    game_env.elements["supply-visual-toggle-button"].dispatch("click", None)
    assert "<svg" in game_env.elements["supply-visual-body"].innerHTML


# --- static page wiring ---------------------------------------------------------

def test_index_html_ships_the_toggles_notes_and_script():
    page = (GAME_DIR / "index.html").read_text()
    for element_id in (
        "trade-visual-toggle-button", "trade-visual", "trade-visual-body", "trade-visual-unsupported",
        "supply-visual-toggle-button", "supply-visual", "supply-visual-body", "supply-visual-unsupported",
    ):
        assert f'id="{element_id}"' in page
    assert page.count("rich-map-note--narrow") == 2
    assert "900px" in page
    assert '<script src="rich-maps.js"></script>' in page
    assert page.count('aria-pressed="false"') >= 2


def test_stylesheet_has_breakpoint_reduced_motion_and_light_theme():
    css = (GAME_DIR / "style.css").read_text()
    assert "@media (min-width: 900px)" in css and "@media (max-width: 899px)" in css
    assert 'html[data-reduced-motion="true"] .rich-flow .rf-dash' in css
    assert re.search(r"prefers-reduced-motion: reduce\) \{\s*\.rich-flow \.rf-dash", css)
    assert 'html[data-theme="light"] .rich-map-panel' in css
    assert "@keyframes rich-flow-move" in css


def test_rich_maps_js_wraps_storage_in_try_catch():
    js = (GAME_DIR / "rich-maps.js").read_text()
    assert "window.loopVisual" in js
    assert js.count("try {") >= 3 and js.count("catch (e)") >= 3
    assert "createSVGRect" in js
