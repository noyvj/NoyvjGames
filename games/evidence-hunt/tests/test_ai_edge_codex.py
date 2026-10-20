"""Edge-case tests for codex.py."""

import codex
import lexicon as lx
import progress


def test_total_returns_expected_constant():
    assert codex.total() == 37


def test_full_handles_missing_kind_and_partial_evidence():
    met = ["hearthkeeper"]
    assert codex.full("hearthkeeper", met, {}) is False
    assert codex.full("hearthkeeper", met, {"hearthkeeper": ["cold", "charge"]}) is False
    assert codex.full("hearthkeeper", met, {"hearthkeeper": ["cold", "charge", "script"]}) is True


def test_counts_with_empty_and_full_inputs():
    best = {}
    assert codex.counts([], [], [], [], best) == (0, 37)
    all_best = {cid: 3 for ch in progress.CHAPTERS for cid in ch["cases"]}
    full_met = list(lx.KIND_IDS)
    full_ev = list(lx.EV_IDS)
    full_eq = list(lx.EV_IDS)
    full_kept = list(lx.KS_IDS)
    assert codex.counts(full_met, full_ev, full_eq, full_kept, all_best) == (37, 37)


def test_spirits_full_with_empty_partial_and_complete_data():
    met = []
    seen = {}
    assert codex.spirits_full(met, seen) == 0
    met = ["hearthkeeper"]
    seen["hearthkeeper"] = ["cold", "charge", "script"]
    assert 0 < codex.spirits_full(met, seen) < len(lx.KIND_IDS)
    full_seen = {k: list(lx.EV_IDS)[:3] for k in lx.KIND_IDS}
    assert codex.spirits_full(lx.KIND_IDS, full_seen) == len(lx.KIND_IDS)


def test_view_structure_and_empty_state():
    v = codex.view([], {}, [], [], [], {})
    assert v["found"] == 0 and v["total"] == 37 and v["complete"] == 0
    assert len(v["sections"]) == 5
    assert all(s["found"] == 0 for s in v["sections"])


def test_view_with_partial_data_reflects_counts():
    met = ["hearthkeeper"]
    seen = {"hearthkeeper": ["cold", "charge"]}
    ev = ["cold"]
    eq = ["cold"]
    kept = []
    best = {}
    v = codex.view(met, seen, ev, eq, kept, best)
    assert v["found"] == 3  # 1 met + 1 ev + 1 eq + 0 kept + 0 notes
    assert v["complete"] == 0
    spirits_sec = next(s for s in v["sections"] if s["id"] == "spirits")
    assert spirits_sec["found"] == 1
    page = next(e for e in spirits_sec["entries"] if e["id"] == "hearthkeeper")
    assert page["unlocked"] is True and "?" in page["lines"][0]


def test_chapter_done_with_empty_and_full_best():
    assert codex.chapter_done({}, 0) is False
    all_best = {cid: 3 for ch in progress.CHAPTERS for cid in ch["cases"]}
    assert codex.chapter_done(all_best, 0) is True
