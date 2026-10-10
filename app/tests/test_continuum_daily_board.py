"""K-10: Continuum's daily challenge board (continuum/daily_challenge). A daily-only, whole-number, higher-is-better
board; the usual opt-in, anonymity and small-group rules come from boards.py and are tested in test_boards.py."""

import boards
from test_boards import T0, client, fresh, get, make_user, post  # noqa: F401  (fresh is an autouse fixture)

GAME, BOARD = "continuum", "daily_challenge"


def test_board_is_registered_daily_only_with_whole_number_points():
    config = boards.board_config(GAME, BOARD)
    assert config["order"] == "desc" and config["integer"] is True
    assert tuple(config["windows"]) == ("daily",)
    assert config["unit"] == "points"


def test_accepts_a_real_score_and_rejects_absurd_or_fractional_ones(fresh):  # noqa: F811
    headers, _ = make_user("cont-a")
    body = {"game": GAME, "board": BOARD, "opt_in": True}
    assert client.post("/scores", json={**body, "score": 841}, headers=headers).status_code == 200
    assert client.post("/scores", json={**body, "score": 841.5}, headers=headers).status_code in (400, 422)
    assert client.post("/scores", json={**body, "score": -3}, headers=headers).status_code in (400, 422)
    assert client.post("/scores", json={**body, "score": 10_000_000}, headers=headers).status_code in (400, 422)


def test_weekly_and_alltime_windows_do_not_exist_for_it(fresh):  # noqa: F811
    headers, _ = make_user("cont-b")
    body = {"game": GAME, "board": BOARD, "score": 500, "opt_in": True, "windows": ["weekly"]}
    assert client.post("/scores", json=body, headers=headers).status_code in (400, 422)


def test_a_player_sees_their_rank_and_the_board_total_once_enough_play(fresh):  # noqa: F811
    users = [make_user(f"cont-{i}") for i in range(6)]
    for i, (headers, _) in enumerate(users):
        assert client.post("/scores", json={"game": GAME, "board": BOARD, "score": 100 + i * 50, "opt_in": True},
                           headers=headers).status_code == 200
    data = client.get(f"/leaderboard/{GAME}/{BOARD}", params={"window": "daily"}, headers=users[0][0]).json()
    assert data["total"] == 6 and data["mine"]["rank"] == 6 and not data["suppressed"]
