"""Audit of the Round 4 Herd view ideas (R4-HEPC-3, -4 and R4-HEMO-2, -3, -4, -7, -8).

Part 1 is the engine side of the herd-size slider (fake DOM, no browser). Part 2 pins the wiring of the
page code (every id the scripts look up exists, phone-only rules stay inside the phone media block, the
service worker registration is still there). The real clicks are in test_ai_round4_browser.py."""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
INDEX = (HERE / "index.html").read_text(encoding="utf-8")
PC_HTML = (HERE / "pc.html").read_text(encoding="utf-8")
STYLE = (HERE / "style.css").read_text(encoding="utf-8")
PC_CSS = (HERE / "pc.css").read_text(encoding="utf-8")
APP_JS = (HERE / "app.js").read_text(encoding="utf-8")
PC_JS = (HERE / "pc.js").read_text(encoding="utf-8")


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _slide(env, value):
    env.elements["herd-size-slider"].value = str(value)
    env.elements["herd-size-slider"].dispatch("input", None)


# ---- R4-HEMO-8: the slider's numbers come from the engine, and buying uses the real Grow Herd ----

def test_projection_matches_really_growing_the_herd(game_env):
    module = game_env.module
    units, cost, methane, income = module.herd_slider_plan(4)
    assert units == 4
    funds_before = game_env.farm.funds
    for _ in range(4):
        assert game_env.farm.grow_herd()
    assert funds_before - game_env.farm.funds == cost
    assert game_env.farm.methane_this_round() == methane
    assert game_env.farm.income_breakdown()["total"] == income


def test_projection_never_changes_the_real_farm(game_env):
    farm = game_env.farm
    before = (farm.funds, farm.herd_size, list(farm.lever_log))
    game_env.module.herd_slider_plan(6)
    assert (farm.funds, farm.herd_size, list(farm.lever_log)) == before


def test_slider_range_runs_from_the_herd_now_to_what_the_funds_allow(game_env):
    module = game_env.module
    module.render()
    slider = game_env.elements["herd-size-slider"]
    room = game_env.farm.bulk_plan("herd", "max")[0]
    assert room > 0
    assert (slider.min, slider.max) == ("0", str(room))
    assert slider.disabled is False


def test_moving_the_handle_updates_the_readouts_and_the_buy_button(game_env):
    _slide(game_env, 3)
    farm = game_env.farm
    _units, cost, methane, income = game_env.module.herd_slider_plan(3)
    assert game_env.elements["herd-slider-value"].innerText == "3"
    assert game_env.elements["herd-slider-methane"].innerText == f"Methane per round: 0.00 → {methane:.2f}"
    assert game_env.elements["herd-slider-income"].innerText == f"Income per round: 0.0 → {income:.1f}"
    button = game_env.elements["herd-slider-buy-button"]
    assert button.disabled is False
    assert button.innerText == f"Grow to 3 ({cost:g} funds)"
    assert farm.herd_size == 0  # planning alone buys nothing


def test_buy_button_buys_exactly_the_planned_units(game_env):
    _slide(game_env, 3)
    _units, cost, _m, _i = game_env.module.herd_slider_plan(3)
    funds = game_env.farm.funds
    _click(game_env, "herd-slider-buy-button")
    assert game_env.farm.herd_size == 3
    assert funds - game_env.farm.funds == cost
    assert [entry[1] for entry in game_env.farm.lever_log] == ["herd", "herd", "herd"]
    # after buying, the slider restarts from the new herd and the button is idle again
    assert game_env.elements["herd-size-slider"].min == "3"
    assert game_env.elements["herd-slider-buy-button"].disabled is True


def test_a_handle_value_beyond_the_funds_is_clamped(game_env):
    _slide(game_env, 999)
    room = game_env.farm.bulk_plan("herd", "max")[0]
    assert game_env.elements["herd-size-slider"].value == str(room)
    _click(game_env, "herd-slider-buy-button")
    assert game_env.farm.herd_size == room


def test_junk_slider_value_falls_back_to_the_current_herd(game_env):
    game_env.elements["herd-size-slider"].value = "not a number"
    game_env.module.render_herd_slider()
    assert game_env.elements["herd-size-slider"].value == "0"
    assert game_env.elements["herd-slider-buy-button"].disabled is True


def test_no_room_to_grow_disables_the_slider(game_env):
    game_env.farm.funds = 0
    game_env.module.render()
    assert game_env.elements["herd-size-slider"].disabled is True
    assert game_env.elements["herd-size-slider"].max == game_env.elements["herd-size-slider"].min


def test_the_slider_leaves_the_save_alone(game_env):
    before = game_env.module.get_state()
    _slide(game_env, 5)
    assert game_env.module.get_state() == before


# ---- wiring: every id the page scripts look up exists, and the CSS is scoped ----

def _ids_in(source):
    return set(re.findall(r'getElementById\("([\w-]+)"\)', source)) | set(re.findall(r'text\("([\w-]+)"\)', source))


