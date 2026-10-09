"""The 14 achievements: the manifest the hub reads, the panel the page draws, and that each can be earned."""

import json
from pathlib import Path

import achievements
import game

GAME_DIR = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def test_the_manifest_matches_the_engine_exactly():
    assert [(m["id"], m["label"], m["description"]) for m in MANIFEST] == [(a[0], a[1], a[2]) for a in achievements.ACHIEVEMENTS]
    assert len(MANIFEST) == 14 and len({m["id"] for m in MANIFEST}) == 14


def test_every_achievement_has_a_number_a_real_fact_and_a_reachable_target():
    facts = game.game.facts()
    for i, _label, _desc, fact, need, chapter in achievements.ACHIEVEMENTS:
        assert fact in facts and need > 0 and 0 <= chapter < len(game.progress.CHAPTERS), i
    assert achievements.RECORD_TOTAL > 100 and achievements.TOTAL == 60


def test_nothing_is_hidden_timed_or_luck_based():
    words = " ".join(a[2].lower() for a in achievements.ACHIEVEMENTS)
    for banned in ("hidden", "secret", "within", "minutes", "streak", "daily", "random", "luck"):
        assert banned not in words


def test_the_save_writes_earned_ids_and_never_reads_them_back():
    game.game.__init__()
    game.game.best.update({sid: 3 for sid in game.progress.ORDER[:5]})
    state = game.get_state()
    assert state["achievements_earned"] == ["first_shift", "clean_hands"]
    state["achievements_earned"] = list(achievements.IDS)          # tampering changes nothing
    game.game.__init__()
    game.load_state(state)
    assert game.get_state()["achievements_earned"] == ["first_shift", "clean_hands"]


def test_the_page_draws_the_panel_the_toast_and_the_share_hook():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', "shared/achievement-share.js"):
        assert needle in HTML
    for needle in ("data-achievement-id", "data-achievement-label", "Achievement unlocked: "):
        assert needle in APP


def test_goals_are_the_next_three_unearned_in_open_chapters_and_run_out_gracefully():
    game.game.__init__()
    g = achievements.goals(game.game.facts(), 1)
    assert [x["id"] for x in g] == ["first_shift", "ten_shifts", "chapter_closed"]
    assert achievements.goals({k: 10 ** 6 for k in game.game.facts()}, 8) == []
