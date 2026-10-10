"""The walker is deterministic and rewinding restores exactly the earlier state."""

import json

import game
import kit
import story
import walker


def _lcg(seed):
    state = seed
    while True:
        state = (state * 1103515245 + 12345) % (2 ** 31)
        yield state >> 8


def random_walk(seed, limit=60):
    """A reproducible walk: at each scene pick one open choice by a seeded generator. Returns the path string."""
    gen = _lcg(seed)
    state, _found = walker.initial()
    path = ""
    while not story.SCENES[state[0]]["end"] and len(path) < limit:
        open_ = [i for i in range(len(story.SCENES[state[0]]["choices"])) if walker.available(state, i)[0]]
        i = open_[next(gen) % len(open_)]
        state, _info = walker.step(state, i)
        path += str(i)
    return path


def test_the_same_choices_always_give_the_same_state():
    for seed in range(40):
        path = random_walk(seed)
        a, b = walker.replay(path), walker.replay(path)
        assert a[1] == b[1] and a[2] == b[2]


def test_every_random_walk_reaches_an_ending_within_twelve_days():
    for seed in range(60):
        path = random_walk(seed)
        final = walker.replay(path)[1]
        assert story.SCENES[final[0]]["end"], (seed, final)
        assert len(path) <= 30


def test_stats_stay_between_zero_and_ten():
    for seed in range(60):
        for step in walker.replay(random_walk(seed))[0]:
            assert all(kit.LOW <= v <= kit.HIGH for v in step["after"][1])


def test_a_locked_choice_is_refused_and_changes_nothing():
    low = ("d2d", (2, 6, 5), ())             # d2d's first reply needs Trust 4
    nxt, info = walker.step(low, 0)
    assert nxt is None and "Trust 4" in info["why"] and "you have 2" in info["why"]
    high = ("d2d", (4, 6, 5), ())
    nxt, info = walker.step(high, 0)
    assert nxt is not None and nxt[0] == "d3a" and "knowfuel" in nxt[2]
    assert walker.step(high, 7)[0] is None and walker.step(high, True)[0] is None


def test_rewinding_restores_exactly_the_earlier_state_in_the_engine():
    for seed in range(25):
        path = random_walk(seed)
        steps = walker.replay(path)[0]
        for n in range(len(path)):
            earlier = walker.replay(path[:n])
            expect = steps[n]["before"] if n < len(steps) else None
            assert earlier[1] == expect


def test_rewinding_through_the_game_restores_exactly_the_earlier_view():
    for seed in range(8):
        path = random_walk(seed)
        for n in range(0, len(path), 3):
            game.game.__init__()
            views = []
            for ch in path:
                views.append(json.loads(game.handle(json.dumps({"action": "choose", "i": int(ch)}))))
            before = json.loads(game.handle('{"action": "open"}'))
            assert before["run"]["path"] == path
            after = json.loads(game.handle(json.dumps({"action": "rewind", "step": n})))
            fresh = walker.replay(path[:n])[1]
            assert after["run"]["path"] == path[:n]
            assert after["run"]["scene"] == fresh[0]
            assert [s["value"] for s in after["stats"]] == list(fresh[1])
            assert sorted(after["run"]["flags"]) == sorted(fresh[2])


def test_rewinding_never_loses_the_map_the_archive_or_the_endings():
    game.game.__init__()
    path = random_walk(3)
    for ch in path:
        game.handle(json.dumps({"action": "choose", "i": int(ch)}))
    full = json.loads(game.handle('{"action": "open"}'))
    back = json.loads(game.handle('{"action": "restart"}'))
    assert back["run"]["path"] == "" and back["run"]["scene"] == story.START
    assert back["progress"] == full["progress"]
    assert back["endings"] == full["endings"] and back["archive"] == full["archive"]
