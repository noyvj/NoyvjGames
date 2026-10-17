"""render() and setup() for all minigames, the list of newer games, the tick functions the page calls every second, and the
'water by minigame' helpers.
Part of the split of the old single-file minigames.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import champ_minigames_runstate as runstate
from champ_minigames_blitz import _blitz_candidate_plots, _setup_blitz, blitz_available, render_blitz
from champ_minigames_racer import _racer_candidate_plots, _setup_racer, racer_available, render_racer
from champ_minigames_boutique import (
    _boutique_colour_entries, _boutique_garment_entries, _setup_boutique, boutique_available, render_boutique,
)
from champ_minigames_cafe import (
    _cafe_food_entries, _cafe_twist_candidate_plots, _setup_cafe, cafe_available, render_cafe,
)
from champ_minigames_sprint import _setup_sprint, _sprint_candidate_plots, render_sprint, sprint_available
from champ_minigames_arcade import _can_water
from champ_minigames_games import _GapsGame, _ListenGame, _OrderGame, _PairsGame
from champ_minigames_amis import AMIS, amis_cache_is_stale, fetch_amis, load_amis_cache
import sys


def render():
    """Called once per repaint from game.py's own render(), same as every
    other secondary mode's render_<mode>() call. Milestone 27 ships only
    Blitz; each later milestone (28-30) adds its own render_<mode>() call
    here as that minigame lands, same incremental pattern as game.py's own
    render() growing one line per milestone."""
    render_blitz()
    render_racer()
    render_boutique()
    render_cafe()
    render_sprint()
    for game in NEW_GAMES:
        game.render()


def setup():
    """Called once from game.py's setup(), after configure(). Wires every
    DOM listener this file needs -- fully self-contained, so game.py never
    reaches into this module's internals beyond configure()/setup()/render()
    and the handful of tick functions JS calls directly (aliased at the
    bottom of game.py). Grows one _setup_<mode>() call per milestone, same
    as render() above."""
    _setup_blitz()
    _setup_racer()
    _setup_boutique()
    _setup_cafe()
    _setup_sprint()
    for game in NEW_GAMES:
        game.setup()
    # Faux Amis: show the last read list straight away (it feeds the farm's false-friend
    # badges) and read the live page again in the background when there is none or it is old.
    load_amis_cache()
    if runstate.amis_status != "ready" or amis_cache_is_stale():
        fetch_amis()


PAIRS = _PairsGame()
GAPS = _GapsGame()
LISTENPICK = _ListenGame()
WORDORDER = _OrderGame()


NEW_GAMES = (PAIRS, GAPS, LISTENPICK, WORDORDER, AMIS)


def pairs_tick(event=None):
    return PAIRS.tick()


def gaps_tick(event=None):
    return GAPS.tick()


def listenpick_tick(event=None):
    return LISTENPICK.tick()


def wordorder_tick(event=None):
    return WORDORDER.tick()


def amis_tick(event=None):
    return AMIS.tick()


def any_timed_run_active():
    """True while any arcade minigame has a countdown running. The page's
    one-second JS timer asks this when the tab is hidden (shared/pause-hidden.js),
    so the "paused while the tab was hidden" note only shows when a run
    really was held. Reads state only; never moves a clock."""
    if runstate.blitz_active or runstate.racer_active or runstate.boutique_active or runstate.cafe_active or runstate.sprint_active:
        return True
    return any(game.active for game in NEW_GAMES)


def pairs_available():
    return PAIRS.available()


def start_pairs(event=None):
    return PAIRS.start()


def start_gaps(event=None):
    return GAPS.start()


def start_listenpick(event=None):
    return LISTENPICK.start()


def start_wordorder(event=None):
    return WORDORDER.start()


# ---------------------------------------------------------------------------
# "Water by minigame": what each game waters, for game.py's Water options
# ---------------------------------------------------------------------------
def _plots_for_fr_texts(fr_texts):
    seen, plots = set(), []
    for fr in fr_texts:
        plot = runstate._plot_for_fr(fr) if runstate._plot_for_fr is not None else None
        if plot is not None and plot.plot_id not in seen:
            seen.add(plot.plot_id)
            plots.append(plot)
    return plots


def _boutique_water_pool():
    frs = [g[0] for g in _boutique_garment_entries()] + [c[0] for c in _boutique_colour_entries()]
    return _plots_for_fr_texts(frs)


def _cafe_water_pool():
    plots = _plots_for_fr_texts([fr for fr, _en in _cafe_food_entries()])
    seen = {p.plot_id for p in plots}
    return plots + [p for p in _cafe_twist_candidate_plots() if p.plot_id not in seen]


def _open_blitz():
    runstate.blitz_open = True
    render()


def _open_racer():
    runstate.racer_open = True
    render()


def _open_boutique():
    runstate.boutique_open = True
    render()


def _open_cafe():
    runstate.cafe_open = True
    render()


def _open_sprint():
    runstate.sprint_open = True
    render()


WATER_GAMES = [
    ("blitz", "Greetings & Basics Blitz", "vocabulary, phrases and examples from weeks 1-11",
     _blitz_candidate_plots, blitz_available, _open_blitz),
    ("racer", "Verb Racer", "grammar plots from weeks 12-15",
     _racer_candidate_plots, racer_available, _open_racer),
    ("boutique", "Boutique Dash", "clothing and colour plots from weeks 16-18",
     _boutique_water_pool, boutique_available, _open_boutique),
    ("cafe", "Café Rush", "food and drink plots, plus passé composé plots in the twist (weeks 19-23)",
     _cafe_water_pool, cafe_available, _open_cafe),
    ("sprint", "Passé Composé Sprint", "passé composé grammar plots from weeks 21-23",
     _sprint_candidate_plots, sprint_available, _open_sprint),
]
_WATER_NOTES = {
    "pairs": "vocabulary and phrase plots from weeks 12-23",
    "gaps": "grammar plots outside weeks 12-15 and the passé composé",
    "listenpick": "vocabulary, phrase and pronunciation plots from every week",
    "wordorder": "grammar plots that have a short example sentence, every week",
}
for _game in NEW_GAMES:
    if _game.key not in _WATER_NOTES:
        continue  # Faux Amis is about a live list, not the player's plots: it waters nothing
    _note = _WATER_NOTES[_game.key]
    WATER_GAMES.append((_game.key, _game.open_label.split(" ", 1)[1], _note, _game.pool, _game.available, _game.open_panel))


def game_pool(key):
    """Every plot a game can water (lazy; the same pools the games draw from)."""
    for entry in WATER_GAMES:
        if entry[0] == key:
            return list(entry[3]())
    return []


def water_game_rows():
    """One row per minigame for game.py's Water options panel: the title, what
    it waters, how many of those plots can still be watered today, whether it
    is open to play."""
    rows = []
    for key, title, note, pool_fn, available_fn, _open_fn in WATER_GAMES:
        available = bool(available_fn())
        count = sum(1 for p in pool_fn() if _can_water(p)) if available else 0
        rows.append({"key": key, "title": title, "note": note, "count": count, "available": available})
    return rows


def open_game(key):
    for entry in WATER_GAMES:
        if entry[0] == key:
            entry[5]()
            return True
    return False


# Hand render() to every earlier module that calls it before this file exists (see the `render = None` lines).
for _name in (
    "champ_minigames_core",
    "champ_minigames_blitz",
    "champ_minigames_racer",
    "champ_minigames_boutique",
    "champ_minigames_cafe",
    "champ_minigames_sprint",
    "champ_minigames_arcade",
    "champ_minigames_games",
    "champ_minigames_amis",
):
    sys.modules[_name].render = render
del _name
