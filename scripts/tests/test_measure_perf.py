"""The pure parts of scripts/measure-perf.py (Z-12): the 20% rule and the budget file's shape.
The measuring itself needs a browser and a running dev server, so it is run by hand."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("measure_perf", ROOT / "scripts" / "measure-perf.py")
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)

BUDGET = {"pyodide_ms": 4000, "first_interactive_ms": 5000, "own_kb": 400, "total_kb": 6000}


def test_within_twenty_percent_passes():
    measured = {"pyodide_ms": 4700, "first_interactive_ms": 5900, "own_kb": 470, "total_kb": 7100}
    assert mp.over_budget(measured, BUDGET) == []


def test_more_than_twenty_percent_over_fails_and_names_the_metric():
    measured = dict(BUDGET, first_interactive_ms=6200, own_kb=500)
    bad = {m[0] for m in mp.over_budget(measured, BUDGET)}
    assert bad == {"first_interactive_ms", "own_kb"}


def test_tiny_absolute_changes_are_noise():
    small = {"own_kb": 10}
    assert mp.over_budget({"own_kb": 13}, small) == []          # +30%, but only 3 KB
    assert mp.over_budget({"own_kb": 40}, small)                # real growth


def test_missing_metrics_are_skipped_not_failed():
    assert mp.over_budget({"pyodide_ms": 100}, BUDGET) == []
    assert mp.over_budget(BUDGET, {}) == []


def test_committed_budget_covers_every_game_with_every_budgeted_metric():
    path = ROOT / "scripts" / "perf-budget.json"
    assert path.exists(), "run python3 scripts/measure-perf.py once to create the baseline"
    games = json.loads(path.read_text())["games"]
    for slug in mp.game_slugs():
        assert slug in games, "no perf budget for " + slug
        for key in mp.BUDGETED:
            assert isinstance(games[slug].get(key), (int, float)) and games[slug][key] > 0, (slug, key)


def test_service_worker_repeat_visit_that_still_downloads_pyodide_fails_loudly():
    assert mp.sw_problems("sol", {"sw_cdn_kb": 0.0}) == []
    assert mp.sw_problems("sol", {"sw_cdn_kb": mp.SW_REPEAT_CDN_LIMIT_KB}) == []
    bad = mp.sw_problems("sol", {"sw_cdn_kb": 5400.0})
    assert len(bad) == 1 and "sol" in bad[0] and "5400" in bad[0]
    assert mp.sw_problems("sol", {"sw_note": "the service worker kept only 0 runtime files"})
    assert mp.sw_problems("sol", {}) == []        # not measured this run: nothing to judge


def test_old_report_rows_are_read_back_in_both_layouts(tmp_path, monkeypatch):
    report = tmp_path / "PERF-BUDGET.md"
    report.write_text("\n".join([
        "| Game | a | b | c | d | e | f |", "|---|---|---|---|---|---|---|",
        "| old | 1173 | 1422 | 367 | 5807 | 1161 | 1422 / 5807 |",
        "| new | 1000 | 1200 | 300 | 5700 | 900 | 2400 / 0 | 1200 / 5700 |",
        "| gone | not measured | | | | | | |",
    ]), encoding="utf-8")
    monkeypatch.setattr(mp, "REPORT_FILE", report)
    rows = mp.read_old_rows()
    assert rows["old"] == {"pyodide_ms": 1173, "first_interactive_ms": 1422, "own_kb": 367,
                           "total_kb": 5807, "warm_first_interactive_ms": 1161}
    assert rows["new"]["sw_first_interactive_ms"] == 2400 and rows["new"]["sw_cdn_kb"] == 0
    assert "gone" not in rows


def test_the_report_names_the_service_worker_cache():
    text = (ROOT / "planning" / "PERF-BUDGET.md").read_text(encoding="utf-8")
    assert "With service worker" in text and "runtime-cdn-cache-v1" in text
