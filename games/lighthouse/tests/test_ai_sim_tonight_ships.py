"""Tests for sim.tonight_ships()."""

import json

import game
import sim
from state import Keep  # noqa: E402


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


def test_tonight_ships_returns_deterministic_list_for_given_seed_and_night():
    k = Keep(42)
    k.night = 1
    k.mail_tonight = False
    ships1 = sim.tonight_ships(k)

    k2 = Keep(42)
    k2.night = 1
    k2.mail_tonight = False
    ships2 = sim.tonight_ships(k2)

    assert isinstance(ships1, list) and isinstance(ships2, list)
    for s in ships1 + ships2:
        assert "id" in s and "kind" in s
    assert len(ships1) == len(ships2)


def test_tonight_ships_includes_mail_boat_when_mail_tonight_is_true():
    k = Keep(42)
    k.night = 5
    k.mail_tonight = False
    ships_no_mail = sim.tonight_ships(k)

    k.mail_tonight = True
    ships_with_mail = sim.tonight_ships(k)

    has_mail_no = any(s["kind"] == "mail" for s in ships_no_mail)
    has_mail_yes = any(s["kind"] == "mail" for s in ships_with_mail)
    assert not has_mail_no and has_mail_yes


def test_tonight_ships_caches_and_regenerates_on_key_change():
    k = Keep(42)
    k.night = 1
    k.mail_tonight = False

    first_call = sim.tonight_ships(k)
    second_call = sim.tonight_ships(k)

    assert first_call is second_call

    k.night = 2
    third_call = sim.tonight_ships(k)
    assert third_call is not first_call
