"""R-13: one continuous playthrough from the Tribal era to the Relay Age through game.py's real UI.

Every era has its own test file for its own content; none of them drove ALL the transitions in one run, which
is where a save, a revisit or the history could break only when the pieces meet. This test clicks through every
transition one after another, plays real seasons between them, saves and reloads at each step (a real JSON
round trip through get_state/load_state), then walks back through every completed era with the Look Back
revisit and returns to the present, checking that forward progress is never lost and the settlement is the
same one afterwards.
"""

import copy
import json

import sim

from .test_digital_era import (
    push_to_agrarian,
    push_to_classical,
    push_to_digital_ready,
    push_to_industrial_ready,
    push_to_medieval,
)
from .test_relay_era import push_to_relay_ready
from .test_space_age_era import push_to_space_ready

# (era reached, how to satisfy and click that transition)
def _click(game_env):
    game_env.module.render()
    game_env.elements["advance-era-button"].dispatch("click", None)


LEGS = [
    ("agrarian", push_to_agrarian),                                   # these two click themselves
    ("classical", push_to_classical),
    ("medieval", push_to_medieval),
    ("industrial", lambda env: (push_to_industrial_ready(env), _click(env))),
    ("digital", lambda env: (push_to_digital_ready(env), _click(env))),
    ("space", lambda env: (push_to_space_ready(env), _click(env))),
    ("relay", lambda env: (push_to_relay_ready(env), _click(env))),
]


def _tend(env):
    """What a player does between eras: keep everyone fed and the stores stocked, so the settlement the next
    transition judges is a healthy one rather than one that starved while the test was only counting seasons."""
    state = env.state
    state.resources["food"] = max(state.resources.get("food", 0.0), 5000.0)
    state.resources["materials"] = max(state.resources.get("materials", 0.0), 5000.0)
    state.resources["tools"] = max(state.resources.get("tools", 0.0), 500.0)
    state.fed_fraction = 1.0


def _roundtrip(env):
    """get_state -> real JSON -> load_state on the live module; returns the dict that was loaded."""
    data = json.loads(json.dumps(copy.deepcopy(env.module.get_state())))
    assert env.module.load_state(copy.deepcopy(data)) is True
    return data


def test_every_transition_in_one_continuous_run_with_a_save_and_reload_after_each(game_env):
    env = game_env
    campaign = env.module.campaign
    assert env.state.era == "tribal"
    reached = ["tribal"]
    season_marks = []
    for era, leg in LEGS:
        _tend(env)
        leg(env)
        assert env.state.era == era, f"the transition into {era} did not happen"
        reached.append(era)
        env.advance_season(2)                          # a couple of real seasons in the new era
        season_marks.append(env.state.season)
        before = env.state.to_dict() if hasattr(env.state, "to_dict") else None
        data = _roundtrip(env)
        assert env.state.era == era and campaign.furthest_era == era
        assert data["current_era"] == era and data["furthest_era"] == era
        assert campaign.revisiting is None
        if before is not None:
            assert env.state.to_dict() == before
    assert reached == ["tribal"] + [e for e, _ in LEGS]
    assert reached == list(sim.ERA_ORDER)[: len(reached)]
    assert season_marks == sorted(season_marks) and len(set(season_marks)) == len(season_marks)


def test_looking_back_at_every_completed_era_and_returning_loses_nothing(game_env):
    env = game_env
    campaign = env.module.campaign
    for _era, leg in LEGS:
        _tend(env)
        leg(env)
        env.advance_season()
    present = copy.deepcopy(env.module.get_state()["current_state"])
    furthest = campaign.furthest_era
    assert furthest == "relay"
    for era in [e for e in sim.ERA_ORDER if e != "relay"]:
        assert campaign.enter_revisit(era) is True, era
        assert env.state.era == era and campaign.revisiting == era
        # a revisit is itself saveable and resumable, with the present parked beside it
        data = _roundtrip(env)
        assert data["revisiting"] == era and data["furthest_era"] == "relay"
        assert campaign.revisiting == era
        env.advance_season(2)                          # play around in the past
        assert campaign.exit_revisit() is True
        assert campaign.revisiting is None and campaign.parked_state is None
        assert env.state.era == "relay"
        assert env.module.get_state()["current_state"] == present, f"forward progress changed after looking at {era}"


def test_an_era_not_yet_reached_cannot_be_revisited_and_the_chain_never_skips(game_env):
    env = game_env
    campaign = env.module.campaign
    assert campaign.enter_revisit("agrarian") is False          # not completed yet
    for era, leg in LEGS[:3]:
        _tend(env)
        leg(env)
    assert env.state.era == "medieval"
    assert campaign.enter_revisit("digital") is False
    assert campaign.enter_revisit("classical") is True
    assert campaign.exit_revisit() is True
    assert env.state.era == "medieval"


def test_the_achievements_and_log_survive_the_whole_run(game_env):
    env = game_env
    for _era, leg in LEGS:
        _tend(env)
        leg(env)
        env.advance_season()
    data = _roundtrip(env)
    assert data["furthest_era"] == "relay"
    earned_before = list(env.module.get_state().get("achievements_earned", []))
    assert earned_before == list(_roundtrip(env).get("achievements_earned", []))
    entries = env.module.get_state()["log"]["entries"]
    beats = [e for e in entries if e.get("kind") == "transition"]
    assert [b["era"] for b in beats] == [era for era, _ in LEGS]       # one beat per era, in order, none lost on reload
    assert all(b["text"] for b in beats)
