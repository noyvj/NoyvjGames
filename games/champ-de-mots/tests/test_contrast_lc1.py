"""LC-1 (2026-10-08): the readability fixes found by the computed-style contrast scan.

The scan itself needs a real browser (tests/tools/contrast_scan.py, run by hand, see
CLAUDE.md "LC-1"). What runs here is a static guard: the colour pairs it fixed are re-derived
from the stylesheets and must clear WCAG AA (4.5:1), so a later edit that puts dark ink back on a
dark card, or pale ink back on the pale sky, fails a test. Plus: the alternate styles' ink rules
exist and cover the classes that were failing, and the scanner tool is present and parses.
"""

import ast
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
STYLE = (GAME_DIR / "style.css").read_text(encoding="utf-8")
VISUAL = (GAME_DIR / "visual-styles.css").read_text(encoding="utf-8")
MINI = (GAME_DIR / "minigames.css").read_text(encoding="utf-8")


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lin(v):
    v /= 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def _lum(c):
    return 0.2126 * _lin(c[0]) + 0.7152 * _lin(c[1]) + 0.0722 * _lin(c[2])


def ratio(a, b):
    a, b = (_rgb(a) if isinstance(a, str) else a), (_rgb(b) if isinstance(b, str) else b)
    hi, lo = max(_lum(a), _lum(b)), min(_lum(a), _lum(b))
    return (hi + 0.05) / (lo + 0.05)


def blend(fg, bg, alpha):
    fg, bg = _rgb(fg), _rgb(bg)
    return tuple(f * alpha + b * (1 - alpha) for f, b in zip(fg, bg))


def body_of(css, selector):
    """Declarations of the first rule whose selector text is exactly `selector`."""
    match = re.search(r"(?:^|\}|\*/)\s*" + re.escape(selector) + r"\s*\{([^}]*)\}", css, flags=re.S)
    assert match, selector
    return match.group(1)


def hexes(text):
    return re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", text)


# --- the title and loose text on the dark theme's sky (the "white on white" report) -----------------


def test_dark_theme_sky_is_dark_enough_for_the_pale_loose_text():
    sky = body_of(STYLE, 'html:not([data-theme="light"]) .ambient-bg--champetre')
    stops = hexes(sky)
    assert len(stops) >= 2
    lightest = max(stops, key=lambda c: _lum(_rgb(c)))
    # the title's gradient stops, the tagline (blended at its 0.75 opacity), the hub link and legend ink
    for ink in ("#eaeaf0", "#a9c3ff", "#cfd2e6", "#b9c3e8"):
        assert ratio(ink, lightest) >= 4.5, (ink, lightest)
    assert ratio(blend("#cfd2e6", lightest, 0.75), lightest) >= 4.5
    hill = hexes(body_of(STYLE, 'html:not([data-theme="light"]) .ambient-bg--champetre .ambient-bg-blobs'))
    for colour in hill:
        assert ratio("#eaeaf0", colour) >= 4.5


def test_the_sky_override_is_scoped_to_the_dark_theme():
    assert 'html:not([data-theme="light"]) .ambient-bg--champetre {' in STYLE
    # the shared pale sky is left alone for the light theme, which has its own rules
    assert 'html[data-theme="light"] .ambient-bg--champetre' not in STYLE


# --- buttons and cream cards in the default look -----------------------------------------------------


def test_primary_button_label_clears_aa_on_both_gradient_stops():
    block = STYLE[STYLE.rindex(".primary { background: linear-gradient"):]
    line = block.splitlines()[0]
    stops = hexes(line)
    assert len(stops) == 3  # two stops and the white label
    label = stops[-1]
    for stop in stops[:2]:
        assert ratio(label, stop) >= 4.5, stop


def test_cream_card_ink_clears_aa():
    cream = "#fbf7ee"
    tail = STYLE[STYLE.rindex("LC-1 (2026-10-08)"):]
    ink_block = re.search(r"\.practice-instruction, .*?\{ color: (#[0-9a-f]{6}); opacity: 1; \}", tail, flags=re.S)
    assert ink_block
    assert ratio(ink_block.group(1), cream) >= 4.5
    for name in (".dashboard-health-row", ".dashboard-practice-row", ".row-blurb", ".srs-explainer-line"):
        assert name in tail
    assert ratio("#33291f", cream) >= 4.5
    # the practice note sits on its own slightly darker cream
    assert ratio(ink_block.group(1), "#f2eddf") >= 4.5


def test_the_filter_selects_have_their_own_light_ink():
    assert ".farm-control select { background: #fdfbf5; color: #33291f;" in STYLE


