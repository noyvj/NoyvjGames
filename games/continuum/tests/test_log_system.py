"""Milestone 6 — the ongoing log / diegetic feedback system.

Covers the three trigger conditions the design doc's milestone table asks
for (a research unlock, a population threshold, a livability shift), the
save round-trip of the "have we already logged this" bookkeeping, and the
game.py wiring (research fires immediately, population/livability fire on
season advance, the panel renders newest-first and never grows past
LOG_VISIBLE_ENTRIES rows in the DOM).
"""

import log
import research
import save
import sim
import sustainability


def fresh_campaign():
    return save.Campaign(sim.CityState(), research.build_tree())


# --- Chronicle: research trigger ----------------------------------------
def test_bootstrap_does_not_log_the_starting_state(game_env):
    """A brand-new settlement (population 6, nothing researched) shouldn't
    retroactively "discover" milestones it started below/without."""
    assert game_env.module.chronicle.entries == []


def test_researching_a_node_logs_it_immediately_not_on_next_season(game_env):
    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 100.0

    assert tree.research("fire_keeping", state.resources) is True
    game_env.module.chronicle.check_research(state, tree)

    kinds = [e.kind for e in game_env.module.chronicle.entries]
    assert "research" in kinds
    entry = next(e for e in game_env.module.chronicle.entries if e.kind == "research")
    assert "Fire-Keeping" in entry.text


def test_research_button_click_logs_through_the_full_handler(game_env):
    state = game_env.state
    state.resources["knowledge"] = 100.0
    game_env.module.render()  # build the research rows/buttons

    game_env.elements["research-fire_keeping"].dispatch("click", None)

    entries = game_env.module.chronicle.entries
    assert any(e.kind == "research" and "Fire-Keeping" in e.text for e in entries)


def test_a_failed_research_attempt_logs_nothing(game_env):
    state = game_env.state
    tree = game_env.module.tree
    assert state.resources["knowledge"] < tree.nodes["fire_keeping"].cost

    assert tree.research("fire_keeping", state.resources) is False
    game_env.module.chronicle.check_research(state, tree)

    assert game_env.module.chronicle.entries == []


# --- Chronicle: population trigger --------------------------------------
def test_population_milestone_logs_once_when_crossed():
    campaign = fresh_campaign()
    campaign.state.population = 9
    campaign.log.check_population(campaign.state)
    assert campaign.log.entries == []

    campaign.state.population = 10
    campaign.log.check_population(campaign.state)
    assert len(campaign.log.entries) == 1
    assert campaign.log.entries[0].kind == "population"

    # Staying at/above 10 (or re-checking) must not log it again.
    campaign.log.check_population(campaign.state)
    campaign.state.population = 11
    campaign.log.check_population(campaign.state)
    assert len(campaign.log.entries) == 1


def test_population_milestones_can_be_skipped_over_in_one_jump():
    """Starvation/growth can move population by more than 1 in a season;
    crossing several thresholds at once should log all of them, not just
    the highest."""
    campaign = fresh_campaign()
    campaign.state.population = 6
    campaign.log.check_population(campaign.state)

    campaign.state.population = 42  # crosses 10, 15, 25, 40 at once
    campaign.log.check_population(campaign.state)

    kinds = [e.kind for e in campaign.log.entries]
    assert kinds.count("population") == 4


# --- Chronicle: livability shift (diegetic feedback) ---------------------
def test_livability_shift_up_logs_a_reaction():
    campaign = fresh_campaign()
    effects = campaign.tree.effects()
    campaign.log._last_score_label = "Strained"  # pretend it was worse before

    label = sustainability.score_label(sustainability.score(campaign.state, effects))
    assert label != "Strained"  # a fresh settlement isn't Strained

    campaign.log.check_livability(campaign.state, effects)
    assert len(campaign.log.entries) == 1
    assert campaign.log.entries[0].kind == "livability-up"


def test_livability_shift_down_names_the_weakest_component():
    campaign = fresh_campaign()
    effects = campaign.tree.effects()
    # Force conditions worse than a fresh settlement's, so the label is
    # guaranteed to be below "Thriving".
    campaign.state.fed_fraction = 0.2
    campaign.state.land_health = 0.2
    campaign.state.resources["tools"] = 0.0
    campaign.state.resources["food"] = 0.0
    starting_label = sustainability.score_label(sustainability.score(campaign.state, effects))
    assert starting_label != "Thriving"
    campaign.log._last_score_label = "Thriving"

    campaign.log.check_livability(campaign.state, effects)
    assert len(campaign.log.entries) == 1
    entry = campaign.log.entries[0]
    assert entry.kind == "livability-down"
    weakest = sustainability.weakest_component(campaign.state, effects)
    assert entry.text == log.LIVABILITY_DOWN_TEXT[weakest]


