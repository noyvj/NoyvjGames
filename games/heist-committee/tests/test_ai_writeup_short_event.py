
import writeup


def test_short_event_keeps_short_text_unchanged():
    """Normal case: text shorter than limit is returned as-is (minus trailing dots)."""
    assert writeup.short_event("The cat sat on the mat.") == "The cat sat on the mat"


def test_short_event_truncates_long_text_with_ellipsis():
    """Normal case: text exceeding the default limit is truncated and ends with '...'."""
    long_text = "A very long sentence that definitely exceeds the limit of eighty-four characters and then some more text here."
    result = writeup.short_event(long_text)
    assert len(result) == 86
    assert result.endswith("...")


def test_short_event_handles_empty_string():
    """Edge case: an empty string should return an empty string without error."""
    assert writeup.short_event("") == ""
