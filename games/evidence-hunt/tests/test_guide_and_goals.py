"""The field guide (codex) and the three always-visible goals."""

import achievements
import codex
import game
import lexicon as lx
import progress
from tests.helpers import call, solve_thoroughly, solve_with_hints


def fresh():
    game.game.__init__()
    return call(action="open")


def test_the_guide_has_37_pages_in_five_sections_and_opens_with_a_fiction_notice():
    v = fresh()
    g = v["guide"]
    assert g["total"] == 37 == codex.total() and g["found"] == 0
    assert [(s["id"], s["total"]) for s in g["sections"]] == [("spirits", 12), ("evidence", 6), ("equipment", 6), ("keepsakes", 8), ("notes", 5)]
    assert "invented" in g["notice"] and all(not e["unlocked"] for s in g["sections"] for e in s["entries"])


def test_a_spirit_page_is_filed_only_when_the_case_is_solved_and_never_leaks_the_answer_before():
    fresh()
    call(action="go", room=2)
    call(action="pack", e=1)
    v = call(action="use", e=1)
    assert v["guide"]["found"] == 2, "an evidence page and an equipment page, and no spirit page yet"
    spirits = next(s for s in v["guide"]["sections"] if s["id"] == "spirits")
    assert spirits["found"] == 0 and game.game.seen == {} and game.game.met == []
    v = solve_with_hints()
    spirits = next(s for s in v["guide"]["sections"] if s["id"] == "spirits")
    assert spirits["found"] == 1 and game.game.met == ["hearthkeeper"]
    page = next(e for e in spirits["entries"] if e["id"] == "hearthkeeper")
    assert page["unlocked"] and "?" in page["lines"][0] and "complete" not in page["title"]


def test_evidence_and_equipment_pages_fill_on_first_use():
    fresh()
    call(action="go", room=2)
    call(action="pack", e=1)
    v = call(action="use", e=1)
    sections = {s["id"]: s for s in v["guide"]["sections"]}
    assert sections["evidence"]["found"] == 1 and sections["equipment"]["found"] == 1
    assert game.game.ev == ["charge"] and game.game.eq == ["charge"]


def test_a_thorough_replay_completes_a_spirit_page():
    fresh()
    solve_with_hints()
    v = solve_thoroughly("1-1")
    page = next(e for s in v["guide"]["sections"] if s["id"] == "spirits" for e in s["entries"] if e["id"] == "hearthkeeper")
    assert "complete" in page["title"] and "all confirmed" in page["lines"][0] and v["guide"]["complete"] == 1


def test_house_notes_fill_when_a_chapter_is_done_and_keepsakes_when_returned():
    fresh()
    for cid in progress.CHAPTERS[0]["cases"]:
        call(action="pick", case=cid)
        solve_with_hints()
    v = call(action="open")
    notes = next(s for s in v["guide"]["sections"] if s["id"] == "notes")
    assert notes["found"] == 1 and notes["entries"][0]["unlocked"]
    game.game.best.update({c: 3 for c in progress.ORDER[8:24]})
    call(action="pick", case="4-2")
    v = solve_with_hints()
    assert v["result"]["keepsake"]["name"] == "Music box" and not v["result"]["keepsake"]["returned"]
    v = call(action="return")
    assert v["result"]["keepsake"]["returned"] and game.game.kept == ["musicbox"]
    kept = next(s for s in v["guide"]["sections"] if s["id"] == "keepsakes")
    assert kept["found"] == 1


def test_a_keepsake_can_be_returned_later_from_a_solved_case_and_not_before():
    fresh()
    game.game.best.update({c: 3 for c in progress.ORDER[:24]})
    call(action="pick", case="4-2")
    assert call(action="return")["ok"] is False
    solve_with_hints()
    call(action="pick", case="1-1")
    call(action="pick", case="4-2")
    assert call(action="return")["ok"] is True and game.game.kept == ["musicbox"]


def test_the_cover_toggle_hides_only_complete_pages_and_counts_distinct_cases():
    fresh()
    assert call(action="cover")["case"]["covered"] is True
    v = call(action="open")
    assert v["case"]["covered"] and all(not s["covered"] for s in v["sheet"])
    solve_with_hints()
    assert game.game.mem == ["1-1"]
    solve_thoroughly("1-1")
    call(action="pick", case="1-1")
    call(action="restore")
    v = call(action="cover")
    assert v["case"]["covered"] and any(s["covered"] and not s["evidence"] for s in v["sheet"] if s["id"] == "hearthkeeper")
    assert game.game.mem == ["1-1"], "the same case is not counted twice"


def test_there_are_fourteen_achievements_and_three_goals_in_view_in_manifest_order():
    v = fresh()
    assert len(achievements.ACHIEVEMENTS) == 14 and len(set(achievements.IDS)) == 14
    assert [g["id"] for g in v["goals"]] == ["first_case", "ten_cases", "chapter_closed"]
    assert all(g["have"] == 0 and g["need"] > 0 for g in v["goals"])
    solve_with_hints()
    v = call(action="open")
    assert [g["id"] for g in v["goals"]][0] == "ten_cases" and "first_case" in game.get_state()["achievements_earned"]


def test_goals_that_need_a_later_chapter_wait_until_it_is_open():
    facts = {"done": 0}
    assert all(a["chapter"] < 1 for a in achievements.goals(facts, 1, count=99))
    assert "two_at_once" not in [a["id"] for a in achievements.goals(facts, 2, count=99)]
    assert "two_at_once" in [a["id"] for a in achievements.goals(facts, 3, count=99)]


def test_every_achievement_fact_exists_in_the_games_facts():
    fresh()
    facts = game.game.facts()
    for _i, _l, _d, fact, need, chapter in achievements.ACHIEVEMENTS:
        assert fact in facts and need > 0 and 0 <= chapter < 5
    assert lx.KIND_IDS and facts["pages"] == 0
