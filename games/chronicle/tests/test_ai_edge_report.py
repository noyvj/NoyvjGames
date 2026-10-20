"""Edge-case tests for report.py build function."""

from types import SimpleNamespace
from report import build, MAX_NOTE


def _make_cset(claims=None, sources=None):
    """Create a mock ChronicleSet-like object."""
    return SimpleNamespace(
        id="test-set",
        version=1,
        status="draft",
        claims=claims or {},
        sources=sources or {}
    )


def _make_claim(claim_id="c1"):
    """Create a mock claim dictionary."""
    return {
        "id": claim_id,
        "text": "Test claim text.",
        "confidence": "documented",
        "sources": [{"source": "s1"}]
    }


class TestBuildEdgeCases:
    """Test limits and edge cases for report.build."""

    def test_build_missing_claim_returns_error(self):
        """Passing a non-existent claim ID should return an error."""
        cset = _make_cset()
        payload, error = build(cset, "nonexistent", "wrong_fact", "")
        assert error is not None
        assert payload is None

    def test_build_invalid_reason_returns_error(self):
        """Passing a reason not in REASON_IDS should return an error."""
        cset = _make_cset(claims={"c1": _make_claim()})
        payload, error = build(cset, "c1", "invalid_reason", "")
        assert error == "Pick a reason first."
        assert payload is None

    def test_build_note_empty_string(self):
        """An empty note string should be accepted and stored as empty."""
        cset = _make_cset(claims={"c1": _make_claim()}, sources={"s1": {"url": "https://example.com"}})
        payload, error = build(cset, "c1", "wrong_fact", "")
        assert error is None
        assert payload["note"] == ""

    def test_build_note_at_max_length(self):
        """A note exactly at MAX_NOTE length should be accepted."""
        cset = _make_cset(claims={"c1": _make_claim()}, sources={"s1": {"url": "https://example.com"}})
        long_note = "x" * MAX_NOTE
        payload, error = build(cset, "c1", "wrong_fact", long_note)
        assert error is None
        assert payload["note"] == long_note

    def test_build_note_over_max_length(self):
        """A note exceeding MAX_NOTE length should be rejected."""
        cset = _make_cset(claims={"c1": _make_claim()}, sources={"s1": {"url": "https://example.com"}})
        too_long_note = "x" * (MAX_NOTE + 1)
        payload, error = build(cset, "c1", "wrong_fact", too_long_note)
        assert error is not None
        assert payload is None

    def test_build_valid_payload_structure(self):
        """A valid input should return a correctly structured payload."""
        cset = _make_cset(claims={"c1": _make_claim()}, sources={"s1": {"url": "https://example.com"}})
        payload, error = build(cset, "c1", "wrong_fact", "A note.")
        assert error is None
        assert payload["kind"] == "chronicle-claim-report"
        assert payload["set_id"] == "test-set"
        assert payload["set_version"] == 1
        assert payload["set_status"] == "draft"
        assert payload["claim_id"] == "c1"
        assert payload["claim_text"] == "Test claim text."
        assert payload["confidence"] == "documented"
        assert payload["source_urls"] == ["https://example.com"]
        assert payload["reason"] == "wrong_fact"
        assert payload["note"] == "A note."

    def test_build_non_string_claim_id(self):
        """Passing a non-string claim ID should be treated as missing."""
        cset = _make_cset(claims={"c1": _make_claim()})
        payload, error = build(cset, 123, "wrong_fact", "")
        assert error is not None
        assert payload is None
