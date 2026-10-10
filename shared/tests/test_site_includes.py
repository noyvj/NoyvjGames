"""Every page must carry the site-wide shared includes (Z-19 a11y, Z-21 perf marks, Z-23 touch
targets, Z-24 debug overlay, Z-25 error boundary, Z-29 info footer, Z-31 lite mode), in an order
that is safe, and the service worker must precache them. Static checks over the HTML files; the
behaviour of each piece is tested in the *_browser.py files next to this one.

Le Champ de Mots is another session's file right now (its index.html is edited by hand and its
pc.html is generated from it), so its two pages are an explicit TODO: they are expected to fail
until that session runs `python3 scripts/wire-shared-includes.py` and regenerates the Desktop page
(the xfail is not strict, so wiring them simply turns these into passes)."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STILL_TO_WIRE = set()

GAME_SCRIPTS = ["lite-mode.js", "error-boundary.js", "perf-mark.js", "debug-overlay.js", "info-footer.js"]
GAME_STYLES = ["a11y.css", "touch-targets.css", "lite-mode.css"]
HUB_PAGES = ["index.html", "settings.html", "help.html", "credits.html", "achievements.html",
             "map.html", "my-stats.html", "steward.html", "whats-new.html", "roadmap.html", "sources.html", "terms.html"]
SHARED_FILES = GAME_SCRIPTS + GAME_STYLES
# Z-17 Report a problem and Z-7 profile helper: on every game page (Classic and Desktop). Not in the
# service worker's precache list yet (that file belongs to the main session), so they are kept apart
# from SHARED_FILES, which test_every_shared_file_is_precached checks.
GAME_EXTRA_SCRIPTS = ["report-problem.js", "profile.js"]


def game_pages():
    out = []
    for folder in sorted((ROOT / "games").iterdir()):
        for name in ("index.html", "pc.html"):
            page = folder / name
            if page.exists():
                out.append(pytest.param(folder.name, name, marks=[pytest.mark.xfail(
                    reason="TODO: Le Champ de Mots is being edited by another session", strict=False)]
                    if folder.name in STILL_TO_WIRE else []))
    return out


def tags(html):
    return [m.group(0) for m in re.finditer(r"<(?:script|link)\b[^>]*>", html)]


def position(html, needle):
    index = html.find(needle)
    assert index >= 0, needle
    return index


def src_tag(html, file):
    found = [t for t in tags(html) if re.search(rf'(?:src|href)="[^"]*shared/{re.escape(file)}"', t)]
    assert found, f"missing include of shared/{file}"
    assert len(found) == 1, f"shared/{file} included {len(found)} times"
    return found[0]


@pytest.mark.parametrize("slug,name", game_pages())
def test_game_page_includes_every_shared_file(slug, name):
    html = (ROOT / "games" / slug / name).read_text(encoding="utf-8")
    for file in SHARED_FILES:
        tag = src_tag(html, file)
        assert (file.endswith(".js") and tag.startswith("<script")) or (file.endswith(".css") and 'rel="stylesheet"' in tag)
    for file in ("error-boundary.js", "perf-mark.js", "info-footer.js"):
        assert f'data-game-id="{slug}"' in src_tag(html, file), f"{file} needs the game id"
    assert 'data-game-id="' not in src_tag(html, "lite-mode.js")


@pytest.mark.parametrize("slug,name", game_pages())
def test_game_page_includes_report_problem_and_profile(slug, name):
    html = (ROOT / "games" / slug / name).read_text(encoding="utf-8")
    head = html[: html.index("</head>")]
    for file in GAME_EXTRA_SCRIPTS:
        tag = src_tag(html, file)
        assert tag.startswith("<script"), file
        assert f'data-game-id="{slug}"' in tag, f"{file} needs the game id"
        # in <head>, after the error boundary (already listening), before the settings sync
        assert position(head, "shared/error-boundary.js") < position(head, f"shared/{file}") < position(head, "shared/site-settings.js")
    if name == "index.html":
        assert 'data-mount=".game-toolbar"' in src_tag(html, "report-problem.js"), "Classic mounts the button in the game toolbar"
        assert "data-button" not in src_tag(html, "report-problem.js")
        assert 'class="game-toolbar' in html, "the toolbar the button is mounted in must exist"
    else:
        # Desktop: a Menu > Help entry replaces the floating button, or the floating button stays
        tag = src_tag(html, "report-problem.js")
        entry = 'id="noyvj-report-menu-button"' in html
        assert entry == ('data-button="none"' in tag), "the toolbar button is off exactly when the Menu entry exists"
        if entry:
            assert '"noyvj-report-menu-button"' in html, "the Help group must list the entry"
            assert html.index('id="noyvj-report-menu-button"') < html.index("shared/pc-shell.js")


@pytest.mark.parametrize("slug,name", game_pages())
def test_game_page_include_order_is_safe(slug, name):
    html = (ROOT / "games" / slug / name).read_text(encoding="utf-8")
    head = html[: html.index("</head>")]
    # scripts run in <head> before the settings sync (which needs NoyvjLite) and before first paint
    assert position(head, "shared/theme.js") < position(head, "shared/lite-mode.js") < position(head, "shared/site-settings.js")
    for file in ("error-boundary.js", "perf-mark.js"):
        assert position(head, f"shared/{file}") < position(head, "shared/site-settings.js")
    # error boundary first, so it is already listening while the others and the game's own scripts run
    assert position(head, "shared/error-boundary.js") < position(head, "shared/perf-mark.js")
    # stylesheets last in <head>, after the game's own CSS, lite mode very last so it wins ties
    own = [m.start() for m in re.finditer(r'<link rel="stylesheet" href="(?!\.\./\.\./shared/(?:a11y|touch-targets|lite-mode))[^"]*">', head)]
    mine = [position(head, f"shared/{f}") for f in GAME_STYLES]
    assert max(own) < min(mine) and mine == sorted(mine)
    assert head.rstrip().endswith('lite-mode.css">')


@pytest.mark.parametrize("name", HUB_PAGES)
def test_hub_pages_include_lite_mode_and_a11y(name):
    html = (ROOT / name).read_text(encoding="utf-8")
    head = html[: html.index("</head>")]
    assert position(head, "shared/theme.js") < position(head, "shared/lite-mode.js")
    if "shared/site-settings.js" in head:
        assert position(head, "shared/lite-mode.js") < position(head, "shared/site-settings.js")
    for file in ("lite-mode.js", "a11y.css", "lite-mode.css"):
        src_tag(head, file)
    assert "touch-targets.css" not in html, "the hub keeps its own sizing; touch targets are for the games"
    assert head.rstrip().endswith('lite-mode.css">')


def test_hub_has_the_lite_toggles():
    assert "data-lite-toggle" in (ROOT / "index.html").read_text(encoding="utf-8")
    settings = (ROOT / "settings.html").read_text(encoding="utf-8")
    assert re.search(r'<input type="checkbox" id="settings-lite" data-lite-toggle>', settings)


def test_every_shared_file_is_precached_and_the_worker_version_moved():
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    block = sw[sw.index("const PRECACHE_URLS"): sw.index("];", sw.index("const PRECACHE_URLS"))]
    for file in SHARED_FILES:
        assert f'"shared/{file}"' in block, f"{file} missing from PRECACHE_URLS"
    version = int(re.search(r"const SW_VERSION = (\d+);", sw).group(1))
    assert version >= 34, "SW_VERSION must be bumped when the precache list changes"


def test_wiring_script_reports_nothing_left_to_do():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "wire-shared-includes.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def test_desktop_pages_are_not_stale():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "generate-pc-pages.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_continuum_scene_reads_the_lite_switch():
    source = (ROOT / "games" / "continuum" / "render3d.js").read_text(encoding="utf-8")
    assert "NoyvjLite" in source and "antialias: !liteMode()" in source


def test_thaw_no_longer_has_a_private_lite_attribute():
    for name in ("settings.js", "style.css"):
        text = (ROOT / "games" / "thaw" / name).read_text(encoding="utf-8")
        assert "data-lite-mode" not in text


def test_wiring_script_is_idempotent_and_refuses_pages_it_cannot_place(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("wire_shared_includes", ROOT / "scripts" / "wire-shared-includes.py")
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    page = tmp_path / "index.html"
    page.write_text('<html><head>\n<link rel="stylesheet" href="style.css">\n'
                    '  <script src="../../shared/theme.js" data-floating-toggle></script>\n'
                    '  <script src="../../shared/site-settings.js" data-game-id="x"></script>\n</head><body></body></html>\n')
    once = wire.wire(page, wire.game_scripts, wire.game_styles, "x")
    page.write_text(once)
    assert wire.wire(page, wire.game_scripts, wire.game_styles, "x") == once, "second run must change nothing"
    for file in SHARED_FILES + GAME_EXTRA_SCRIPTS:
        assert once.count(f"shared/{file}") == 1
    assert once.index("info-footer.js") < once.index("report-problem.js") < once.index("profile.js") < once.index("site-settings.js")
    assert once.index("lite-mode.js") < once.index("site-settings.js")
    page.write_text("<html><head></head><body>no theme tag</body></html>")
    assert wire.wire(page, wire.game_scripts, wire.game_styles, "x") is None
