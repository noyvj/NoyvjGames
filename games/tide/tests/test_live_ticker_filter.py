"""D-17 (remaining part): chips and a search for the SHORT live ticker. The rule that matters: nothing is
hidden unless a player turns a filter on, and while one is on the page says so in words."""

import types

import pytest

MESSAGES = [
    "Fish stocks quietly declining — acidity is catching up.",
    "Economy diversified: tourism is now level 1.",
    "The first coastline tile has flooded — the sea has arrived.",
    "⛈️ Storm surge in Season 5 (Battered): 12 of 18 held back by your defences; the rest cost 6 funds.",
]


def _event(value):
    return types.SimpleNamespace(target=types.SimpleNamespace(value=value))


@pytest.fixture
def live(game_env):
    game_env.state.ticker_log = list(MESSAGES)
    game_env.module.live_ticker_filter = "all"
    game_env.module.live_ticker_search = ""
    game_env.module.render()
    return game_env


def _shown(env):
    return env.elements["ticker-log"].innerHTML


def test_default_shows_every_message_and_no_status_line(live):
    assert _shown(live) == "<br>".join(MESSAGES)
    assert live.elements["live-filter-status"].innerText == ""
    assert live.elements["live-filter-summary"].innerText == "Filter this list"
    assert live.elements["live-filter-all"].getAttribute("aria-pressed") == "true"


def test_a_fresh_page_state_is_all_and_empty_search(game_env):
    assert game_env.module.live_ticker_filter == "all"
    assert game_env.module.live_ticker_search == ""
    assert game_env.module.live_ticker_filtering() is False


def test_chip_narrows_the_live_ticker_and_says_what_is_hidden(live):
    live.elements["live-filter-fish"].dispatch("click", None)
    assert _shown(live) == MESSAGES[0]
    assert live.elements["live-filter-fish"].getAttribute("aria-pressed") == "true"
    assert live.elements["live-filter-all"].getAttribute("aria-pressed") == "false"
    status = live.elements["live-filter-status"].innerText
    assert "3 of the last 4 message(s) are hidden" in status and "Choose All" in status
    assert live.elements["live-filter-summary"].innerText == "Filter this list (on: Fish)"


def test_all_chip_restores_everything(live):
    live.elements["live-filter-storm"].dispatch("click", None)
    assert _shown(live) == MESSAGES[3]
    live.elements["live-filter-all"].dispatch("click", None)
    assert _shown(live) == "<br>".join(MESSAGES)
    assert live.elements["live-filter-status"].innerText == ""


def test_search_is_case_insensitive_and_combines_with_a_chip(live):
    live.elements["live-search-input"].dispatch("input", _event("TOURISM"))
    assert _shown(live) == MESSAGES[1]
    assert live.elements["live-filter-summary"].innerText == "Filter this list (on: search)"
    live.elements["live-filter-fish"].dispatch("click", None)
    assert _shown(live) == "No recent message matches this filter."
    assert "4 of the last 4" in live.elements["live-filter-status"].innerText
    assert live.elements["live-filter-summary"].innerText == "Filter this list (on: Fish + search)"


def test_filtering_never_changes_the_stored_ticker_or_the_full_history(live):
    full_before = list(live.state.ticker_full_history)
    live.elements["live-filter-sea"].dispatch("click", None)
    assert live.state.ticker_log == MESSAGES
    assert live.state.ticker_full_history == full_before


def test_live_and_full_history_filters_are_independent(live):
    live.state.ticker_full_history = list(MESSAGES)
    live.elements["live-filter-fish"].dispatch("click", None)
    live.module.render()
    assert live.module.ticker_filter == "all"
    assert live.elements["ticker-history-list"].innerHTML.count("<br>") == 3
    live.elements["live-filter-all"].dispatch("click", None)
    live.elements["ticker-filter-storm"].dispatch("click", None)
    assert _shown(live) == "<br>".join(MESSAGES)  # the history chip does not touch the live ticker
    live.module.ticker_filter = "all"


def test_a_new_message_is_filtered_the_same_way_as_it_arrives(live):
    live.elements["live-filter-economy"].dispatch("click", None)
    live.state._log_ticker("Economy diversified: aquaculture is now level 1.")
    live.module.render()
    assert "aquaculture" in _shown(live)
    live.state._log_ticker("Fish stocks recovering.")
    live.module.render()
    assert "recovering" not in _shown(live)


def test_empty_ticker_keeps_its_own_wording_whatever_the_filter(game_env):
    game_env.state.ticker_log = []
    game_env.module.live_ticker_filter = "fish"
    game_env.module.render()
    assert game_env.elements["ticker-log"].innerHTML == "No notable changes yet."
    assert game_env.elements["live-filter-status"].innerText == ""
    game_env.module.live_ticker_filter = "all"


def test_when_everything_matches_the_status_says_so(live):
    live.state.ticker_log = ["Fish stocks fell.", "Fish stocks rose."]
    live.elements["live-filter-fish"].dispatch("click", None)
    assert live.elements["live-filter-status"].innerText == "Filtered: every recent message matches."


def test_markup_default_is_closed_and_all(  ):
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    block = html[html.index('class="ticker-live-filter"'):html.index('id="live-filter-status"')]
    assert "<details class=\"ticker-live-filter\"" in html and " open" not in block.split(">")[0]
    assert 'id="live-filter-all" class="secondary ticker-chip" type="button" aria-pressed="true"' in block
    assert block.count("aria-pressed=\"true\"") == 1
