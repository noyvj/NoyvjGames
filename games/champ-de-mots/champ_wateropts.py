"""The 'Water options' chooser: starting a session of the chosen kind, the listening buttons and the panel's drawing.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import minigames
import champ_runstate as runstate
from champ_model import state
from champ_util import _element, speak_french, speech_available
from champ_watering import water_today_text
from champ_water_pool import (
    WATER_LISTEN_MODE, WATER_MC_MODE, WATER_ROW_MODE, WATER_TOPICS, WATER_TOPIC_MODE, WATER_TYPED_MODE,
    WATER_WILTING_MODE, water_option_counts, water_option_proxies,
)
from champ_review import start_review
from champ_practice import on_water_next


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


def start_water_session(mode, arg=None, event=None):
    """Begin a chooser session in the Review panel; returns how many plots it
    holds (0 shows the friendly empty message)."""
    runstate.water_mode_arg = arg
    runstate.water_options_open = False
    start_review(mode)
    try:
        # Classic: the Review panel is further down the page than the chooser.
        getattr(_element("review-panel"), "scrollIntoView")()
    except Exception:
        pass
    return len(runstate.review_queue)


def on_toggle_water_options(event=None):
    runstate.water_options_open = not runstate.water_options_open
    render()


def on_water_row_change(event=None):
    try:
        runstate.water_row_choice = int(_element("water-row-select").value)
    except (TypeError, ValueError):
        runstate.water_row_choice = 1
    render()


def on_water_topic_change(event=None):
    value = _element("water-topic-select").value
    if value in {key for key, _ in WATER_TOPICS}:
        runstate.water_topic_choice = value
    render()


def on_water_next_option(event=None):
    runstate.water_options_open = False
    on_water_next()
    render()


def on_water_row_start(event=None):
    start_water_session(WATER_ROW_MODE, runstate.water_row_choice)


def on_water_topic_start(event=None):
    start_water_session(WATER_TOPIC_MODE, runstate.water_topic_choice)


def on_water_wilting_start(event=None):
    start_water_session(WATER_WILTING_MODE)


def on_water_mc_start(event=None):
    start_water_session(WATER_MC_MODE)


def on_water_typed_start(event=None):
    start_water_session(WATER_TYPED_MODE)


def on_water_listen_start(event=None):
    start_water_session(WATER_LISTEN_MODE)


def on_review_listen(event=None):
    if runstate.review_question is not None and runstate.review_mode == WATER_LISTEN_MODE:
        speak_french(runstate.review_question["prompt"])


def on_review_listen_show(event=None):
    runstate.review_listen_revealed = True
    render()


def _populate_water_selects():
    row_select = _element("water-row-select")
    row_select.innerHTML = ""
    for row in state.rows:
        option = document.createElement("option")
        option.value = str(row.sequence)
        title = f": {row.chapter_title}" if row.chapter_title else ""
        option.innerText = f"Week {row.sequence}{title}"
        row_select.appendChild(option)
    row_select.value = str(runstate.water_row_choice)
    topic_select = _element("water-topic-select")
    topic_select.innerHTML = ""
    for key, label in WATER_TOPICS:
        option = document.createElement("option")
        option.value = key
        option.innerText = label
        topic_select.appendChild(option)
    topic_select.value = runstate.water_topic_choice


def _water_count_text(count, unit="plot"):
    if count == 1:
        return f"1 {unit} can be watered now"
    return f"{count} {unit}s can be watered now"


def _destroy_water_option_proxies():
    for proxy in water_option_proxies:
        proxy.destroy()
    water_option_proxies.clear()


def _make_open_game_handler(key):
    def handler(event=None):
        runstate.water_options_open = False
        minigames.open_game(key)
        render()
    return handler


def render_water_options():
    panel = _element("water-options-panel")
    toggle = _element("water-options-toggle-button")
    toggle.innerText = "Close water options" if runstate.water_options_open else "🚿 Water options"
    _destroy_water_option_proxies()
    if not runstate.water_options_open:
        panel.hidden = True
        return
    panel.hidden = False
    _element("water-today-line").innerText = water_today_text()
    counts = water_option_counts()
    for key, count in counts.items():
        _element(f"water-opt-{key}-count").innerText = _water_count_text(count)
        _element(f"water-opt-{key}-button").disabled = count == 0
    if not speech_available():
        _element("water-opt-listen-count").innerText = "needs speech synthesis (not available here)"
    games_box = _element("water-games-list")
    games_box.innerHTML = ""
    for row in minigames.water_game_rows():
        line = document.createElement("div")
        line.className = "water-game-row"
        label = document.createElement("span")
        label.className = "water-game-label dashboard-practice-row"
        label.innerText = f"{row['title']} — waters {row['note']}"
        count = document.createElement("span")
        count.className = "water-game-count dashboard-practice-row"
        count.innerText = _water_count_text(row["count"]) if row["available"] else "locked"
        button = document.createElement("button")
        button.className = "secondary"
        button.innerText = "Play"
        button.id = f"water-game-{row['key']}-button"
        button.disabled = not row["available"]
        proxy = create_proxy(_make_open_game_handler(row["key"]))
        button.addEventListener("click", proxy)
        water_option_proxies.append(proxy)
        line.appendChild(label)
        line.appendChild(count)
        line.appendChild(button)
        games_box.appendChild(line)
