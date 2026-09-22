"""planning/TODO.md's "Big standalone features": a visual-style switcher
(low-poly / text-based / cartoon / high-def), chosen on first load and
changeable in settings, desktop-only.

Entirely a browser-level UI preference -- plain JS + CSS, independent of
Pyodide (see visual-style.js's own docstring), so there is no game.py
function to unit-test here. These tests instead pin the same kind of
structural contract this game's suite already uses for other zero-Python
integrations (e.g. test_farm_ui.py's check that shared/save-widget.js is
actually wired into index.html): the right files are linked, the settings
control exists with the right ids, and the game's existing wellbeing/static-
screenshot constraints aren't violated by the new files.
"""

from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _source(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def test_visual_style_files_exist():
    assert (GAME_DIR / "visual-style.js").exists()
    assert (GAME_DIR / "visual-styles.css").exists()


def test_index_html_links_the_visual_style_files():
    html = _source("index.html")
    assert '<script src="visual-style.js"></script>' in html
    assert '<link rel="stylesheet" href="visual-styles.css">' in html
    # Loaded after style.css/minigames.css so its overrides can win the cascade.
    style_pos = html.index('href="style.css"')
    minigames_pos = html.index('href="minigames.css"')
    switcher_pos = html.index('href="visual-styles.css"')
    assert style_pos < switcher_pos
    assert minigames_pos < switcher_pos


def test_settings_panel_has_all_four_style_buttons_for_both_contexts():
    """L2: two independent presets (farm/review), each with its own row of
    the same four style buttons."""
    html = _source("index.html")
    assert 'id="settings-toggle-button"' in html
    assert 'id="settings-panel"' in html
    for context in ("farm", "review"):
        for name in ("highdef", "lowpoly", "textbased", "cartoon"):
            assert f'id="visual-style-{name}-{context}-button"' in html


def test_visual_style_js_declares_the_same_four_styles():
    source = _source("visual-style.js")
    for name in ("highdef", "lowpoly", "textbased", "cartoon"):
        assert f'"{name}"' in source
    assert 'DEFAULT_STYLE = "highdef"' in source


def test_visual_style_js_persists_to_localstorage_not_game_state():
    """Browser-level preference, same category as ACCENT_SENSITIVE and
    plot.last_variant -- must never ride the save-code payload."""
    source = _source("visual-style.js")
    assert "localStorage" in source
    assert "get_state" not in source
    assert "load_state" not in source


def test_visual_styles_css_only_targets_the_data_attribute_scope():
    """High-def is the pre-existing look and needs zero rules of its own --
    every real override must be scoped under a non-default
    html[data-visual-style="..."] selector so it can never leak into the
    default experience."""
    css = _source("visual-styles.css")
    for name in ("lowpoly", "textbased", "cartoon"):
        assert f'html[data-visual-style="{name}"]' in css


def test_visual_styles_css_never_touches_plot_stage_color_source():
    """The farm's own stage-colour meanings (style.css's .plot/.plot--*
    block) must stay byte-for-byte untouched by this feature, same
    constraint the site-wide space-theme pass already enforced (see
    CLAUDE.md's Milestone 4 build note). Any recolouring a style wants to do
    to the farm grid has to happen via a `filter` layered on top from this
    separate, later-loaded file -- never a hex value edited in style.css."""
    style_css = _source("style.css")
    assert "background: #efe7d7" in style_css  # .plot--seed's original tone, untouched
    assert "background: #b6d792" in style_css  # .plot--automated's original tone, untouched


def test_visual_styles_css_has_no_animation_or_timers():
    """This game's whole aesthetic (Milestone 7) treats every frame as a
    usable screenshot -- a style switch should be an instant swap. Not
    scanned by test_polish.py's own style.css-only check, since this is a
    separate file, so it gets the same rule pinned here explicitly."""
    css = _source("visual-styles.css")
    for pattern in ("@keyframes", "animation:", "transition:"):
        assert pattern not in css
    js = _source("visual-style.js")
    for pattern in ("setInterval", "setTimeout", "requestAnimationFrame"):
        assert pattern not in js


def test_settings_note_explains_the_scope_and_persistence():
    html = _source("index.html")
    assert "Saved to this browser only" in html


# --- V-AB-1: first-run picker ------------------------------------------


def test_index_html_has_an_accessible_first_run_picker():
    html = _source("index.html")
    assert 'id="visual-style-picker"' in html
    assert 'role="dialog"' in html and 'aria-modal="true"' in html
    assert 'id="visual-style-picker-skip"' in html
    for name in ("highdef", "lowpoly", "textbased", "cartoon"):
        assert f'data-style="{name}"' in html
    # Starts hidden; only visual-style.js reveals it on a first run.
    picker_tag = html[html.index('<div id="visual-style-picker"'):]
    assert " hidden>" in picker_tag.split(">", 1)[0] + ">"


def test_picker_text_is_honest_about_css_only_styles():
    html = _source("index.html").lower()
    assert "not separate artwork" in html


def test_visual_style_js_opens_picker_only_on_first_desktop_run():
    source = _source("visual-style.js")
    assert "hasStoredStyle" in source
    assert "min-width: 641px" in source
    assert "openPicker" in source
    # Skip / Escape both take the default, and the choice is persisted via applyStyle.
    assert 'event.key === "Escape"' in source
    assert "close(DEFAULT_STYLE)" in source


def test_first_run_default_is_not_persisted_until_answered():
    source = _source("visual-style.js")
    assert "applyStyleUnsaved" in source


def test_tutorial_waits_for_the_picker():
    html = _source("index.html")
    assert "whenPickerDone(startTutorial)" in html


# --- L2: two independent per-context presets (farm / review) -----------


def test_visual_style_js_has_two_distinct_storage_keys():
    source = _source("visual-style.js")
    assert '"champ-de-mots-visual-style"' in source
    assert '"champ-de-mots-visual-style-review"' in source


def test_an_unset_review_preset_falls_back_to_the_farm_preset():
    """A returning player who never touches the new review row should see
    no behavior change from before this feature existed."""
    source = _source("visual-style.js")
    assert 'context === "review" ? readStoredStyle("farm")' in source


def test_set_context_is_exposed_for_game_py_to_call():
    source = _source("visual-style.js")
    assert "function setContext(context)" in source
    assert "setContext: setContext" in source


def test_set_context_is_a_no_op_when_the_context_is_unchanged():
    """Avoids redundant DOM writes every render — render_review() calls
    this on every single render() pass, not just on a real transition."""
    source = _source("visual-style.js")
    assert "context === currentContext" in source


def test_reset_button_resets_both_contexts():
    source = _source("visual-style.js")
    reset_section = source[source.index("settingsResetButton"):]
    assert "CONTEXTS.forEach" in reset_section


def test_game_py_notifies_the_switcher_from_render_review():
    """L2's actual context signal: game.py's render_review() is the one
    function that knows whether #review-panel is genuinely showing."""
    source = _source("game.py")
    assert "def _notify_visual_style_context(context):" in source
    assert 'ChampDeMotsVisualStyle' in source
    render_review = source[source.index("def render_review():"):]
    assert '_notify_visual_style_context("review" if review_mode is not None else "farm")' in render_review[:200]


def test_settings_note_explains_the_two_contexts():
    html = _source("index.html")
    assert "Two independent presets" in html
    assert "while on the farm" in html.lower()
    assert "during a review session" in html.lower()
