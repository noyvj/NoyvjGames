import engine


def _make_sim(C):
    return engine.Sim(C, "pigeon_museum", ["dot"], {"lanes": [[None]]}, seed=0)


def test_fmt_substitutes_single_key(C):
    """Sim.fmt replaces a single placeholder correctly."""
    sim = _make_sim(C)
    result = sim.fmt("{crew} is ready.", crew="Dot")
    assert result == "Dot is ready."


def test_fmt_substitutes_multiple_keys(C):
    """Sim.fmt replaces multiple placeholders correctly."""
    sim = _make_sim(C)
    result = sim.fmt("{a} and {b} are here.", a="Pip", b="Bea")
    assert result == "Pip and Bea are here."


def test_fmt_falls_back_on_missing_key(C):
    """Sim.fmt returns the original template if a key is missing."""
    sim = _make_sim(C)
    result = sim.fmt("{crew} is {status}.", crew="Dot")
    assert result == "{crew} is {status}."
