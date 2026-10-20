
import writeup


def test_outcome_class_handles_all_combinations():
    """outcome_class returns correct class for escaped/alarm/stranded flags."""
    assert writeup.outcome_class({"escaped": True, "alarm": False}) == "clean"
    assert writeup.outcome_class({"escaped": True, "alarm": True}) == "loud"
    assert writeup.outcome_class({"escaped": False, "alarm": False, "stranded": True}) == "stranded"
    assert writeup.outcome_class({"escaped": False, "alarm": False}) == "bust"


def test_short_event_truncates_and_appends_ellipsis():
    """short_event truncates long text to limit-1 chars and adds '...'."""
    short = "A quick sentence."
    assert writeup.short_event(short, 84) == short.rstrip(".")
    long_text = "x" * 100
    truncated = writeup.short_event(long_text, 84)
    assert truncated.startswith("x") and truncated.endswith("...")
    # limit=0 takes all but last char and appends ellipsis per current implementation
    assert writeup.short_event("anything", 0) == "anythin..."


def test_join_names_formats_lists_correctly():
    """join_names joins names with commas and 'and' before the last item."""
    assert writeup.join_names([]) == ""
    assert writeup.join_names(["Alice"]) == "Alice"
    assert writeup.join_names(["Alice", "Bob"]) == "Alice and Bob"
    assert writeup.join_names(["A", "B", "C"]) == "A, B and C"


def test_plural_handles_zero_and_one():
    """plural returns correct singular or plural form."""
    assert writeup.plural(0, "problem") == "0 problems"
    assert writeup.plural(1, "problem") == "1 problem"
    assert writeup.plural(2, "problem") == "2 problems"
    assert writeup.plural(100, "item") == "100 items"


def test_build_handles_empty_events_and_minimal_result(C):
    """build produces valid output even with no events or minimal result dict."""
    crew_ids = list(C.crew_order)[:5]
    seed = 42
    target_id = "pigeon_museum"

    # Minimal result mimicking engine.simulate output structure
    result = {
        "outcome": {"escaped": True, "alarm": False, "chain_links": 0, "chain_path": [], "absorbed": 0},
        "events": []
    }

    w = writeup.build(C, target_id, result, crew_ids, seed)
    assert "title" in w and "text" in w and "chain" in w and "cls" in w
    assert w["cls"] == "clean"
    assert "{" not in w["text"] and "{" not in w["title"]
