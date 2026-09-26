"""Batch A #4: mastery-rank checklist. Thresholds and per-item points come from
the Warframe Wiki's Mastery Rank page (read 2026-09-27)."""

from .helpers import all_text, click, find_all, known_state


def test_thresholds_match_the_wiki_table(game_env):
    m = game_env.module
    # Rows the Wiki page shows: MR1 2,500 ... MR10 250,000, MR14 490,000
    assert [m.mastery_points_for_rank(r) for r in (1, 2, 3, 10, 14, 30)] == [2500, 10000, 22500, 250000, 490000, 2250000]
    assert m.MASTERY_ITEM_XP == {"weapon": 3000, "frame": 6000}


def test_rank_from_points(game_env):
    m = game_env.module
    assert m.mastery_rank_for_points(0) == 0
    assert m.mastery_rank_for_points(2499) == 0
    assert m.mastery_rank_for_points(2500) == 1
    assert m.mastery_rank_for_points(9999) == 1
    assert m.mastery_rank_for_points(10000) == 2
    assert m.mastery_rank_for_points(2_250_000) == 30
    assert m.mastery_rank_for_points(9_000_000) == 30  # capped
    assert m.mastery_rank_for_points(-5) == 0


def test_items_until_next_rank(game_env):
    m = game_env.module
    m.state["mastery"]["base"] = 10000  # MR2, next rank at 22,500
    status = m.mastery_status()
    assert (status["rank"], status["next_rank"], status["needed"]) == (2, 3, 12500)
    assert (status["weapons"], status["frames"]) == (5, 3)
    assert status["from_list"] is None
    for i in range(5):
        assert m.add_mastery_item(f"W{i}", "weapon")[0] is True
    assert m.mastery_status()["from_list"] == 5
    m.state["mastery"]["items"][0]["done"] = True
    assert m.mastery_total() == 13000
    assert m.mastery_status()["from_list"] == 4  # 9,500 still needed; four more weapons give 12,000


def test_from_list_counts_frames_as_six_thousand(game_env):
    m = game_env.module
    m.state["mastery"]["base"] = 10000
    m.add_mastery_item("Frame A", "frame")
    m.add_mastery_item("Frame B", "frame")
    m.add_mastery_item("Frame C", "frame")
    assert m.mastery_status()["from_list"] == 3  # two frames give 12,000, short of 12,500


def test_rank_thirty_text(game_env):
    m = game_env.module
    m.state["mastery"]["base"] = 2_250_000
    assert "Rank 30 reached" in m.mastery_text()
    assert m.mastery_status()["next_rank"] is None


def test_add_item_validation(game_env):
    m = game_env.module
    assert m.add_mastery_item("", "weapon")[0] is False
    assert m.add_mastery_item("Braton", "sword")[0] is False
    assert m.add_mastery_item("Braton", "weapon")[0] is True
    assert m.add_mastery_item("braton", "weapon")[0] is False
    for i in range(m.MASTERY_ITEM_MAX):
        m.state["mastery"]["items"].append({"n": f"x{i}", "t": "weapon", "done": False})
    assert m.add_mastery_item("one more", "weapon")[0] is False


def test_ui_ticking_and_base_input(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    els["mastery-base-input"].value = "5000"
    els["mastery-base-input"].dispatch("change", None)
    els["mastery-name-input"].value = "Kuva Bramma"
    els["mastery-type-select"].value = "weapon"
    click(els["mastery-add-button"])
    assert [i["n"] for i in m.state["mastery"]["items"]] == ["Kuva Bramma"]
    box = find_all(els["mastery-list"], tag="input")[0]
    box.checked = True
    box.dispatch("change", None)
    assert m.mastery_total() == 8000
    assert "8,000 mastery points: Mastery Rank 1." in els["mastery-summary"].textContent
    click(find_all(els["mastery-list"], tag="button")[0])
    assert m.state["mastery"]["items"] == []
    assert "No items yet" in all_text(els["mastery-list"])


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "mastery" not in m.get_state()
    m.state["mastery"] = {"base": 100, "items": [{"n": "A", "t": "frame", "done": True}]}
    saved = m.get_state()
    m.state["mastery"] = {"base": 0, "items": []}
    m.load_state(saved)
    assert m.state["mastery"] == {"base": 100, "items": [{"n": "A", "t": "frame", "done": True}]}
    m.load_state({"mastery": {"base": -1, "items": [
        {"n": "ok", "t": "weapon", "done": False},
        {"n": "OK", "t": "weapon", "done": False},
        {"n": "bad type", "t": "sword", "done": False},
        {"n": "bad type list", "t": ["x"], "done": False},
        {"n": "no bool", "t": "weapon", "done": 1},
        {"n": "", "t": "weapon", "done": False},
        "junk",
    ]}})
    assert m.state["mastery"] == {"base": 0, "items": [{"n": "ok", "t": "weapon", "done": False}]}
    m.load_state({"mastery": {"base": True, "items": "x"}})
    assert m.state["mastery"] == {"base": 0, "items": []}
    m.load_state({"mastery": []})
    assert m.state["mastery"] == {"base": 0, "items": []}