def test_no_shift_logs_nothing():
    campaign = fresh_campaign()
    effects = campaign.tree.effects()
    campaign.log.check_livability(campaign.state, effects)  # first call: baseline already set
    before = len(campaign.log.entries)
    campaign.log.check_livability(campaign.state, effects)  # nothing changed
    assert len(campaign.log.entries) == before


# --- Chronicle: entry cap -------------------------------------------------
def test_entries_are_capped_at_max_entries():
    campaign = fresh_campaign()
    for i in range(log.MAX_ENTRIES + 10):
        campaign.log._add(log.LogEntry(i, "tribal", "population", f"entry {i}"))
    assert len(campaign.log.entries) == log.MAX_ENTRIES
    # Oldest dropped first: the surviving entries are the most recent ones.
    assert campaign.log.entries[0].text == f"entry {10}"
    assert campaign.log.entries[-1].text == f"entry {log.MAX_ENTRIES + 9}"


# --- save round-trip -------------------------------------------------------
def test_log_survives_a_save_round_trip():
    campaign = fresh_campaign()
    campaign.state.resources["knowledge"] = 100.0
    campaign.tree.research("fire_keeping", campaign.state.resources)
    campaign.log.check_research(campaign.state, campaign.tree)
    campaign.state.population = 10
    campaign.log.check_population(campaign.state)

    data = campaign.to_dict()
    assert len(data["log"]["entries"]) == 2

    fresh = fresh_campaign()
    assert fresh.load_dict(data) is True
    assert len(fresh.log.entries) == 2
    assert fresh.log.entries[0].text == campaign.log.entries[0].text
    assert fresh.log._population_milestones_hit == {10}
    assert fresh.log._researched_seen == {"fire_keeping"}

    # Re-checking after a load must not re-log anything already recorded.
    fresh.log.check_research(fresh.state, fresh.tree)
    fresh.log.check_population(fresh.state)
    assert len(fresh.log.entries) == 2


def test_loading_a_pre_milestone_6_save_bootstraps_instead_of_replaying_history():
    """A save with no "log" key at all (written before this system existed)
    shouldn't dump the settlement's whole history into the log the moment
    it loads."""
    campaign = fresh_campaign()
    campaign.state.resources["knowledge"] = 100.0
    campaign.tree.research("fire_keeping", campaign.state.resources)
    campaign.state.population = 25
    data = campaign.to_dict()
    del data["log"]

    fresh = fresh_campaign()
    assert fresh.load_dict(data) is True
    assert fresh.log.entries == []
    assert fresh.log._researched_seen == {"fire_keeping"}
    assert 10 in fresh.log._population_milestones_hit
    assert 25 in fresh.log._population_milestones_hit
    assert 40 not in fresh.log._population_milestones_hit

    # And nothing gets logged retroactively on the next real check either.
    fresh.log.check_research(fresh.state, fresh.tree)
    fresh.log.check_population(fresh.state)
    assert fresh.log.entries == []


def test_restore_tolerates_a_malformed_log_dict():
    campaign = fresh_campaign()
    campaign.log.restore({"entries": "not a list", "population_milestones_hit": None})
    assert campaign.log.entries == []
    assert campaign.log._population_milestones_hit == set()


# --- game.py wiring / rendering -------------------------------------------
def test_advance_season_checks_population_and_livability(game_env):
    state = game_env.state
    # Push the settlement well past the first population milestone by
    # feeding it hard, then advance seasons through game.py's own handler.
    state.resources["food"] = 500.0
    state.buildings["shelter"] = 5  # plenty of housing headroom
    for _ in range(6):
        game_env.advance_season()

    entries = game_env.module.chronicle.entries
    assert entries, "expected at least one log entry after several seasons"


def test_render_log_shows_newest_first_and_caps_visible_rows(game_env):
    chronicle = game_env.module.chronicle
    for i in range(game_env.module.LOG_VISIBLE_ENTRIES + 5):
        chronicle._add(log.LogEntry(i, "tribal", "population", f"entry {i}"))

    game_env.module.render_log()

    rows = game_env.elements["log-list"].children
    assert len(rows) == game_env.module.LOG_VISIBLE_ENTRIES
    # Newest entry (highest i) should be the first row rendered.
    newest_text = rows[0].children[1].innerText
    assert newest_text == f"entry {game_env.module.LOG_VISIBLE_ENTRIES + 4}"


def test_render_log_shows_placeholder_when_empty(game_env):
    game_env.module.render_log()
    rows = game_env.elements["log-list"].children
    assert len(rows) == 1
    assert "Nothing to report yet" in rows[0].innerText
