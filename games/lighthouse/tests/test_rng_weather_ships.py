"""The generators are pure functions of the seed: same inputs, same weather and ships, in any order."""

import collections

import clock
import data
import rng
import ships
import weather


def test_rng_is_deterministic_and_in_range():
    assert rng.unit(1, "a", 2) == rng.unit(1, "a", 2)
    assert rng.unit(1, "a", 2) != rng.unit(1, "a", 3)
    values = [rng.unit(7, i) for i in range(2000)]
    assert all(0.0 <= v < 1.0 for v in values)
    assert 0.45 < sum(values) / len(values) < 0.55
    assert {rng.rint(3, 5, 9, i) for i in range(200)} == {3, 4, 5}
    assert rng.pick("abc", 1, 2) in "abc"


def test_rng_order_and_type_matter_but_negative_and_text_parts_work():
    assert rng.mix(1, 2) != rng.mix(2, 1)
    assert rng.mix(-5) != rng.mix(5)
    assert rng.mix("x") != rng.mix("y")


def test_weighted_respects_weights():
    got = collections.Counter(rng.weighted("ab", (9, 1), 4, i) for i in range(2000))
    assert got["a"] > 1600 and got["b"] > 100


def test_weather_is_deterministic_and_well_formed():
    for seed in (1, 2, 99):
        for night in range(1, 121):
            a, b = weather.weather(seed, night), weather.weather(seed, night)
            assert a.cond == b.cond and a.wind == b.wind
            assert len(a.cond) == len(a.wind) == clock.night_len(night)
            assert all(0 <= c <= 4 for c in a.cond) and all(0 <= w <= 4 for w in a.wind)


def test_weather_does_not_depend_on_call_order():
    first = {n: weather.weather(5, n).cond[:] for n in range(1, 30)}
    weather._cache.clear()
    for n in reversed(range(1, 30)):
        assert weather.weather(5, n).cond == first[n]


def test_severity_shapes_the_night():
    seen = set()
    for night in range(1, 400):
        w = weather.weather(3, night)
        seen.add(w.severity)
        if w.severity == 3:
            assert 4 in w.cond and 3 in w.cond
        if w.severity == 2:
            assert 2 in w.cond or 3 in w.cond
        if w.severity == 0:
            assert max(w.cond) <= 1
        if w.severity == 1:
            assert max(w.cond) <= 2 and (1 in w.cond or 2 in w.cond)
    assert seen == {0, 1, 2, 3}


def test_gentle_first_nights_and_a_calm_festival_every_year():
    for seed in range(1, 40):
        assert weather.severity(seed, 1) == 0
        assert weather.severity(seed, 2) <= 1 and weather.severity(seed, 3) <= 1
        for year in range(4):
            night = year * data.NIGHTS_PER_YEAR + data.FESTIVAL_NIGHT
            assert clock.is_festival(night)
            assert weather.weather(seed, night).cond == [0] * clock.night_len(night)


def test_seasons_change_the_odds():
    def rate(season, sev):
        nights = [n for n in range(1, 801) if clock.season_of(n) == season and not clock.is_festival(n) and n > 3]
        return sum(1 for n in nights if weather.severity(11, n) >= sev) / float(len(nights))
    assert rate(3, 3) > rate(1, 3)           # winter has more storms than summer
    assert rate(1, 1) < rate(2, 1)           # summer is calmer than autumn


def test_the_barometer_is_truthful_on_average_and_wrong_sometimes():
    for vane, floor in ((False, 0.88), (True, 0.94)):
        hits = wrong = narrow = 0
        for night in range(1, 1501):
            lo, hi = weather.forecast(8, night, vane)
            assert 0 <= lo <= hi <= 3 and hi - lo <= 1
            truth = weather.severity(8, night)
            hits += lo <= truth <= hi
            wrong += not (lo <= truth <= hi)
            narrow += lo == hi
        assert hits / 1500.0 >= floor
        assert wrong > 0                      # "wrong sometimes", it is a judgment call
        assert (narrow > 0) == vane           # only the vane ever narrows the band to one step


def test_clock_labels_and_blocks():
    assert clock.clock_label(1, 0) == "20:00"
    assert clock.clock_label(1, 6) == "21:00"
    assert clock.night_len(1) == 42 and clock.night_len(11) == 36 and clock.night_len(21) == 48 and clock.night_len(31) == 56
    for night in (1, 11, 21, 31):
        length = clock.night_len(night)
        assert [clock.block_of(night, t) for t in range(length)] == sorted(clock.block_of(night, t) for t in range(length))
        assert clock.block_of(night, clock.block_end(night, 0)) == 1
        assert clock.block_end(night, 2) == length
    assert 0 <= clock.darkness(1, 0) < clock.darkness(1, 21) <= 1


def test_ships_are_deterministic_and_inside_the_night():
    for seed in (1, 4):
        for night in range(1, 100):
            mail = ships.mail_scheduled(seed, night)
            a, b = ships.ships_for_night(seed, night, mail), ships.ships_for_night(seed, night, mail)
            assert a == b
            length = clock.night_len(night)
            for s in a:
                assert 0 <= s["arrive"] and s["arrive"] + s["window"] <= length - 1
                assert s["kind"] in data.SHIP_KINDS and s["need"] == data.SHIP_KINDS[s["kind"]]["need"]
            assert [s["arrive"] for s in a] == sorted(s["arrive"] for s in a)
            assert len({s["id"] for s in a}) == len(a)


def test_festival_nights_have_no_ships_and_the_first_night_has_company():
    for seed in range(1, 20):
        assert ships.ships_for_night(seed, 20) == []
        assert len(ships.ships_for_night(seed, 1)) >= 2


def test_the_mail_boat_comes_first_on_night_three_then_every_three_to_five_nights():
    for seed in range(1, 30):
        nights = ships.mail_nights_before(seed, 200)
        assert nights[0] == 3
        gaps = [b - a for a, b in zip(nights, nights[1:])]
        assert gaps and all(3 <= g <= 5 for g in gaps)
        assert ships.next_mail_night(seed, 3) == nights[1]
        with_mail = ships.ships_for_night(seed, 3, True)
        assert sum(1 for s in with_mail if s["kind"] == "mail") == 1
        assert not any(s["kind"] == "mail" for s in ships.ships_for_night(seed, 3, False))


def test_ship_kinds_follow_the_season():
    def share(season, kind):
        total = count = 0
        for night in range(1, 600):
            if clock.season_of(night) != season:
                continue
            for s in ships.ships_for_night(2, night):
                total += 1
                count += s["kind"] == kind
        return count / float(total)
    assert share(3, "cargo") > share(1, "cargo")
    assert share(1, "yacht") > share(3, "yacht")
    assert share(3, "yacht") == 0.0
