"""Small page helpers: HTML escaping, the reduced-motion and effects switches, and the notice toast."""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import trade_runstate as runstate


def _reduced_motion_on():
    try:
        return bool(document.documentElement.classList.contains("reduce-motion"))
    except Exception:
        return False


def _effects_on():
    """J-31 -- the Settings "Effects" toggle (settings.js adds `.effects-off`
    to <html>). Effects are the optional flourishes: sale sparks, dock pulses
    and the ribbon unlock flourish. Reduced motion also turns them off."""
    try:
        classes = document.documentElement.classList
        return not (classes.contains("effects-off") or classes.contains("reduce-motion"))
    except Exception:
        return True


# J8/J17 — a second, independent toast for lightweight gameplay nudges
# (a manual ship's arrival, a one-time first-automation callout) that
# are deliberately *not* achievements, kept as its own element/class/
# proxy so it can never collide with an achievement unlocking at the
# same moment (both can be on screen together, in different spots).
_notice_hide_proxy = None

NOTICE_TOAST_DURATION_MS = 3000


def show_notice_toast(message):
    toast = document.getElementById("notice-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("notice-toast--visible")

    # Never destroy a still-pending timer's proxy: the browser would later
    # call it and Pyodide throws "Object has already been destroyed". Each
    # timer owns its own proxy and destroys it after firing; a newer toast
    # just bumps the generation so stale timers become no-ops.
    runstate._notice_hide_proxy_gen += 1
    my_gen = runstate._notice_hide_proxy_gen
    holder = []

    def _hide():
        if my_gen == runstate._notice_hide_proxy_gen:
            toast.classList.remove("notice-toast--visible")
            toast.hidden = True
        holder[0].destroy()

    holder.append(create_proxy(_hide))
    setTimeout(holder[0], NOTICE_TOAST_DURATION_MS)


def _html_escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
