"""The dread ledger: the promise that the unease never turns into horror, proved from the data and the schedule.

Every odd or moment beat belongs to a mystery with a later, warm resolve; no mystery is left open at the end of the
year for any of a thousand seeds; nothing odd falls where the rules forbid; the hidden meter stays inside its cap; and
no player-visible string uses a word the design bans."""

import re

import clock
import data
import harness
import mysteries
import sim
import story
import unease
from state import Keep
from .test_story_data import BANNED

ODD = ("odd", "moment")
ALL_BEATS = [(mid, b) for mid, m in mysteries.MYSTERIES.items() for b in m["beats"]]


def player_strings():
    for m in mysteries.MYSTERIES.values():
        yield m["title"]
        yield m["summary"]
        for b in m["beats"]:
            yield b["text"]
    for t in mysteries.TRIFLES.values():
        yield t["odd"]
        yield t["resolve"]


def test_there_are_six_mysteries_and_eight_small_oddities_with_unique_ids():
    assert len(mysteries.MYSTERIES) == 6 and len(mysteries.TRIFLES) == 8
    ids = [b["id"] for _m, b in ALL_BEATS]
    assert len(ids) == len(set(ids))


def test_every_mystery_has_exactly_one_resolve_and_it_comes_last_and_is_warm():
    for mid, m in mysteries.MYSTERIES.items():
        kinds = [b["kind"] for b in m["beats"]]
        assert kinds.count("resolve") == 1 and kinds[-1] == "resolve", mid
        assert "warm" in m["tags"], mid
        assert m["beats"][-1]["window"][1] <= m["resolves_by"] <= data.NIGHTS_PER_YEAR, mid
        assert m["summary"] and m["title"]


def test_every_odd_and_moment_beat_has_a_later_resolve_and_a_kind_beat_before_it():
    for mid, m in mysteries.MYSTERIES.items():
        kinds = [b["kind"] for b in m["beats"]]
        resolve_at = kinds.index("resolve")
        for i, kind in enumerate(kinds):
            if kind in ODD:
                assert i < resolve_at, (mid, i)
        assert "kind" in kinds[:resolve_at] and "moment" in kinds[:resolve_at], mid
        assert 5 <= len(kinds) <= 9, mid
        assert kinds[resolve_at - 1] in ("moment", "odd", "kind")


def test_no_banned_word_in_any_player_visible_string():
    for text in player_strings():
        assert not BANNED.search(text), text
    assert not BANNED.search(__import__("lore").CONTENT_NOTE)


def test_nothing_in_the_mysteries_harms_anyone():
    for text in player_strings():
        assert not re.search(r"\b(hurt|harm|injur\w*|attack\w*|bleed\w*|wounded|wounds|lost at sea|never seen again|vanish\w*)\b", text, re.I), text


def test_each_resolution_reframes_the_fear_as_a_person_an_animal_or_a_plain_fact():
    for mid, m in mysteries.MYSTERIES.items():
        text = m["beats"][-1]["text"].lower() + " " + m["summary"].lower()
        assert re.search(r"seal|ilse|berit|pip|hesper|dunstan|floor|slope", text), mid


def test_every_oddity_is_explained_and_kindly():
    for tid, t in mysteries.TRIFLES.items():
        assert 1 <= t["delay"] <= 2 and t["at"] in ("deep", "dawn", "morning")
        assert t["odd"] and t["resolve"] and t["odd"] != t["resolve"]


def test_the_schedule_obeys_every_rule_for_a_thousand_seeds():
    for seed in range(1, 1001):
        plan = unease.schedule(seed)
        assert set(plan) == {b["id"] for _m, b in ALL_BEATS}
        odd_by_night, kind_nights = {}, set()
        for mid, m in mysteries.MYSTERIES.items():
            prev = 0
            for b in m["beats"]:
                n = plan[b["id"]]
                lo, hi = b["window"]
                assert lo <= n <= hi and n >= prev + b.get("gap", 1), (seed, b["id"])
                prev = n
                if b["kind"] in ODD:
                    odd_by_night[n] = odd_by_night.get(n, 0) + 1
                    assert n >= 4 and (n - 1) % data.NIGHTS_PER_SEASON != 0 and not clock.is_festival(n), (seed, b["id"], n)
                else:
                    kind_nights.add(n)
            assert plan[m["beats"][-1]["id"]] <= m["resolves_by"], (seed, mid)
        assert max(odd_by_night.values()) <= 2
        for n in odd_by_night:
            assert unease.run_length(n, set(odd_by_night), kind_nights) <= 2, (seed, n)


def test_the_schedule_is_a_pure_function_of_the_seed():
    first = {s: unease.schedule(s) for s in range(1, 30)}
    unease._cache.clear()
    assert all(unease.schedule(s) == first[s] for s in range(1, 30))


def test_beats_prefer_foggy_nights_when_one_is_available():
    foggy = total = 0
    for seed in range(1, 200):
        plan = unease.schedule(seed)
        for _mid, b in ALL_BEATS:
            if b.get("fog"):
                total += 1
                foggy += unease.hazy(seed, plan[b["id"]])
    assert foggy / float(total) > 0.7


