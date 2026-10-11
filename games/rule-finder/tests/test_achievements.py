import json
from pathlib import Path

import achievements
import cases
import game
import lang

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


def test_the_plans_fourteen_names_are_all_there():
    labels = {a[1] for a in achievements.ACHIEVEMENTS}
    assert labels == {"First Gate", "Eight Named", "Twenty-Four Named", "All Forty-Eight", "Drawer Closed", "Four Drawers", "Quick Eye", "At Par",
                      "Counter-Example", "Both Ways", "Patient Hands", "Shape Reader", "Odd Gate Open", "Full Codex"}


def test_every_achievement_has_a_visible_number_and_none_is_hidden():
    for a in achievements.view({}):
        assert a["need"] >= 1 and a["have"] == 0 and not a["earned"]
    assert "hidden" not in (GAME_DIR / "achievements.json").read_text(encoding="utf-8")


def test_totals_follow_the_game_size():
    by_id = {a[0]: a for a in achievements.ACHIEVEMENTS}
    assert by_id["all_forty_eight"][4] == by_id["full_codex"][4] == len(cases.ORDER) == 48
    assert by_id["four_drawers"][4] < len(cases.DRAWER_LIST) and by_id["shape_reader"][4] == len(cases.DRAWER_LIST[1]["cases"])


def test_nothing_is_time_luck_or_streak_based():
    allowed = {"named", "drawers_closed", "quick", "clean", "counter", "both", "tests", "shapes_drawer", "odd_drawer", "read"}
    for _i, label, description, fact, _n in achievements.ACHIEVEMENTS:
        for word in ("day", "week", "streak", "daily", "minute", "second", "random", "luck"):
            assert word not in description.lower().split(), (label, word)
        assert fact in allowed


def test_the_panel_toast_and_share_button_are_wired_with_the_hub_hooks():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', 'data-game-name="Rule Finder"', "achievement-share.js"):
        assert needle in HTML
    assert "data-achievement-id" in APP and "data-achievement-label" in APP and "Achievement unlocked: " in APP


def test_earned_ids_are_written_to_the_save_and_never_read_back():
    game.game.__init__()
    game.game._enter("latch")
    call(action="name", rule=lang.rule_json(cases.BY_ID["latch"].rule))
    state = game.get_state()
    assert "first_gate" in state["achievements_earned"] and "quick_eye" in state["achievements_earned"]
    game.game.__init__()
    game.load_state({"achievements_earned": list(achievements.IDS)})
    v = call(action="open")
    assert v["totals"]["named"] == 0 and not any(a["earned"] for a in v["achievements"])


def _name_on_the_shortest_path(cid):
    """What a perfect player does: send exactly the shortest-path tests, then name the rule."""
    c = cases.BY_ID[cid]
    call(action="pick", case=cid)
    for key in c.shortest:
        call(action="test", item=key)
    return call(action="name", rule=lang.rule_json(c.rule))


def test_a_perfect_player_earns_every_achievement_without_luck_hints_or_time():
    game.game.__init__()
    # a near miss first (a rule that fits every example but is wrong), for Counter-Example
    latch = cases.BY_ID["latch"]
    call(action="pick", case="latch")
    call(action="name", rule=lang.rule_json(lang.parse_rule("num", "ge:30")))
    assert call(action="open")["tally"]["near"] == 1
    for cid in cases.ORDER:
        v = _name_on_the_shortest_path(cid)
        assert v["verdict"]["kind"] == "named", cid
        assert v["verdict"]["medal"] == "gold", cid
    assert latch.id in game.game.named
    # Patient Hands: send more tests (free) up to 200
    call(action="pick", case="cog")
    for n in range(100):
        call(action="test", item=str(n))
    call(action="pick", case="valve")
    v = call(action="open")
    assert v["tally"]["tests"] >= 150
    while call(action="open")["tally"]["tests"] < 200:
        for key in cases.BY_ID["bobbin"].domain.items[:60]:
            call(action="pick", case="bobbin")
            call(action="test", item=key)
    # Full Codex: read every page
    for cid in cases.ORDER:
        assert call(action="page", case=cid)["ok"]
    v = call(action="open")
    missing = [a["id"] for a in v["achievements"] if not a["earned"]]
    assert missing == []
    assert set(game.get_state()["achievements_earned"]) == set(achievements.IDS)
    assert v["totals"]["clean"] == 48 and v["totals"]["drawers_closed"] == 6 and v["goals"] == []


def test_each_achievement_needs_what_it_says_and_not_less():
    game.game.__init__()
    facts = game.game.facts()
    assert achievements.earned(facts) == []
    assert achievements.earned(dict(facts, named=8)) == ["first_gate", "eight_named"]
    assert "quick_eye" in achievements.earned(dict(facts, quick=1)) and "at_par" not in achievements.earned(dict(facts, clean=9))
    assert "at_par" in achievements.earned(dict(facts, clean=10)) and "both_ways" not in achievements.earned(dict(facts, both=4))
    assert "patient_hands" not in achievements.earned(dict(facts, tests=199)) and "patient_hands" in achievements.earned(dict(facts, tests=200))
