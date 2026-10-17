"""The time-lapse run replay (K-9): frames, scrubber, play and the panel."""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import timelapse

import continuum_runstate as runstate
from continuum_archive import _download_text
from continuum_founders import settlement_name


# ===========================================================================
# K-9: the time-lapse run replay. Scrub the settlement's recorded history as the civic map,
# with discoveries, eras, first buildings and founder's notes pinned on a timeline, and
# download an image strip. The data work is in timelapse.py; the panel is session-only state.
# ===========================================================================
TIMELAPSE_STEP_MS = 450


def _tl_frames():
    return timelapse.frames(runstate.campaign.ui) if runstate.campaign.revisiting is None else []


def on_toggle_timelapse(event=None):
    runstate.timelapse_open = not runstate.timelapse_open
    if runstate.timelapse_open:
        runstate._tl_index = max(0, len(_tl_frames()) - 1)
    else:
        _tl_stop()
    update_timelapse_panel()


def _tl_stop():
    runstate._tl_playing = False


def _tl_set_index(index):
    count = len(_tl_frames())
    runstate._tl_index = max(0, min(max(0, count - 1), int(index)))


def on_timelapse_scrub(event=None):
    _tl_stop()
    try:
        _tl_set_index(int(document.getElementById("timelapse-scrub").value))
    except (TypeError, ValueError):
        pass
    update_timelapse_panel()


def on_timelapse_prev(event=None):
    _tl_stop()
    _tl_set_index(runstate._tl_index - 1)
    update_timelapse_panel()


def on_timelapse_next(event=None):
    _tl_stop()
    _tl_set_index(runstate._tl_index + 1)
    update_timelapse_panel()


def _tl_tick(*args):
    if not runstate._tl_playing or not runstate.timelapse_open:
        runstate._tl_playing = False
        return
    count = len(_tl_frames())
    if runstate._tl_index >= count - 1:
        runstate._tl_playing = False
        update_timelapse_panel()
        return
    _tl_set_index(runstate._tl_index + 1)
    update_timelapse_panel()
    if runstate._tl_playing:
        setTimeout(runstate._tl_proxy, TIMELAPSE_STEP_MS)


def on_timelapse_play(event=None):
    if runstate._tl_playing:
        _tl_stop()
        update_timelapse_panel()
        return
    count = len(_tl_frames())
    if count < timelapse.MIN_FRAMES:
        return
    if runstate._tl_index >= count - 1:
        _tl_set_index(0)
    runstate._tl_playing = True
    if runstate._tl_proxy is None:
        runstate._tl_proxy = create_proxy(_tl_tick)
    update_timelapse_panel()
    setTimeout(runstate._tl_proxy, TIMELAPSE_STEP_MS)


def _make_timelapse_jump_handler(season):
    def handler(event=None):
        _tl_stop()
        for i, frame in enumerate(_tl_frames()):
            if frame["season"] == season:
                _tl_set_index(i)
                break
        update_timelapse_panel()
    return handler


_tl_pin_proxies = []


def on_timelapse_strip(event=None):
    frame_list = _tl_frames()
    if not timelapse.usable(frame_list):
        return
    name = settlement_name()
    _download_text(timelapse.strip_svg(frame_list, name), timelapse.strip_filename(name, frame_list), "image/svg+xml")


def update_timelapse_panel():
    toggle = document.getElementById("timelapse-toggle-button")
    panel = document.getElementById("timelapse-panel")
    toggle.innerText = "Hide Time-lapse" if runstate.timelapse_open else "⏱ Time-lapse"
    panel.hidden = not runstate.timelapse_open
    if not runstate.timelapse_open:
        return
    frame_list = _tl_frames()
    caption = document.getElementById("timelapse-caption")
    scrub = document.getElementById("timelapse-scrub")
    play = document.getElementById("timelapse-play-button")
    usable = timelapse.usable(frame_list)
    for button_id in ("timelapse-prev-button", "timelapse-next-button", "timelapse-strip-button"):
        document.getElementById(button_id).disabled = not usable
    play.disabled = not usable
    scrub.disabled = not usable
    pin_box = document.getElementById("timelapse-pins-list")
    for stale in _tl_pin_proxies:
        stale.destroy()
    _tl_pin_proxies.clear()
    pin_box.innerHTML = ""
    if not usable:
        caption.innerText = (
            "Nothing to replay yet: play at least two seasons (a Look Back has no replay of its own)."
            if runstate.campaign.revisiting is None
            else "A Look Back shows a past snapshot; return to the present to use the time-lapse."
        )
        document.getElementById("timelapse-map").innerHTML = ""
        document.getElementById("timelapse-chart").innerHTML = ""
        play.innerText = "▶ Play"
        return
    _tl_set_index(runstate._tl_index)
    frame = frame_list[runstate._tl_index]
    pin_list = timelapse.pins(runstate.campaign.ui, frame_list)
    scrub.setAttribute("min", "0")
    scrub.setAttribute("max", str(len(frame_list) - 1))
    if str(scrub.value) != str(runstate._tl_index):
        scrub.value = str(runstate._tl_index)
    scrub.setAttribute("aria-valuetext", timelapse.caption(frame))
    play.innerText = "⏸ Pause" if runstate._tl_playing else "▶ Play"
    play.setAttribute("aria-pressed", "true" if runstate._tl_playing else "false")
    caption.innerText = timelapse.caption(frame)
    here = timelapse.pins_at(pin_list, frame["season"])
    if here:
        caption.innerText += " " + " ".join(timelapse.pin_text(p) for p in here)
    document.getElementById("timelapse-map").innerHTML = timelapse.map_svg(frame)
    document.getElementById("timelapse-chart").innerHTML = timelapse.chart_svg(frame_list, runstate._tl_index, pin_list)
    if not pin_list:
        row = document.createElement("p")
        row.className = "row-blurb"
        row.innerText = "No events pinned yet: study a discovery, raise a building or add a founder's note."
        pin_box.appendChild(row)
    for pin in pin_list:
        button = document.createElement("button")
        button.className = "secondary timelapse-pin"
        button.type = "button"
        button.innerText = timelapse.pin_text(pin)
        proxy = create_proxy(_make_timelapse_jump_handler(pin["season"]))
        _tl_pin_proxies.append(proxy)
        button.addEventListener("click", proxy)
        pin_box.appendChild(button)