def test_every_id_app_js_looks_up_exists_on_both_pages():
    ids = _ids_in(APP_JS)
    assert {"mobile-round", "mobile-funds", "mobile-methane", "mobile-strip-label", "methane-thermometer", "calm-barn-toggle", "calm-barn-exit", "calm-barn-word",
            "explain-panel", "explain-methane-button", "pressure-display", "methane-display"} <= ids
    for id_ in ids:
        assert f'id="{id_}"' in INDEX, id_
        assert f'id="{id_}"' in PC_HTML, id_


def test_every_id_pc_js_looks_up_exists_on_the_desktop_page():
    for id_ in ("pasture-visual", "lever-history-filter", "grow-herd-button", "actions", "pasture-herd-count",
                "golden-cow-glider", "pasture-barn"):
        assert f'id="{id_}"' in PC_HTML, id_
    for id_ in ("pasture-visual", "lever-history-filter", "actions"):
        assert f'getElementById("{id_}")' in PC_JS, id_
    # the two Menu windows the right-click menu opens are real composites in pc-config.json
    config = (HERE / "pc-config.json").read_text(encoding="utf-8")
    assert '"id": "pc-collection-panel"' in config and '"id": "pc-baseline-panel"' in config
    assert '"pc-open-pc-collection-panel"' in PC_JS and '"pc-open-pc-baseline-panel"' in PC_JS


def test_lever_history_filter_offers_every_key_the_right_click_menu_uses():
    for key in ("herd", "feed", "caps", "capture", "pivot"):
        assert f'<option value="{key}">' in INDEX


def test_service_worker_registration_is_still_on_the_page():
    assert 'navigator.serviceWorker.register("../../sw.js")' in INDEX
    assert 'navigator.serviceWorker.register("../../sw.js")' in PC_HTML


def test_phone_pieces_are_hidden_by_default_and_switched_on_only_in_the_phone_block():
    base_rule = re.search(r"\.mobile-top-strip, \.methane-thermo[^{]*\{\s*display: none;\s*\}", STYLE)
    assert base_rule, "base rule must hide the phone-only pieces on wide screens"
    block = STYLE[STYLE.index("@media (max-width: 600px) {\n  body, body.has-mobile-hud"):]
    for selector in (".mobile-top-strip {", ".lever-shelf {", ".herd-slider-container {", ".methane-thermo {",
                     "#calm-barn-toggle { display: block;"):
        assert selector in block, selector
    # the lever shelf must not hide the levers on a wide screen (it once did)
    assert not re.search(r"\.lever-shelf\s*\{\s*display:\s*none", STYLE)


def test_calm_barn_keeps_the_advance_button_the_pasture_and_the_announcer():
    for needle in ('id="advance-round-button" class="primary calm-keep"',
                   'id="pasture-visual" class="pasture-visual calm-keep"',
                   'id="calm-barn-word" class="calm-barn-word calm-keep"',
                   'id="calm-barn-exit" class="secondary calm-barn-exit calm-keep"'):
        assert needle in INDEX, needle
    assert "#game.calm-barn-mode > :not(.calm-keep):not(#round-announcer) { display: none !important; }" in STYLE
    assert 'id="round-announcer" class="sr-only" role="status"' in INDEX


def test_calm_barn_motion_is_slower_never_faster_and_off_with_reduced_motion():
    # the base animations the calm barn slows (seconds per loop)
    assert re.search(r"animation: cow-graze 4\.5s", STYLE)
    assert re.search(r"animation: wisp-rise 3\.6s", STYLE)
    assert re.search(r"animation: cloud-drift 40s", STYLE)
    calm = dict(re.findall(r"calm-barn-mode \.pasture-visual-(cow|wisp|cloud) \{ animation-duration: (\d+)s", STYLE))
    assert calm == {"cow": "14", "wisp": "14", "cloud": "160"}
    assert int(calm["cow"]) > 4.5 and int(calm["wisp"]) > 3.6 and int(calm["cloud"]) > 40
    assert 'html[data-reduced-motion="true"] #game.calm-barn-mode .pasture-visual-cow' in STYLE
    assert "@media (prefers-reduced-motion: reduce) {\n    #game.calm-barn-mode .pasture-visual-cow" in STYLE


def test_calm_barn_is_a_per_device_setting_never_in_the_save():
    assert 'var CALM_KEY = "herd-calm-barn"' in APP_JS
    assert "herd-calm-barn" not in (HERE / "game.py").read_text(encoding="utf-8")
    # Settings > Reset to Default leaves the calm barn
    assert "#settings-reset-button" in APP_JS and "storeCalm(false)" in APP_JS


def test_pasture_labels_are_built_by_the_desktop_script_only():
    assert "data-label" not in INDEX and "data-label" not in PC_HTML
    assert "pasture-label" in PC_JS and ".pasture-label" in PC_CSS
    assert ".pasture-label" not in STYLE and "labels-on" not in INDEX
    # no internal planning ids leak into the player-facing text
    assert not re.search(r"\((?:F|GF)-?\d+\)", PC_JS)


def test_the_right_click_menu_belongs_to_the_desktop_page():
    assert 'window.NOYVJ_LAYOUT !== "pc"' in PC_JS
    assert ".lever-context-menu" in PC_CSS and ".lever-context-menu" not in STYLE
    assert "simulated" not in PC_JS  # the first version showed a made-up cost
