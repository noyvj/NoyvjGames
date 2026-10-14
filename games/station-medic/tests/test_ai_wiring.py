"""Wiring checks for the Round 4 phone and Desktop additions (R4-SMMO-*, R4-SMPC-*): the page elements the scripts need exist,
events are dispatched on the target that is listened to, settings are wired, and the pledge holds (no timers, no audio)."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
PC = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
PC_HTML = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
PAGE_IDS = set(re.findall(r'\bid="([^"]+)"', HTML))


def test_every_id_pc_js_looks_up_exists_in_the_page_or_is_made_by_pc_js():
    used = set(re.findall(r'getElementById\("([^"]+)"\)', PC))
    made = set(re.findall(r'\.id = "([^"]+)"', PC))
    assert used <= PAGE_IDS | made | {"pc-stage", "pc-side"}, sorted(used - PAGE_IDS - made)


def test_every_id_app_js_builds_or_reads_for_the_new_ui_is_in_the_page():
    for needed in ("cabinet-tabs", "sheet-tab", "sheet-close-button", "sheet-panel", "sheet-heading", "notes-banner", "notes-list",
                   "notes-close-btn", "notes-tab", "sign-conditions", "night-toggle", "shift-heading", "action-line"):
        assert needed in PAGE_IDS, needed
        assert needed in APP or needed in SETTINGS, needed


def test_the_old_mobile_supplies_file_is_gone_and_not_loaded():
    assert not (GAME_DIR / "mobile-supplies.js").exists()
    assert "mobile-supplies" not in HTML and "mobile-supplies" not in PC_HTML


def test_the_redraw_event_is_dispatched_and_listened_to_on_document():
    assert 'document.dispatchEvent(new CustomEvent("station-medic-rendered"))' in APP
    assert 'document.addEventListener("station-medic-rendered"' in PC
    assert "window.dispatchEvent" not in APP and "window.stationMedicView" in APP and "window.stationMedicSelect" in APP


def test_the_key_guard_ignores_hidden_window_frames_and_keys_are_wired():
    assert "[role='dialog']:not([hidden])" in APP
    assert re.search(r"[^:]\[role='dialog'\]\"", APP) is None
    for key in ('key === "s"', 'key === "t"', 'key === "z"'):
        assert key in APP
    assert 'action: "undo"' in APP


def test_the_sheet_has_a_visible_way_open_and_the_desktop_layout_keeps_the_plain_panel():
    assert 'id="sheet-tab"' in HTML and "setSheetOpen(true)" in APP
    assert CSS.count('html:not([data-layout="pc"]) #sheet-panel') >= 2
    assert not re.search(r"^\s*#sheet-panel\s*\{[^}]*position: fixed", CSS, re.M)


def test_phone_only_elements_are_hidden_by_default_on_every_width():
    assert re.search(r"\.sheet-tab, \.sheet-close, \.notes-banner, \.notes-tab \{ display: none; \}", CSS)


def test_night_mode_is_a_per_device_setting_read_on_load_and_reset():
    assert "station-medic-dim-night" in SETTINGS and 'getElementById("night-toggle")' in SETTINGS
    assert re.search(r"remove\(DIM_KEY\)", SETTINGS)
    assert 'html[data-dim-night="on"]' in CSS
    assert "night-mode" not in CSS.replace("shared/night-mode", "")


def test_the_buzz_is_off_under_reduced_motion_and_the_effects_switch_and_nothing_is_timed_or_audible():
    body = APP[APP.index("function buzz("):APP.index("function buzz(") + 500]
    assert 'data-reduced-motion") === "true"' in body and 'data-effects") === "off"' in body and "navigator.vibrate" in body
    assert not re.search(r"setInterval\(", APP + PC) and len(re.findall(r"setTimeout\(", APP)) == 1 and "setTimeout(" not in PC
    assert "new Audio" not in APP + PC and "AudioContext" not in APP + PC


def test_pc_extras_are_scoped_to_the_desktop_page_and_print_hides_the_rest():
    assert 'src="pc.js"' in PC_HTML and 'src="pc.js"' not in HTML
    assert '#print-report { display: none; }' in PC_CSS
    assert 'html[data-layout="pc"] body > *:not(#print-report) { display: none !important; }' in PC_CSS
    assert "role\", \"dialog\"" not in PC
