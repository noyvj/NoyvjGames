"""GF-19 tactile feel: CSS squish and a tractor on Advance Round (plain JS in settings.js, no audio)."""

from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CSS = (HERE / "style.css").read_text(encoding="utf-8")
JS = (HERE / "settings.js").read_text(encoding="utf-8")


def test_on_by_default_and_switchable():
    assert 'getItem(TACTILE_KEY) !== "false"' in JS
    assert "setTactile(true)" in JS  # Reset to Default turns it back on
    for page in ("index.html", "pc.html"):
        assert 'id="tactile-checkbox"' in (HERE / page).read_text(encoding="utf-8")


def test_the_tractor_is_decorative_and_only_runs_when_motion_is_allowed():
    assert 'tractor.setAttribute("aria-hidden", "true")' in JS
    assert "!motionAllowed()" in JS and "tactileOn()" in JS
    assert "click\", driveTractor" in JS


def test_squish_and_tractor_are_off_for_reduced_motion_and_lite_mode():
    for gate in ('html[data-reduced-motion="true"] .pasture-tractor', 'html[data-lite="true"] .pasture-tractor',
                 'html[data-reduced-motion="true"] button:active:not(:disabled)', "prefers-reduced-motion: reduce) { .pasture-tractor"):
        assert gate in CSS
    assert 'html:not([data-tactile="off"]) button:active' in CSS


def test_no_audio_is_involved():
    block = JS[JS.index("// GF-19"):JS.index("function initTactile")]
    assert "Audio" not in block and ".play(" not in block
