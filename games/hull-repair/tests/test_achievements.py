import json
from pathlib import Path

import achievements
import boards
import game

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def test_manifest_matches_the_engine_table_and_has_fourteen():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [m["id"] for m in manifest] == list(achievements.IDS) and len(manifest) == 14
    for entry, row in zip(manifest, achievements.ACHIEVEMENTS):
        assert entry == {"id": row[0], "label": row[1], "description": row[2]}


def test_every_achievement_has_a_visible_number_and_none_is_hidden():
    for a in achievements.view({}):
        assert a["need"] >= 1 and a["have"] == 0 and not a["earned"]
    assert "hidden" not in (GAME_DIR / "achievements.json").read_text(encoding="utf-8")


def test_totals_follow_the_game_size():
    by_id = {a[0]: a for a in achievements.ACHIEVEMENTS}
    assert by_id["station_lit"][4] == by_id["hull_whole"][4] == len(boards.ORDER) == 40
    assert by_id["three_decks"][4] < len(boards.CHAPTER_LIST)


def test_nothing_is_time_luck_or_streak_based():
    allowed = {"patched", "restored", "decks_patched", "flag_bridge", "flag_valve", "flag_mix", "flag_retry", "rung3", "laid"}
    for _i, label, description, fact, _n in achievements.ACHIEVEMENTS:
        for word in ("day", "week", "streak", "daily", "minute", "second", "random", "luck"):
            assert word not in description.lower().replace("second thoughts", "").split(), (label, word)
        assert fact in allowed


def test_the_panel_and_toast_are_wired_with_the_hub_hooks():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', 'data-game-name="Hull Repair"'):
        assert needle in HTML
    assert "data-achievement-id" in APP and "data-achievement-label" in APP and "Achievement unlocked: " in APP


def test_earned_ids_are_written_to_the_save_and_never_read_back():
    game.game.__init__()
    game.game.draw.load_answer(boards.ALL_BOARDS[0].solution)
    game.game._record()
    state = game.get_state()
    assert "first_spark" in state["achievements_earned"]
    game.game.__init__()
    game.load_state({"achievements_earned": list(achievements.IDS)})
    v = call(action="open")
    assert v["totals"]["patched"] == 0 and not any(a["earned"] for a in v["achievements"])


def test_a_layout_only_player_earns_every_achievement():
    game.game.__init__()
    for bid in boards.ORDER:
        call(action="pick", board=bid)
        d = game.game.draw
        # take a line back first on one board (Second Thoughts), then lay the stored layout drag by drag
        if bid == boards.ORDER[0]:
            call(action="begin", x=3, y=0)
            call(action="move", cells=[[2, 0]])
            call(action="move", cells=[[3, 0]])
            call(action="end")
        d.load_answer(boards.BY_ID[bid].solution)
        game.game._record()
    for _ in range(3):
        call(action="hint")
    facts = game.game.facts()
    facts["laid"] = max(facts["laid"], 500)
    missing = [a for a in achievements.IDS if a not in achievements.earned(facts)]
    assert missing == []
    assert facts["flag_retry"] == 1 and facts["rung3"] == 1 and facts["decks_patched"] == 5


def test_laying_pipe_counts_toward_pipe_layer():
    game.game.__init__()
    v = call(action="open")
    pipe = [a for a in v["achievements"] if a["id"] == "pipe_layer"][0]
    assert pipe["have"] == 0 and pipe["need"] == 500
    call(action="begin", x=3, y=0)
    call(action="move", cells=[[2, 0]])
    call(action="end")
    assert [a for a in call(action="open")["achievements"] if a["id"] == "pipe_layer"][0]["have"] == 1
