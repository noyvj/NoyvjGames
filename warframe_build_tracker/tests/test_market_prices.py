"""Market price reference: prices arrive as JSON from the backend proxy."""

import json

from .test_refinery import _all_text
from .test_tracker import _find_row, _reset_to_known_state


def _short_amarast(m):
    _reset_to_known_state(m, parts={"Splat Loader": {"owned": 0, "target": 1}})
    m._market["prices"] = {}


def test_slug_matches_the_backend_whitelist(game_env):
    m = game_env.module
    assert m.market_slug("Star Amarast") == "star_amarast"
    assert m.market_slug("Tear Azurite") == "tear_azurite"
    assert m.market_slug("Heart Nyth") == "heart_nyth"


def test_prices_are_stored_for_known_resources_only(game_env):
    m = game_env.module
    _short_amarast(m)
    payload = {"prices": {
        "star_amarast": {"lowest_sell": 12, "orders": 30},
        "tear_azurite": {"lowest_sell": 2.5, "orders": 5},
        "nonsense": {"lowest_sell": 1, "orders": 1},
        "heart_nyth": {"lowest_sell": True},
        "goblite_tears": {"lowest_sell": -3},
        "esher_devar": "junk",
    }}
    assert m.set_market_prices(json.dumps(payload)) == 2
    assert m._market["prices"] == {"Star Amarast": 12, "Tear Azurite": 2.5}


def test_bad_payloads_clear_prices_without_crashing(game_env):
    m = game_env.module
    m._market["prices"] = {"Star Amarast": 9}
    assert m.set_market_prices("not json") == 0
    assert m.set_market_prices(json.dumps([1, 2])) == 0
    assert m.set_market_prices(json.dumps({"prices": "x"})) == 0
    assert m._market["prices"] == {}


def test_total_counts_only_tradeable_resources_still_short(game_env):
    m = game_env.module
    _short_amarast(m)
    _, rows = m.calculate()
    amarast = next(r for r in rows if r["name"] == "Star Amarast")
    assert amarast["built_short"] > 0
    m.set_market_prices(json.dumps({"prices": {"star_amarast": {"lowest_sell": 10}, "tear_azurite": {"lowest_sell": 4}}}))
    _, rows = m.calculate()
    total, counted = m.market_value_short(rows)
    assert counted >= 1 and total >= 10 * amarast["built_short"]
    assert "platinum" in m.market_text(rows)


def test_row_badge_and_summary_hidden_without_prices(game_env):
    m = game_env.module
    _short_amarast(m)
    m.render()
    assert game_env.elements["market-summary"].hidden is True
    m.set_market_prices(json.dumps({"prices": {"star_amarast": {"lowest_sell": 10}}}))
    row = _find_row(game_env.elements["resources-body"], "data-resource", "Star Amarast")
    assert "~10 plat each" in _all_text(row)
    assert game_env.elements["market-summary"].hidden is False