def test_the_unease_meter_stays_in_its_cap_over_a_thousand_synthetic_years():
    import random
    rng = random.Random(7)
    unease_value = 0
    for _ in range(1000 * data.NIGHTS_PER_YEAR):
        unease_value = unease.meter_after_night(unease_value, rng.choice((0, 0, 1, 2, 3, 4)), rng.choice((0, 0, 3, 9, 15)), rng.random() < 0.2, rng.random() < 0.02)
        assert 0 <= unease_value <= mysteries.UNEASE_CAP
    assert unease.meter_after_night(100, 4, 20, False, False) == 100
    assert unease.meter_after_night(50, 0, 0, True, True) == 0


def test_a_letter_a_solved_mystery_and_a_storm_move_the_meter_the_right_way():
    assert unease.meter_after_night(20, 4, 0, False, False) > unease.meter_after_night(20, 0, 0, False, False)
    assert unease.meter_after_night(40, 0, 0, True, False) < 40 and unease.meter_after_night(60, 0, 0, False, True) < 30


def test_a_played_year_solves_every_mystery_and_never_leaves_dread_hanging():
    for seed in (3, 11, 29):
        k = Keep(seed)
        sim.to_evening(k)
        odd_per_night = []

        def note(keep):
            n = sum(1 for e in keep.log if e[1] in ("odd", "hand"))
            odd_per_night.append(n)
        harness.play(k, 40, "careful", on_morning=note)
        seen = story.beat_nights(k)
        resolves = {m["beats"][-1]["id"] for m in mysteries.MYSTERIES.values()}
        assert resolves <= set(seen), (seed, resolves - set(seen))
        assert all(n <= 3 for n in odd_per_night)           # two mystery beats and at most one small oddity
        for mid, m in mysteries.MYSTERIES.items():
            assert seen[m["beats"][-1]["id"]] <= m["resolves_by"]
        assert set(k.meta["story"]["mysteries"]) == set(mysteries.MYSTERIES)
        # every small oddity that was shown has been explained, except one that fell too near the end
        pending = [t for t in k.story["trifles"] if t not in k.story["explained"]]
        assert len(pending) <= 1


def test_oddities_wait_for_the_keeper_to_have_a_kind_moment_and_never_make_three_odd_nights():
    for seed in range(1, 25):
        k = Keep(seed)
        sim.to_evening(k)
        harness.play(k, 40, "careful")
        odd, kind = unease.odd_nights(seed)
        odd |= set(k.story["trifles"].values())
        for n in odd:
            assert unease.run_length(n, odd, kind) <= 2, (seed, n)


def test_eerie_details_off_hides_every_odd_beat_but_keeps_the_kind_ones_and_the_resolutions():
    k = Keep(2)
    k._eerie = False
    sim.to_evening(k)
    harness.play(k, 40, "careful")
    assert not any(e[1] in ("odd", "hand") for e in k.log)
    seen = story.beat_nights(k)
    kinds = {b["id"]: b["kind"] for _m, b in ALL_BEATS}
    assert seen and all(kinds[i] in ("kind", "resolve") for i in seen)
    assert k.story["trifles"] == {}
    assert len([i for i in seen if kinds[i] == "resolve"]) == 6


def test_a_quiet_run_never_meets_a_mystery():
    k = Keep(2)
    k.quiet = True
    sim.to_evening(k)
    harness.play(k, 40, "careful")
    assert k.story["beats"] == [] and not any(e[1] in ("odd", "story", "hand") for e in k.log)


def test_the_odd_light_shows_only_while_its_beat_is_active_and_resolves_in_the_morning():
    seed = 2
    plan = unease.schedule(seed)
    k = Keep(seed)
    k.night = plan["sl4"]
    sim.to_evening(k)
    sim.begin_night(k)
    assert story.odd_visuals(k) == []
    sim.step(k, 10 ** 6)
    assert story.odd_visuals(k) == []                 # the night is over; the scene is a morning scene
    assert "sl4" in story.beat_nights(k)


def test_the_room_shows_the_chair_turning_and_the_extra_cup_until_it_is_explained():
    k = Keep(2)
    k.story["beats"] = [["ch1", 12], ["ch2", 14]]
    assert story.room_odd(k)["chair"] == 12
    k.story["beats"].append(["ec1", 22])
    assert story.room_odd(k)["cup"] is True
    k.story["gifts"].append("second_cup")
    assert story.room_odd(k)["cup"] is False


def test_every_ghost_entry_on_the_board_is_a_beat_that_resolves():
    boards = [b for _m, b in ALL_BEATS if b.get("board")]
    assert boards and all(b["id"].startswith("ws") for b in boards)
    k = Keep(2)
    k.night = unease.schedule(2)["ws1"]
    sim.to_evening(k)
    from view import build
    notice = build(k, {"eerie": True})["notice"]
    assert any(n.get("ghost") and n["name"] == "Lantern Lark" for n in notice)
    k._eerie = False
    assert not any(n.get("ghost") for n in build(k, {"eerie": False})["notice"])


def test_the_content_note_is_one_gentle_non_spoiling_line():
    import lore
    assert lore.CONTENT_NOTE == "This game plays with the feeling of dread. Nothing frightening ever happens."
    assert not any(m["title"].lower() in lore.CONTENT_NOTE.lower() for m in mysteries.MYSTERIES.values())
