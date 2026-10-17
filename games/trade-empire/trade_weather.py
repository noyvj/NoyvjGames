"""Market weather (booms, slumps, rumours, the ticker): the event stream, headlines, status text and panel."""

from js import document

import trade_runstate as runstate
from trade_colony import colony_producing
from trade_effects import WEATHER_BOOM, WEATHER_SLUMP, weather_active_event, weather_cascade_good
from trade_market import seasonal_reachable_goods
from trade_records import RECORDS_COUNT_MAX, records
from trade_rules import ALL_COLONIES, GOOD_LABEL


# ---------------------------------------------------------------------------
# J-17 / J-18 -- Market Weather (opt-in, off by default). One event at a time: after a quiet
# stretch (20-40 ticks) a boom or a slump hits one good for 20-40 ticks (a boom pays +30%, a
# slump pays 25% less) and the good made at the colony that needs it follows at half strength.
# Everything is derived from a hash of the charter's founding seed and the event number, so it
# is deterministic and testable, yet looks unpredictable to a player who is not reading the
# Almanac: dock gossip appears 12 ticks ahead (which colony), and 5 ticks ahead it says boom or
# slump, so a close reader can front-run it (stockpile before a boom). A text-only ticker chip
# on the map names the current event (no scrolling). Nothing here is ever lost permanently:
# a slump only lowers what one good sells for while it lasts.
# ---------------------------------------------------------------------------
WEATHER_GAP = (20, 40)
WEATHER_DURATION = (20, 40)
WEATHER_RUMOUR_TICKS = 12
WEATHER_DIRECTION_TICKS = 5
WEATHER_ACHIEVEMENT_EVENTS = 5
WEATHER_HEADLINES = {
    "boom": (
        "Festival at {colony}: demand for {good} is up",
        "Trade fair at {colony}: {good} is in short supply",
    ),
    "slump": (
        "Strike at {colony}: {good} buyers hold off, prices soften",
        "Port backlog at {colony}: {good} sits unsold, prices soften",
    ),
}


def _weather_hash(n):
    x = (runstate.founding_seed * 2654435761 + (n + 1) * 40503 + 12345) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 2246822519) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 3266489917) & 0xFFFFFFFF
    x ^= x >> 16
    return x


def _weather_make(n=None):
    """The event with number `n` (default: the next one), over the goods that can be reached right now."""
    n = runstate.weather_n if n is None else n
    goods = seasonal_reachable_goods()
    if not goods:
        return None
    h = _weather_hash(n)
    low, high = WEATHER_GAP
    dlow, dhigh = WEATHER_DURATION
    dur = dlow + (h >> 9) % (dhigh - dlow + 1)
    return {
        "good": goods[h % len(goods)],
        "kind": "boom" if (h >> 5) & 1 else "slump",
        "style": (h >> 7) & 1,
        "wait": low + (h >> 16) % (high - low + 1),
        "left": dur,
        "dur": dur,
    }


def weather_tick():
    """One tick of the weather clock (only while the mode is on)."""
    if not runstate.weather_enabled:
        return
    if runstate.weather_event is None:
        runstate.weather_event = _weather_make()
        if runstate.weather_event is None:
            return
        runstate.weather_n += 1
    ev = runstate.weather_event
    if ev["wait"] > 0:
        ev["wait"] -= 1
    elif ev["left"] > 0:
        ev["left"] -= 1
        if ev["left"] <= 0:
            runstate.weather_event = None
            if not runstate.sandbox_active:
                records["weather_events"] = min(RECORDS_COUNT_MAX, records["weather_events"] + 1)


def _weather_colony_name(good):
    return ALL_COLONIES[colony_producing(good)]["name"]


def weather_headline(ev):
    template = WEATHER_HEADLINES[ev["kind"]][ev["style"]]
    return template.format(colony=_weather_colony_name(ev["good"]), good=GOOD_LABEL[ev["good"]])


def weather_rumour(ev=None):
    """Dock gossip about an event that has not started yet, or '' when it is too far off."""
    ev = runstate.weather_event if ev is None else ev
    if not runstate.weather_enabled or ev is None or ev["wait"] <= 0:
        return ""
    colony = _weather_colony_name(ev["good"])
    if ev["wait"] <= WEATHER_DIRECTION_TICKS:
        word = "a boom" if ev["kind"] == "boom" else "a slump"
        return f"Dock gossip: {word} looks likely for {GOOD_LABEL[ev['good']]} from {colony} in about {ev['wait']} tick(s)."
    if ev["wait"] <= WEATHER_RUMOUR_TICKS:
        return f"Dock gossip at {colony}: something is brewing, in about {ev['wait']} tick(s)."
    return ""


def weather_ticker_text():
    if not runstate.weather_enabled:
        return ""
    ev = weather_active_event()
    if ev is not None:
        effect = WEATHER_BOOM if ev["kind"] == "boom" else WEATHER_SLUMP
        return f"{weather_headline(ev)} ({effect * 100:+.0f}%, {ev['left']} tick(s) left)."
    rumour = weather_rumour()
    return rumour or "Quiet markets: no weather right now."


def weather_status_text():
    if not runstate.weather_enabled:
        return (
            f"Optional: now and then one good has a boom ({WEATHER_BOOM * 100:+.0f}% on its price) or a slump "
            f"({WEATHER_SLUMP * 100:+.0f}%) for 20-40 ticks, and the good that depends on it follows at half strength. "
            "Dock gossip warns you a few ticks ahead. Nothing is permanent."
        )
    ev = weather_active_event()
    seen = records["weather_events"]
    line = f"Weather on. Events weathered so far: {seen}. "
    if ev is not None:
        follow = weather_cascade_good(ev["good"])
        line += f"Now: {weather_ticker_text()}"
        if follow:
            line += f" {GOOD_LABEL[follow]} follows at half strength."
    else:
        line += weather_rumour() or "Quiet markets for now."
    return line


def weather_almanac_note():
    if not runstate.weather_enabled:
        return ""
    return (
        '<p class="almanac-weather">Leading indicators for Market Weather: dock gossip names the colony '
        f"{WEATHER_RUMOUR_TICKS} ticks before an event and says boom or slump {WEATHER_DIRECTION_TICKS} ticks before. "
        "Stockpile ahead of a boom; a slump only lowers one good's price while it lasts.</p>"
    )


def render_weather():
    button = document.getElementById("weather-toggle-button")
    status = document.getElementById("weather-status")
    ticker = document.getElementById("news-ticker")
    if button is None or status is None:
        return
    button.innerText = f"Market weather: {'on' if runstate.weather_enabled else 'off'}"
    button.setAttribute("aria-pressed", "true" if runstate.weather_enabled else "false")
    status.innerText = weather_status_text()
    if ticker is not None:
        text = weather_ticker_text()
        ticker.hidden = not text
        if text != runstate._weather_ticker_text:
            runstate._weather_ticker_text = text
            ticker.innerText = text
