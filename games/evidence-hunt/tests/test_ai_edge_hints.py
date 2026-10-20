"""Edge-case tests for hints.py: next_action and describe."""

import json

import pytest

import game
import hints
import lexicon as lx
import progress

FIRST = progress.ORDER[0]


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


@pytest.fixture(autouse=True)
def clean():
    game.game.__init__()
    call(action="difficulty", level="normal")
    yield
    call(action="difficulty", level="normal")
    game.game.__init__()


def test_describe_with_none_act_returns_restore_advice():
    """act=None should always return the restore advice dictionary."""
    call(action="pick", case=FIRST)
    v = hints.describe(game.game.case, game.game.st, None)
    assert v["kind"] == "restore" and v["label"] == "Restore the case"


def test_describe_falls_through_for_unknown_action_kind():
    """An action kind not handled by describe should return the default restore advice."""
    call(action="pick", case=FIRST)
    v = hints.describe(game.game.case, game.game.st, ("fly", 0))
    assert v["kind"] == "restore" and v["label"] == "Restore the case"


def test_describe_pack_smallest_and_largest_equipment_indices():
    """Equipment indices 0 and 5 should produce correct labels without error."""
    call(action="pick", case=FIRST)
    call(action="restore")
    v0 = hints.describe(game.game.case, game.game.st, ("pack", 0))
    assert v0["label"] == "Pack the %s" % lx.GEAR_NAME[0]
    v5 = hints.describe(game.game.case, game.game.st, ("pack", 5))
    assert v5["label"] == "Pack the %s" % lx.GEAR_NAME[5]


def test_describe_use_with_equipment_indices():
    """Use action with equipment indices 0 and 5 should produce correct labels."""
    call(action="pick", case=FIRST)
    call(action="restore")
    v0 = hints.describe(game.game.case, game.game.st, ("use", 0))
    assert v0["label"] == "Use the %s here" % lx.GEAR_NAME[0]
    v5 = hints.describe(game.game.case, game.game.st, ("use", 5))
    assert v5["label"] == "Use the %s here" % lx.GEAR_NAME[5]


def test_describe_accuse_with_single_and_multiple_kinds():
    """Accuse action should format labels correctly for one or more kinds."""
    call(action="pick", case=FIRST)
    call(action="restore")
    # hints.describe expects kind indexes (e.g., 0), not string names.
    v1 = hints.describe(game.game.case, game.game.st, ("accuse", 0))
    assert "Name " in v1["label"]
    v2 = hints.describe(game.game.case, game.game.st, ("accuse", 0, 1))
    assert " and " in v2["label"]


def test_next_action_returns_valid_actions_until_case_done():
    """next_action should return a valid action tuple until the case is finished."""
    call(action="pick", case=FIRST)
    call(action="restore")
    act = hints.next_action(game.game.case, game.game.st)
    assert act is not None
    for _ in range(20):
        if game.game.case.done(game.game.st):
            break
        act = hints.next_action(game.game.case, game.game.st)
        assert act is not None
