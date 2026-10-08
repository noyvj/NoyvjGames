"""shared/migrate.py (TODO Z-9): the save-schema version registry and chain, plus a fixture test
that pushes a real save of EVERY game through it.

Fixtures live in shared/tests/fixtures/saves/ and were produced by scripts/generate-save-fixtures.py
from each game's own `get_state()` (booted through its own fake-DOM test harness): `<game>.fresh.json`
is a brand-new game, `<game>.json` a seeded mid-game save. They are HISTORY, not a mirror of the
current code: when a game changes its save shape, keep the old file and add the new shape beside
it. No game has a registered migration yet, so every one of these (version 0, no `schema_version`)
must come back from `migrate()` unchanged, and must still load through the game's own
`load_state()` and give a clean, stable state back."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import migrate  # noqa: E402
import smoke_support as ss  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "saves"
FIXTURE_FILES = sorted(FIXTURES.glob("*.json"))


@pytest.fixture
def scratch_registry():
    """A clean registry for the unit tests; the real one is restored afterwards."""
    saved_registry, saved_versions = dict(migrate._REGISTRY), dict(migrate.CURRENT_VERSIONS)
    migrate._REGISTRY.clear()
    migrate.CURRENT_VERSIONS.clear()
    yield migrate
    migrate._REGISTRY.clear()
    migrate._REGISTRY.update(saved_registry)
    migrate.CURRENT_VERSIONS.clear()
    migrate.CURRENT_VERSIONS.update(saved_versions)


# -- the chain ---------------------------------------------------------------------------------

def test_real_registry_is_consistent_and_every_game_currently_reads_version_zero():
    assert migrate.audit() == []
    for slug in ss.ALL_GAMES:
        assert migrate.current_version(slug) == 0 or migrate.registered(slug), slug


def test_unversioned_save_of_a_version_zero_game_comes_back_untouched(scratch_registry):
    save = {"funds": 5, "plots": [1, 2]}
    out = migrate.migrate("toy", save)
    assert out is save and out == {"funds": 5, "plots": [1, 2]} and "schema_version" not in out
    assert migrate.stamp("toy", {"a": 1}) == {"a": 1}             # version 0: not stamped


def test_steps_chain_in_order_and_stamp_the_version(scratch_registry):
    @migrate.register("toy", 0)
    def v0_to_v1(save):
        save["coins"] = save.pop("gold")
        return save

    @migrate.register("toy", 1)
    def v1_to_v2(save):
        save["coins"] = save["coins"] * 10
        return save

    migrate.CURRENT_VERSIONS["toy"] = 2
    old = {"gold": 4}
    out = migrate.migrate("toy", old)
    assert out == {"coins": 40, "schema_version": 2}
    assert old == {"gold": 4}                                      # the argument is never edited
    # Starting midway runs only the remaining steps.
    assert migrate.migrate("toy", {"coins": 3, "schema_version": 1}) == {"coins": 30, "schema_version": 2}
    # Already current: same object back.
    current = {"coins": 1, "schema_version": 2}
    assert migrate.migrate("toy", current) is current
    assert migrate.stamp("toy", {"coins": 1}) == {"coins": 1, "schema_version": 2}
    assert migrate.audit() == []


def test_audit_reports_gaps_and_stray_steps(scratch_registry):
    migrate.CURRENT_VERSIONS["toy"] = 2
    migrate.register("toy", 0)(lambda s: s)
    assert any("from version 1 to 2" in p for p in migrate.audit("toy"))
    migrate.register("toy", 1)(lambda s: s)
    migrate.register("toy", 2)(lambda s: s)
    assert any("at or beyond" in p for p in migrate.audit("toy"))


def test_registering_a_step_twice_is_refused(scratch_registry):
    migrate.register("toy", 0)(lambda s: s)
    with pytest.raises(ValueError):
        migrate.register("toy", 0)(lambda s: s)
    with pytest.raises(ValueError):
        migrate.register("toy", -1)


@pytest.mark.parametrize("bad", [None, [], "text", 4, True])
def test_a_non_object_save_is_a_migration_error(bad):
    with pytest.raises(migrate.MigrationError):
        migrate.migrate("grid", bad)


@pytest.mark.parametrize("version", ["1", -1, 1.5, True, None])
def test_a_bad_schema_version_is_a_migration_error(version):
    with pytest.raises(migrate.MigrationError):
        migrate.migrate("grid", {"schema_version": version})


def test_a_save_from_a_newer_build_is_refused_with_the_raw_data(scratch_registry):
    migrate.CURRENT_VERSIONS["toy"] = 1
    migrate.register("toy", 0)(lambda s: s)
    save = {"schema_version": 5, "x": 1}
    with pytest.raises(migrate.MigrationError) as info:
        migrate.migrate("toy", save)
    assert info.value.save is save and info.value.version == 5 and "newer" in str(info.value)


def test_a_missing_or_crashing_step_fails_without_touching_the_original(scratch_registry):
    migrate.CURRENT_VERSIONS["toy"] = 2
    migrate.register("toy", 0)(lambda s: dict(s, ok=True))
    save = {"x": 1}
    with pytest.raises(migrate.MigrationError) as info:                 # nothing from 1 to 2
        migrate.migrate("toy", save)
    assert info.value.version == 1 and save == {"x": 1}

    migrate.register("toy", 1)(lambda s: s["nope"])
    with pytest.raises(migrate.MigrationError) as info:                 # step 1 raises KeyError
        migrate.migrate("toy", save)
    assert info.value.version == 1 and "KeyError" in str(info.value) and save == {"x": 1}


def test_a_step_that_returns_something_else_fails(scratch_registry):
    migrate.CURRENT_VERSIONS["toy"] = 1
    migrate.register("toy", 0)(lambda s: None)
    with pytest.raises(migrate.MigrationError):
        migrate.migrate("toy", {"x": 1})


def test_safe_migrate_gives_the_raw_code_screen_what_it_needs(scratch_registry):
    migrate.CURRENT_VERSIONS["toy"] = 1
    migrate.register("toy", 0)(lambda s: s["nope"])
    ok, out, failure = migrate.safe_migrate("toy", {"b": 2, "a": 1})
    assert ok is False and out is None
    assert failure["game"] == "toy" and failure["stopped_at_version"] == 0
    assert json.loads(failure["raw"]) == {"a": 1, "b": 2}               # exact original, copyable
    ok, out, failure = migrate.safe_migrate("toy", {"schema_version": 1, "z": 0})
    assert ok is True and out == {"schema_version": 1, "z": 0} and failure is None
    ok, _, failure = migrate.safe_migrate("toy", "not a save")
    assert ok is False and failure["game"] == "toy" and "JSON object" in failure["message"]


# -- every game's historic save ----------------------------------------------------------------

def test_every_game_has_both_fixtures():
    names = {p.name for p in FIXTURE_FILES}
    for slug in ss.ALL_GAMES:
        assert slug + ".json" in names and slug + ".fresh.json" in names, slug


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.name)
def test_fixture_passes_through_migrate_unchanged(path):
    slug = path.name.split(".")[0]
    save = json.loads(path.read_text(encoding="utf8"))
    before = copy.deepcopy(save)
    assert migrate.version_of(save) == 0
    out = migrate.migrate(slug, save)
    assert out == before and out is save and "schema_version" not in out
    ok, out2, failure = migrate.safe_migrate(slug, save)
    assert ok and out2 == before and failure is None
    assert ss.state_problems(save, signed_ok=".*") == []               # clean JSON, no NaN


def _load_into_game(slug, data):
    """Boot the game, feed it the save through its own load_state(), return (result, state_after)."""
    if slug in ss.FAKE_DOM_GAMES:
        with ss.fake_dom_game(slug) as env:
            result = env.module.load_state(copy.deepcopy(data))
            after = json.loads(json.dumps(env.module.get_state()))
            env.module.load_state(copy.deepcopy(after))
            again = json.loads(json.dumps(env.module.get_state()))
        return result, after, again
    with ss.engine_game(slug) as (call, get_state, next_request):
        module = _engine_module(slug)
        result = module.load_state(copy.deepcopy(data))
        after = json.loads(json.dumps(get_state()))
        module.load_state(copy.deepcopy(after))
        again = json.loads(json.dumps(get_state()))
    return result, after, again


def _engine_module(slug):
    name = {"signal": "signal_game"}.get(slug, "game")
    return sys.modules[name]


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.name)
def test_fixture_still_loads_into_its_game(path):
    """Each game's own load_state() accepts the migrated save, keeps every top-level key it was
    given, and a second save/load round trip changes nothing (so the load is stable)."""
    slug = path.name.split(".")[0]
    data = migrate.migrate(slug, json.loads(path.read_text(encoding="utf8")))
    result, after, again = _load_into_game(slug, data)
    assert result is not False, "load_state refused the save"
    assert ss.state_problems(after, signed_ok=".*") == []
    assert set(data) <= set(after), "load dropped top-level keys: %s" % sorted(set(data) - set(after))
    assert after == again, "load_state(get_state()) is not stable"
