"""Tiny helpers every panel uses: _element() (look up a page element), pref_get()/pref_set() (per-browser preferences) and the
speech hooks speech_available()/speak_french().
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document


def _element(element_id):
    return document.getElementById(element_id)


# --- per-browser preferences (remembered, not part of the save code) -------
# index.html defines window.champPrefGet/champPrefSet over localStorage. They
# do not exist under pytest (there is no js.window in the fake module), so both
# helpers quietly do nothing there. Used for the "Always multiple choice"
# setting and every minigame's difficulty.


def pref_get(key, default=None):
    try:
        from js import window

        getter = getattr(window, "champPrefGet", None)
        if getter is None:
            return default
        value = getter(key)
        return default if value is None else str(value)
    except Exception:
        return default


def pref_set(key, value):
    try:
        from js import window

        setter = getattr(window, "champPrefSet", None)
        if setter is not None:
            setter(key, str(value))
    except Exception:
        pass


def speech_available():
    """Whether the page can speak French (its `champSpeak` hook exists and the
    browser reports speech synthesis)."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    return getattr(window, "champSpeak", None) is not None and bool(getattr(window, "champSpeechAvailable", lambda: False)())


def speak_french(text, slow=False):
    """Reads `text` aloud; False when the page cannot speak."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    hook = getattr(window, "champSpeak", None)
    if hook is None:
        return False
    hook(str(text), bool(slow))
    return True
