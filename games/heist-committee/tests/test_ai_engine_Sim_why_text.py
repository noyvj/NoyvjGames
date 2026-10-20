import engine


def test_why_text_positive_margin(C):
    """Normal case: positive margin with multiple modifiers."""
    sim = engine.Sim(C, "pigeon_museum", C.crew_order[:5], engine.empty_plan(3))
    parts = [("Skill", 2), ("Trait bonus", 1)]
    margin = 3
    result = sim.why_text(parts, margin)
    assert result == "Skill +2; Trait bonus +1 = +3 (Solid)"


def test_why_text_negative_margin(C):
    """Normal case: negative margin with a single modifier."""
    sim = engine.Sim(C, "pigeon_museum", C.crew_order[:5], engine.empty_plan(3))
    parts = [("No clear tag", -2)]
    margin = -1
    result = sim.why_text(parts, margin)
    assert result == "No clear tag -2 = -1 (Long shot)"


def test_why_text_zero_margin_empty_parts(C):
    """Edge case: zero margin with no modifiers."""
    sim = engine.Sim(C, "pigeon_museum", C.crew_order[:5], engine.empty_plan(3))
    parts = []
    margin = 0
    result = sim.why_text(parts, margin)
    assert result == " = +0 (Risky)"
