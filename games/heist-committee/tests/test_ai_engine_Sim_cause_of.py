import engine


def test_cause_of_returns_max_event_index_for_required_tags(C):
    """cause_of should return the highest event index among tags that are in self.src."""
    sim = engine.Sim(C, "pigeon_museum", ["dot", "pip", "bea", "tomasz", "hank"], engine.empty_plan(3))
    sim.src = {"alarm": 5, "noise": 12}
    comp = {"requires": ["alarm", "noise"], "requires_any": []}
    assert sim.cause_of(comp) == 12


def test_cause_of_handles_requires_any(C):
    """If a complication uses requires_any, cause_of should consider those tags too."""
    sim = engine.Sim(C, "pigeon_museum", ["dot", "pip", "bea", "tomasz", "hank"], engine.empty_plan(3))
    sim.src = {"clear": 3}
    comp = {"requires": [], "requires_any": ["clear", "quiet"]}
    assert sim.cause_of(comp) == 3


def test_cause_of_returns_none_on_missing_or_non_int_sources(C):
    """Edge case: if no required tags are in src, or matching values aren't ints, returns None."""
    sim = engine.Sim(C, "pigeon_museum", ["dot", "pip", "bea", "tomasz", "hank"], engine.empty_plan(3))
    sim.src = {"noise": "not_an_int"}
    comp = {"requires": ["noise"], "requires_any": []}
    assert sim.cause_of(comp) is None
