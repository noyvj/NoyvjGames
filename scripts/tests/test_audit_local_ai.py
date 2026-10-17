"""The pure parts of scripts/audit_local_ai.py: reading commit subjects, scope, tooling, precache and findings."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("audit_local_ai", Path(__file__).resolve().parent.parent / "audit_local_ai.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_subject_gives_the_round_4_id_and_ignores_tooling():
    assert audit.parse_subject("local-ai: R4-LHMO-9: Round 4 idea R4-LHMO-9: Keep four lamp-level buttons") == "R4-LHMO-9"
    assert audit.parse_subject("local-ai: sort_queue.py orders the queue easy to hard") is None
    assert audit.parse_subject("Merge remote-tracking branch 'origin/main'") is None


def test_game_and_scope():
    paths = ["games/herd/app.js", "games/herd/tests/test_x.py"]
    assert audit.game_of(paths) == "herd"
    assert audit.game_of(paths + ["games/thaw/app.js"]) == "*"
    assert audit.game_of(["local-ai/RULES.md"]) == ""
    assert audit.outside_scope(paths + ["shared/seed.js"], "herd") == ["shared/seed.js"]


def test_tooling_commits_only_touch_local_ai_and_dev_logs():
    assert audit.is_tooling(["local-ai/ai.ps1", "BCM206-DEV-LOG.md"])
    assert not audit.is_tooling(["local-ai/ai.ps1", "games/herd/app.js"])
    assert not audit.is_tooling([])


def test_ticked_ids_reads_only_checked_round_4_items():
    text = "- [x] R4-AB-1: done\n  - [ ] R4-AB-2: open\n  - [x] R4-CD-10: done too\n- [x] Z-3a: other list\n"
    assert audit.ticked_ids(text) == {"R4-AB-1", "R4-CD-10"}


def test_precache_check_flags_only_missing_files_inside_the_game_folder():
    html = '<script src="app.js"></script><script src="../../shared/seed.js"></script><link href="../../ad-bar.css"><script src="new.js"></script>'
    sw = '  "games/demo/app.js",\n'
    present = {"games/demo/app.js", "games/demo/new.js", "shared/seed.js", "ad-bar.css"}
    assert audit.missing_precache(html, "demo", sw, lambda p: p in present) == ["games/demo/new.js"]


def test_new_findings_ignore_line_number_shifts_and_the_all_clear_line():
    before = ["games/x/app.js:10 missing-id: no HTML, JS or Python writes id \"a\""]
    after = ["games/x/app.js:14 missing-id: no HTML, JS or Python writes id \"a\"",
             "games/x/app.js:20 hidden-dialog: use it", "static_check: no findings for x"]
    assert audit.new_findings(after, before) == ["games/x/app.js:20 hidden-dialog: use it"]


def test_tick_marks_only_the_named_open_items(tmp_path):
    todo = tmp_path / "TODO-NEXT.md"
    todo.write_text("- [ ] R4-AB-1: a\n  - [ ] R4-AB-2: b\n  - [ ] R4-AB-3: c\n")
    audit.tick(todo, ["R4-AB-1", "R4-AB-3"])
    assert todo.read_text() == "- [x] R4-AB-1: a\n  - [ ] R4-AB-2: b\n  - [x] R4-AB-3: c\n"
