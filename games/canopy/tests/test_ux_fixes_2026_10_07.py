"""UX-1, UX-3, UX-4, UX-5 (user-reported 2026-10-07).

UX-3 and UX-1 and UX-5 live in index.html / style.css / pc.css / pc-config.json, which the
fake-DOM harness cannot run, so those are structural guards (the behaviour was verified in a real
browser, see CLAUDE.md). UX-4 is behavioural and lives in test_display_batch_1.py.
"""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
INDEX = (GAME_DIR / "index.html").read_text(encoding="utf-8")
STYLE = (GAME_DIR / "style.css").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
PC_CONFIG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
GAME_PY = (GAME_DIR / "game.py").read_text(encoding="utf-8")


# --- UX-3: arrow keys -------------------------------------------------------

def test_arrow_keys_listen_on_the_document_not_only_on_the_grid():
    """The old listener sat on #plot-grid and needed a focused tile, but the grid is rebuilt every
    tick, so focus was lost one second after any click."""
    assert 'plotGrid.addEventListener("keydown"' not in INDEX
    assert re.search(r'document\.addEventListener\("keydown",\s*\(e\)\s*=>\s*\{\s*const delta = ARROW_DELTA', INDEX)


def test_focus_is_restored_after_the_grid_is_rebuilt():
    assert "keyboardFocusWanted" in INDEX
    assert re.search(r"new MutationObserver\(\(\) => \{\s*if \(!keyboardFocusWanted", INDEX)
    assert "tile.focus({ preventScroll: true })" in INDEX


def test_arrow_keys_still_ignore_form_fields_and_modals():
    handler = INDEX[INDEX.index("const ARROW_DELTA"):INDEX.index('window.addEventListener("keydown"')]
    for needle in ("SELECT", "INPUT", "TEXTAREA", "#opening-screen", "#tutorial-overlay", "e.shiftKey"):
        assert needle in handler


def test_shortcut_help_lists_the_arrow_keys():
    assert "Arrow keys" in INDEX[INDEX.index("KeyboardShortcuts.init"):]


# --- UX-4: reset flow -------------------------------------------------------

def test_reset_uses_the_shared_confirm_dialog_not_a_timed_double_press():
    assert "RESET_CONFIRM_WINDOW_MS" not in GAME_PY
    assert "_reset_confirm_armed" not in GAME_PY
    assert "ConfirmDialog" in GAME_PY
    assert "confirm-dialog.js" in INDEX


def test_escape_dismisses_the_confirm_dialog_before_the_menu_can_open():
    assert 'getElementById("confirm-dialog-cancel")' in INDEX


# --- UX-1: phone layout -----------------------------------------------------

def _phone_block():
    start = STYLE.index("Mobile condensed action panel")
    start = STYLE.index("@media (max-width: 640px)", start)
    end = STYLE.index("Mobile docked stats + legend")
    return STYLE[start:end]


def test_phone_action_dock_is_one_compact_row():
    block = _phone_block()
    assert "flex-wrap: nowrap" in block
    assert "max-height: 42vh" in block
    assert "--action-dock-h" in block


def test_phone_dock_folds_the_extras_behind_a_button():
    block = _phone_block()
    for needle in ("#tend-status", ".names-details", "#soil-hint", "#adopted-plot-panel", ".action-dock-more"):
        assert needle in block
    assert 'id="action-dock-more"' in INDEX
    assert "--action-dock-h" in INDEX


def test_phone_pills_follow_the_dock_instead_of_sitting_on_it():
    block = _phone_block()
    assert "#story-toggle" in block
    assert "#save-widget.collapsed" in block
    # the Stats pill used to be a fixed 138px up, i.e. underneath a taller dock
    assert "bottom: 138px" not in STYLE


def test_desktop_boot_hides_the_phone_only_button():
    assert "#action-dock-more" in PC_CSS


# --- UX-5: Desktop side column ----------------------------------------------

def test_desktop_side_column_holds_only_what_you_act_on():
    assert PC_CONFIG["zones"]["side"] == ["#action-panel", "#stakeholder-panel"]


def test_desktop_demoted_panels_are_windows_not_dropped():
    composites = {c["id"]: c for c in PC_CONFIG["composites"]}
    assert composites["pc-stats-panel"]["members"] == ["#stats"]
    assert composites["pc-name-panel"]["members"] == [".names-details"]
    assert "#forest-visual" in composites["pc-about-panel"]["members"]


def test_every_id_game_py_needs_is_still_in_the_desktop_page():
    pc_html = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
    for element_id in ("stats", "forest-visual", "forest-name-input", "plot-nickname-input",
                       "tend-status", "action-panel", "stakeholder-panel", "specialist-row"):
        assert f'id="{element_id}"' in pc_html