# --- the alternate styles' dark blocks ------------------------------------------------------------------

PANEL_BG = {}
for _style in ("lowpoly", "textbased", "cartoon"):
    _m = re.search(
        r'html\[data-visual-style="%s"\] \.section,\s*(?:html\[data-visual-style="%s"\] [.\w-]+,\s*)*'
        r'html\[data-visual-style="%s"\] \.minigame-prompt-card \{([^}]*)\}' % (_style, _style, _style),
        VISUAL,
        flags=re.S,
    )
    assert _m, _style
    PANEL_BG[_style] = re.search(r"background:\s*(#[0-9a-fA-F]{6})", _m.group(1)).group(1)


def _lc_vars(style):
    block = body_of(VISUAL, f'html[data-visual-style="{style}"]:not([data-theme="light"])')
    return dict(re.findall(r"--(lc-[a-z]+):\s*(#[0-9a-fA-F]{6})", block))


def test_each_alternate_styles_ink_and_good_green_clear_aa_on_its_panels():
    for style in ("lowpoly", "textbased", "cartoon"):
        colours = _lc_vars(style)
        assert {"lc-ink", "lc-soft", "lc-good", "lc-bg"} <= set(colours), style
        for name in ("lc-ink", "lc-soft", "lc-good"):
            assert ratio(colours[name], PANEL_BG[style]) >= 4.5, (style, name)
            assert ratio(colours[name], colours["lc-bg"]) >= 4.5, (style, name)


def test_the_alternate_dark_ink_rule_covers_every_class_that_was_failing():
    start = VISUAL.index("LC-1 (2026-10-08)")
    rule = VISUAL[start:]
    first = rule[rule.index(":is(.practice-instruction, .practice-prompt, .practice-confidence-label"):]
    first = first[: first.index("{")]
    for needed in (
        ".practice-instruction", ".practice-prompt", ".practice-confidence-label",
        ".achievement-next", ".dashboard-since", ".dashboard-mastery-row", ".dashboard-empty",
        ".dashboard-heading", ".dashboard-practice-row", ".dashboard-health-row", ".achievement-heading",
        ".row-blurb", ".proficiency-topic-line", ".srs-explainer-line",
        ".settings-note", ".howto-step-number", "#placement-summary", "#conversation-line",
        '[id$="-prompt"]', '[id$="-instruction"]',
    ):
        assert needed in first, needed
    assert "[id$=\"-feedback\"]" in rule


def test_the_arcade_panels_get_pale_ink_in_the_dark_theme():
    start = VISUAL.index("LC-1 (2026-10-08)")
    rule = VISUAL[start:]
    assert 'html:not([data-theme="light"]) .minigame-panel :is(.practice-prompt' in rule
    # the arcade panel is dark glass: its darkest-to-lightest stops all carry the pale ink
    for stop in re.findall(r"rgba\((\d+), (\d+), (\d+), [\d.]+\)", body_of(MINI, ".minigame-panel").split("border")[0]):
        assert ratio("#eaeaf0", tuple(int(v) for v in stop)) >= 4.5
    feedback = re.search(r"\.practice-feedback.*?\{ color: (#[0-9a-fA-F]{6});", rule).group(1)
    assert ratio(feedback, (36, 42, 66)) >= 4.5  # the glass over the dusk sky, at its lightest


# --- the scanner tool ----------------------------------------------------------------------------------

def test_the_contrast_scanner_ships_with_the_tests_and_parses():
    tool = GAME_DIR / "tests" / "tools" / "contrast_scan.py"
    script = GAME_DIR / "tests" / "tools" / "contrast_scan.js"
    assert tool.exists() and script.exists()
    ast.parse(tool.read_text(encoding="utf-8"))
    source = tool.read_text(encoding="utf-8")
    assert "Disabled controls" in source and "fastapicloud" in source  # never touches the live backend


def test_no_text_colour_is_left_on_a_background_it_cannot_beat():
    """A pair-table of the colours the scan fixed, so one edit cannot undo them silently."""
    pairs = [
        ("#ffffff", "#527a37"), ("#ffffff", "#3b5322"),   # green buttons
        ("#eef3f6", "#22323d"), ("#b9f5c9", "#0a0f12"), ("#f5eaff", "#3a1868"),  # alternate dark panels
        ("#33291f", "#fbf7ee"), ("#5a4c38", "#fbf7ee"),   # cream cards
    ]
    for fg, bg in pairs:
        assert ratio(fg, bg) >= 4.5, (fg, bg)
