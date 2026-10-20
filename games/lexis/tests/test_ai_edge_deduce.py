"""Edge-case tests for deduce.py."""


from deduce import Hypothesis, consistent_hypotheses, determinate, disagreements, evaluate
from pulse import PULSE
from world import Station


def test_sem_of_returns_ignore_for_unknown_form():
    hyp = Hypothesis("binary_msb", (("1000", "LAMPS"),))
    assert hyp.sem_of("9999") == "IGNORE"


def test_evaluate_with_empty_marks_returns_unchanged_station():
    hyp = Hypothesis("binary_msb", (("1000", "LAMPS"), ("1001", "DOOR")))
    start = Station(3, "open")
    assert evaluate(hyp, "", start, PULSE) == start


def test_evaluate_with_partial_token_returns_unchanged_station():
    hyp = Hypothesis("binary_msb", (("1000", "LAMPS"), ("1001", "DOOR")))
    start = Station(3, "open")
    # PULSE token length is 4; "10" is incomplete and should be ignored
    assert evaluate(hyp, "10", start, PULSE) == start


def test_consistent_hypotheses_with_empty_scenes_returns_all():
    hyps = consistent_hypotheses(())
    assert len(hyps) > 0
    assert all(isinstance(h, Hypothesis) for h in hyps)


def test_disagreements_with_empty_scenes_is_non_empty():
    # With no scenes, all hypotheses are consistent, so they will disagree on probe messages.
    assert len(disagreements(())) > 0


def test_determinate_with_empty_scenes_is_false():
    assert determinate(()) is False
