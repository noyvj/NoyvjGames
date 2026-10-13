"""Open a game's page (and its Desktop page) in Chromium and list the script errors from the game's own files.

    python local-ai/page_check.py <repo folder> <game>       prints a JSON list of error lines

Used by ai.ps1 after a task changes a game's .js, .html or .css: the 2026-10-12 review found Signal
Desktop features that passed every test but crashed or did nothing in the browser, because pc.js runs
before the board exists. Waits for the Python engine to start (Pyodide comes from its CDN, so this needs
the network), then a few more seconds. Errors from the service worker or other sites are ignored.
"""
import contextlib
import functools
import http.server
import json
import socket
import sys
import threading
import time
from pathlib import Path


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def free_port():
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def check(root, game):
    from playwright.sync_api import sync_playwright
    port = free_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(QuietHandler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for page_name in ("index.html", "pc.html"):
                if not (root / "games" / game / page_name).exists():
                    continue
                page = browser.new_page(viewport={"width": 1400, "height": 900} if page_name == "pc.html" else {"width": 390, "height": 844})
                found = []
                page.on("pageerror", lambda exc, found=found: found.append(f"{exc.name}: {exc.message} | {exc.stack or ''}"))
                page.goto(f"http://127.0.0.1:{port}/games/{game}/{page_name}", wait_until="load", timeout=60000)
                deadline = time.time() + 45
                while time.time() < deadline and not page.evaluate("!!window.pyodide"):
                    time.sleep(1)
                time.sleep(4)
                for line in found:
                    if f"/games/{game}/" in line or "/games/" not in line:
                        first = line.split("\n")[0]
                        errors.append(f"{page_name}: {first[:300]}")
                page.close()
            browser.close()
    finally:
        server.shutdown()
    return sorted(set(errors))


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    try:
        print(json.dumps(check(Path(sys.argv[1]).resolve(), sys.argv[2])))
    except Exception as exc:                      # no Playwright, no network: say so, never block a task on it
        print(json.dumps({"unavailable": str(exc)[:200]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
