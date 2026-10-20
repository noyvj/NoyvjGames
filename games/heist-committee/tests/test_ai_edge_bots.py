import bots


def test_scouted_kinds_limit_zero(C):
    """scouted_kinds with limit=0 should return an empty list."""
    kinds = bots.scouted_kinds(C, "pigeon_museum", limit=0)
    assert kinds == []


def test_scouted_kinds_limit_exceeds_available(C):
    """scouted_kinds with a large limit should return all available unique kinds without error."""
    kinds = bots.scouted_kinds(C, "the_affineur", limit=100)
    assert len(kinds) > 0
    for k in kinds:
        assert k in C.targets["the_affineur"]["cover_options"]


def test_greedy_plan_standby_false(C):
    """greedy_plan with standby=False should not place any standby actions."""
    crew = ("dot", "pip", "bea", "tomasz", "hank")
    plan = bots.greedy_plan(C, "lucky_barge", crew, standby=False)
    for lane in plan["lanes"]:
        for cell in lane:
            assert not str(cell).startswith("standby:")


def test_greedy_plan_optional_requirements(C):
    """greedy_plan with optional=True should include actions for optional requirements."""
    crew = ("dot", "pip", "bea", "tomasz", "hank")
    plan_opt = bots.greedy_plan(C, "glasshouse_dome", crew, optional=True)
    plan_no_opt = bots.greedy_plan(C, "glasshouse_dome", crew, optional=False)
    count_opt = sum(1 for lane in plan_opt["lanes"] for cell in lane if cell and not str(cell).startswith("standby:"))
    count_no_opt = sum(1 for lane in plan_no_opt["lanes"] for cell in lane if cell and not str(cell).startswith("standby:"))
    assert count_opt >= count_no_opt


def test_random_plan_seed_zero(C):
    """random_plan with seed=0 should produce a valid plan without raising."""
    crew = ("dot", "pip", "bea", "tomasz", "hank")
    plan = bots.random_plan(C, "pigeon_museum", crew, seed=0)
    assert len(plan["lanes"]) == 5


def test_random_plan_large_seed(C):
    """random_plan with a large seed should produce a valid plan without raising."""
    crew = ("dot", "pip", "bea", "tomasz", "hank")
    plan = bots.random_plan(C, "glasshouse_dome", crew, seed=2147483647)
    assert len(plan["lanes"]) == 5
