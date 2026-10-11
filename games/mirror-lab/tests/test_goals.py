"""The three-goals strip: the next three goals not yet done, in any order, each a number the player can already see."""

import json

import benches
import game
import goals
import logbook
import progress


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def setup_function(_fn):
    game.game.__init__()


def test_a_fresh_game_shows_exactly_three_goals_with_bars_at_zero():
    v = call(action="open")
    assert [g["id"] for g in v["goals"]] == ["ch1-5", "benches-10", "shelf-5"]
    assert all(g["have"] == 0 and g["need"] > 0 and not g["done"] and g["label"] and g["description"] for g in v["goals"])
    assert v["goals_summary"] == {"done": 0, "total": len(goals.GOALS)}


def test_goal_ids_are_unique_and_descriptions_state_their_numbers():
    assert len(set(goals.GOAL_IDS)) == len(goals.GOALS)
    for gid, _label, description, _have, need in goals.GOALS:
        assert str(need) in description or "all" in description or "every" in description.lower(), gid


def test_clearing_benches_moves_the_bars_and_a_done_goal_is_replaced():
    for b in benches.CHAPTERS[0]["benches"][:5]:
        game.game.cleared[b.id] = b.solution_layout()
    v = call(action="open")
    ids = [g["id"] for g in v["goals"]]
    assert "ch1-5" not in ids and ids[0] == "benches-10" and v["goals"][0]["have"] == 5
    assert len(ids) == 3


def test_goals_count_what_the_player_does_on_screen():
    game.game.cleared["c1-1"] = benches.BY_ID["c1-1"].solution_layout()
    game.game.used = {"mirror", "prism"}
    by_id = {g["id"]: g for g in goals.all_goals(game.game.cleared, game.game.used)}
    assert by_id["shelf-5"]["have"] == 2 and by_id["fewest-5"]["have"] == 1 and by_id["benches-10"]["have"] == 1 and by_id["ch1-5"]["have"] == 1


def test_every_goal_can_be_finished_and_none_is_lost_by_playing():
    cleared = {b.id: b.solution_layout() for b in benches.ALL_BENCHES}
    used = {fid for fid, _t, _p, _w in logbook.SHELF}
    assert goals.next_goals(cleared, used) == [] and goals.summary(cleared, used) == {"done": len(goals.GOALS), "total": len(goals.GOALS)}
    assert progress.fewest_tags(cleared) == len(benches.ALL_BENCHES)


def test_the_page_has_the_strip_and_the_tally_has_the_hints_stat():
    html = (game.__file__.rsplit("/", 1)[0] + "/index.html")
    text = open(html, encoding="utf-8").read()
    for needle in ('id="goals"', 'id="goals-list"', 'id="stat-hints"', "Hints asked", "(any order)"):
        assert needle in text
