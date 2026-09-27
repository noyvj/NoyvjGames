"""Clock handling (UTC rollover) and view fields the UI relies on."""

import datetime


def test_before_launch_day_the_game_acts_like_launch_day(g, game):
    game.set_clock(lambda: datetime.date(2026, 1, 1))
    view = g.call("boot")["view"]
    assert view["session"]["date"] == game.EPOCH and view["today"] == game.EPOCH


def test_midnight_rollover_opens_the_new_daily_and_reports_next_utc(g):
    view = g.call("boot")["view"]
    assert view["today"] == "2026-09-27" and view["next_utc"] == "2026-09-28"
    g.set_day(1)
    view = g.call("boot")["view"]
    assert view["today"] == "2026-09-28" and view["session"]["number"] == 2 and view["next_utc"] == "2026-09-29"


def test_month_and_year_boundaries_in_next_utc(g):
    g.set_day(3)  # 2026-09-30
    assert g.call("boot")["view"]["next_utc"] == "2026-10-01"
    g.set_day(96)  # 2027-01-01
    assert g.call("boot")["view"]["today"] == "2027-01-01"


def test_view_never_contains_the_truth_while_in_progress(g):
    import json
    g.call("boot")
    g.call("ping", r=4, c=4)
    text = json.dumps(g.call("view"))
    assert '"truth": null' in text and '"guess": null' in text


def test_view_presets_list_matches_the_engine(g, game):
    view = g.call("boot")["view"]
    assert [p["key"] for p in view["presets"]] == list(game.PRESET_ORDER)
    assert {p["key"] for p in view["presets"] if p["daily"]} == {"easy", "hard"}


def test_handle_round_trips_json_text(game):
    import json
    game.reset_engine()
    out = json.loads(game.handle(json.dumps({"action": "boot"})))
    assert out["ok"] and out["view"]["board"]["n"] == 9
    assert out["changelog"][0]["date"] == "2026-09-27"
