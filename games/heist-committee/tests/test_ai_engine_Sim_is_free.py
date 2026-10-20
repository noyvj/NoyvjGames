import content
import engine


DATA = content.load()
TARGET = list(DATA.targets.keys())[0]
CREW = ["dot", "pip", "bea", "tomasz", "hank"]


def test_is_free_returns_true_for_standby_lane():
    """A crew member in a standby lane at beat 0 is free to help."""
    plan = {"lanes": [["standby:noise"] + [None] * 9 for _ in range(5)]}
    sim = engine.Sim(DATA, TARGET, CREW, plan, seed=1)
    assert sim.is_free(0, 0) is True


def test_is_free_returns_false_for_busy_task_lane():
    """A crew member in the middle of a task at beat 0 cannot help."""
    valid_action = next(k for k in DATA.actions if DATA.actions[k]["kind"] == "task")
    plan = {"lanes": [[valid_action] + [None] * 9 for _ in range(5)]}
    sim = engine.Sim(DATA, TARGET, CREW, plan, seed=1)
    assert sim.is_free(0, 0) is False


def test_is_free_returns_false_when_sidelined():
    """A sidelined crew member is never free, regardless of their plan slot."""
    plan = {"lanes": [["standby:noise"] + [None] * 9 for _ in range(5)]}
    sim = engine.Sim(DATA, TARGET, CREW, plan, seed=1)
    sim.sidelined[2] = 5  # Sidelined until beat 6
    assert sim.is_free(2, 0) is False
