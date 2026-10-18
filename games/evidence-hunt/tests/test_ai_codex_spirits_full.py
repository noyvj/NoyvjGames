"""Tests for codex.spirits_full()."""

import codex
import lexicon as lx


def test_spirits_full_returns_zero_when_no_spirits_met():
    met = []
    seen = {}
    assert codex.spirits_full(met, seen) == 0


def test_spirits_full_counts_only_spirits_with_all_three_evidence_confirmed():
    sample_kind = lx.KIND_IDS[0]
    met = [sample_kind]
    seen = {sample_kind: ["cold", "charge", "script"]}
    assert codex.spirits_full(met, seen) == 1


def test_spirits_full_ignores_met_spirits_without_all_evidence():
    k1, k2 = lx.KIND_IDS[0], lx.KIND_IDS[1]
    met = [k1, k2]
    seen = {k1: ["cold", "charge", "script"], k2: ["cold", "charge"]}
    assert codex.spirits_full(met, seen) == 1


def test_spirits_full_edge_case_seen_contains_unmet_kind():
    k1 = lx.KIND_IDS[0]
    unmet_kind = lx.KIND_IDS[1]
    met = [k1]
    seen = {unmet_kind: ["cold", "charge", "script"], k1: ["cold", "charge", "script"]}
    assert codex.spirits_full(met, seen) == 1
