"""Test helpers."""


def make_sim(C, target="pigeon_museum", crew=("dot", "pip", "bea", "tomasz", "hank"), cells=None, gear=(), seed=1,
             relations=None, preview=False):
    """A Sim for hand-built scenarios. cells = {(lane, beat): action_cell}."""
    import engine
    target_data = C.targets[target]
    plan = engine.empty_plan(len(target_data["beats"]))
    for (lane, beat), cell in (cells or {}).items():
        plan["lanes"][lane][beat] = cell
    return engine.Sim(C, target, list(crew), plan, gear, seed, relations, 0, preview=preview)
