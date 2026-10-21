"""Browser tests for the 3D settlement camera (wheel zoom, right-drag pan, two-finger tap, one-finger orbit).

The scene needs WebGL and Three.js; when headless Chromium has neither, every test skips (a green run can mean
"skipped", so check the skip count). Events are dispatched by hand, the way a mouse or two fingers would send them.
"""
import math

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

from browser_helpers import open_game  # noqa: E402


def scene_ready(page):
    page.wait_for_timeout(3000)
    return page.evaluate("!!(window.ContinuumScene && window.ContinuumScene.ready())")


def wheel(page, delta_y, times=1):
    page.evaluate(
        "([dy, n]) => { const el = document.querySelector('#visual3d-container');"
        " for (let i = 0; i < n; i++) el.dispatchEvent(new WheelEvent('wheel', {deltaY: dy, bubbles: true, cancelable: true})); }",
        [delta_y, times])


def down(page, **kw):
    page.evaluate(
        "(o) => document.querySelector('#visual3d-container').dispatchEvent(new PointerEvent('pointerdown', Object.assign({bubbles: true}, o)))",
        kw)


def on_window(page, kind, **kw):
    page.evaluate("([k, o]) => window.dispatchEvent(new PointerEvent(k, o))", [kind, kw])


def camera(page):
    return page.evaluate("window.ContinuumScene.cameraState()")


def test_the_wheel_zooms_the_camera_and_stops_at_the_limits(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")
        wheel(page, -100)
        assert abs(camera(page)["distance"] - 9.5 / 1.1) < 0.01
        wheel(page, -100, 30)
        assert camera(page)["distance"] == 3.5
        wheel(page, 100, 60)
        assert camera(page)["distance"] == 16
        assert page.errors == []
        browser.close()


def test_a_right_drag_pans_the_camera_and_a_preset_resets_it(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")
        down(page, pointerType="mouse", button=2, pointerId=1, clientX=200, clientY=200)
        on_window(page, "pointermove", pointerType="mouse", pointerId=1, clientX=250, clientY=200)
        on_window(page, "pointerup", pointerType="mouse", pointerId=1)
        s = camera(page)
        k = s["distance"] * 0.0016
        assert abs(s["targetX"] - (-math.cos(s["yaw"]) * 50 * k)) < 1e-6
        assert abs(s["targetZ"] - (math.sin(s["yaw"]) * 50 * k)) < 1e-6
        page.click("#camera-preset-overview-button")
        s = camera(page)
        assert s["targetX"] == 0 and s["targetZ"] == 0
        yaw_before = s["yaw"]
        down(page, pointerType="mouse", button=0, pointerId=2, clientX=200, clientY=200)
        on_window(page, "pointermove", pointerType="mouse", pointerId=2, clientX=250, clientY=200)
        on_window(page, "pointerup", pointerType="mouse", pointerId=2)
        s = camera(page)
        assert s["targetX"] == 0 and s["targetZ"] == 0
        assert s["yaw"] != yaw_before
        assert page.errors == []
        browser.close()


def test_a_two_finger_tap_returns_to_the_last_preset(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")
        page.click("#camera-preset-closeup-button")
        wheel(page, -100)
        assert camera(page)["distance"] != 5.5
        down(page, pointerType="touch", pointerId=1, clientX=200, clientY=200)
        down(page, pointerType="touch", pointerId=2, clientX=260, clientY=200)
        on_window(page, "pointerup", pointerType="touch", pointerId=2)
        on_window(page, "pointerup", pointerType="touch", pointerId=1)
        s = camera(page)
        assert s["distance"] == 5.5 and s["targetX"] == 0 and s["targetZ"] == 0
        assert abs(s["yaw"] - 0.7) < 1e-9 and abs(s["pitch"] - 0.4) < 1e-9
        assert page.errors == []
        browser.close()


def test_two_fingers_that_move_do_not_reset_the_camera(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")
        page.click("#camera-preset-closeup-button")
        wheel(page, -100)
        zoomed = camera(page)["distance"]
        down(page, pointerType="touch", pointerId=1, clientX=200, clientY=200)
        down(page, pointerType="touch", pointerId=2, clientX=260, clientY=200)
        on_window(page, "pointermove", pointerType="touch", pointerId=1, clientX=240, clientY=200)
        on_window(page, "pointerup", pointerType="touch", pointerId=2)
        on_window(page, "pointerup", pointerType="touch", pointerId=1)
        assert camera(page)["distance"] == zoomed
        assert page.errors == []
        browser.close()


def test_one_finger_still_orbits_and_a_single_tap_changes_nothing(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")
        page.click("#camera-preset-closeup-button")
        wheel(page, -100)
        before = camera(page)
        down(page, pointerType="touch", pointerId=1, clientX=200, clientY=200)
        on_window(page, "pointerup", pointerType="touch", pointerId=1)
        assert camera(page) == before
        down(page, pointerType="touch", pointerId=1, clientX=200, clientY=200)
        on_window(page, "pointermove", pointerType="touch", pointerId=1, clientX=250, clientY=200)
        on_window(page, "pointerup", pointerType="touch", pointerId=1)
        after = camera(page)
        assert after["yaw"] != before["yaw"]
        assert after["distance"] == before["distance"]
        assert page.errors == []
        browser.close()
