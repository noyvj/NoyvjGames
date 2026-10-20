import contextlib
import functools
import http.server
import socket
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
GAME = "continuum"


@pytest.fixture(scope="module")
def base():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield "http://localhost:%d/games/%s/" % (port, GAME)
    server.shutdown()


READY = ("(() => { const s = document.querySelector('#engine-status');"
         " if (s) return s.textContent === '' || s.hidden;"
         " return !!window.pyodide && !!window.pyodide.globals.get('get_state'); })()")


def open_game(p, base, width=1280, height=800):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route("**/*fastapicloud*/**", lambda route: route.abort())
    page = ctx.new_page()
    page.goto(base + "index.html#play")
    page.wait_for_function(READY, timeout=90000)
    return browser, page


def scene_ready(page):
    page.wait_for_timeout(3000)
    return page.evaluate("!!(window.ContinuumScene && window.ContinuumScene.ready())")


def test_the_wheel_zooms_the_camera_and_stops_at_the_limits(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")

        # Zoom in (deltaY negative)
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true }));
        """)
        dist = page.evaluate("window.ContinuumScene.cameraState().distance")
        assert abs(dist - 8.5) < 0.01

        # Thirty more wheel-up events
        for _ in range(30):
            page.evaluate("""
                const el = document.querySelector('#visual3d-container');
                el.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true }));
            """)
        dist = page.evaluate("window.ContinuumScene.cameraState().distance")
        assert dist == 3.5

        # Sixty events with deltaY 100 (zoom out)
        for _ in range(60):
            page.evaluate("""
                const el = document.querySelector('#visual3d-container');
                el.dispatchEvent(new WheelEvent('wheel', { deltaY: 100, bubbles: true, cancelable: true }));
            """)
        dist = page.evaluate("window.ContinuumScene.cameraState().distance")
        assert dist == 16.0

        # No JS errors expected during interaction.
        browser.close()


def test_a_right_drag_pans_the_camera_and_a_preset_resets_it(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")

        # Right-drag pan
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new PointerEvent('pointerdown', {pointerType: 'mouse', button: 2, pointerId: 1, bubbles: true, clientX: 200, clientY: 200}));
        """)
        page.evaluate("""
            window.dispatchEvent(new PointerEvent('pointermove', {pointerType: 'mouse', pointerId: 1, clientX: 250, clientY: 200}));
        """)
        page.evaluate("window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 1}));")

        # Check pan offset
        checks = page.evaluate("""
            (() => {
                const s = window.ContinuumScene.cameraState();
                const k = s.distance * 0.0016;
                const expX = -Math.cos(s.yaw) * 50 * k;
                const expZ = Math.sin(s.yaw) * 50 * k;
                return {
                    x: Math.abs(s.targetX - expX) < 1e-6,
                    z: Math.abs(s.targetZ - expZ) < 1e-6
                };
            })()
        """)
        assert checks["x"]
        assert checks["z"]

        # Preset resets targetX and targetZ to 0
        page.click("#camera-preset-overview-button")
        s = page.evaluate("""
            (() => {
                const c = window.ContinuumScene.cameraState();
                return { targetX: c.targetX, targetZ: c.targetZ };
            })()
        """)
        assert s["targetX"] == 0
        assert s["targetZ"] == 0

        # Left-button drag changes yaw but leaves targetX/targetZ at 0
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new PointerEvent('pointerdown', {pointerType: 'mouse', button: 0, pointerId: 2, bubbles: true, clientX: 200, clientY: 200}));
        """)
        page.evaluate("""
            window.dispatchEvent(new PointerEvent('pointermove', {pointerType: 'mouse', pointerId: 2, clientX: 250, clientY: 200}));
        """)
        page.evaluate("window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 2}));")

        s = page.evaluate("""
            (() => {
                const c = window.ContinuumScene.cameraState();
                return { targetX: c.targetX, targetZ: c.targetZ, yaw: c.yaw };
            })()
        """)
        assert s["targetX"] == 0
        assert s["targetZ"] == 0
        assert s["yaw"] != 0

        browser.close()


def test_a_two_finger_tap_returns_to_the_last_preset(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")

        # Click closeup preset
        page.click("#camera-preset-closeup-button")

        # Zoom in slightly so distance changes from 5.5
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true }));
        """)

        # Two finger down on container
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new PointerEvent('pointerdown', {pointerType: 'touch', pointerId: 1, bubbles: true, clientX: 200, clientY: 200}));
        """)
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new PointerEvent('pointerdown', {pointerType: 'touch', pointerId: 2, bubbles: true, clientX: 260, clientY: 200}));
        """)

        # Two finger up on window (order: 2 then 1)
        page.evaluate("window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 2}));")
        page.evaluate("window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 1}));")

        s = page.evaluate("""
            (() => {
                const c = window.ContinuumScene.cameraState();
                return { yaw: c.yaw, pitch: c.pitch, distance: c.distance, targetX: c.targetX, targetZ: c.targetZ };
            })()
        """)
        assert abs(s["yaw"] - 0.7) < 1e-6
        assert abs(s["pitch"] - 0.4) < 1e-6
        assert abs(s["distance"] - 4.5) < 1e-6
        assert s["targetX"] == 0
        assert s["targetZ"] == 0

        browser.close()


def test_two_finger_tap_with_move_keeps_distance(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")

        # Click closeup preset
        page.click("#camera-preset-closeup-button")

        # Zoom in slightly
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true }));
        """)
        initial_dist = page.evaluate("window.ContinuumScene.cameraState().distance")

        # Two finger down on container
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new PointerEvent('pointerdown', {pointerType: 'touch', pointerId: 1, bubbles: true, clientX: 200, clientY: 200}));
        """)
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new PointerEvent('pointerdown', {pointerType: 'touch', pointerId: 2, bubbles: true, clientX: 260, clientY: 200}));
        """)

        # Move finger 1 on window
        page.evaluate("""
            window.dispatchEvent(new PointerEvent('pointermove', {pointerType: 'touch', pointerId: 1, clientX: 240, clientY: 200}));
        """)

        # Two finger up on window
        page.evaluate("window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 2}));")
        page.evaluate("window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 1}));")

        final_dist = page.evaluate("window.ContinuumScene.cameraState().distance")
        assert abs(final_dist - initial_dist) < 1e-6

        browser.close()


def test_one_finger_tap_does_not_change_camera(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base)
        if not scene_ready(page):
            pytest.skip("no WebGL")

        # Click closeup preset
        page.click("#camera-preset-closeup-button")

        initial_dist = page.evaluate("window.ContinuumScene.cameraState().distance")

        # One finger down and up on container
        page.evaluate("""
            const el = document.querySelector('#visual3d-container');
            el.dispatchEvent(new PointerEvent('pointerdown', {pointerType: 'touch', pointerId: 1, bubbles: true, clientX: 200, clientY: 200}));
        """)
        page.evaluate("window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 1}));")

        final_dist = page.evaluate("window.ContinuumScene.cameraState().distance")
        assert abs(final_dist - initial_dist) < 1e-6

        browser.close()
