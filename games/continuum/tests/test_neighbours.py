"""K-7: computer-controlled neighbouring settlements."""

import pytest

import challengerun
import neighbours
import sim


def fresh(seed=7):
    ui = {}
    neighbours.ensure(ui, seed)
    return ui


@pytest.mark.parametrize("raw", [None, 3, [], "x", {"slots": 5}, {"slots": {"n1": {"attitude": 99, "next_trade": -4, "shared": "no"}}},
                                 {"lease": {"holder": "mars", "until": "x"}}, {"events": [{"season": 0, "text": "x"}, 4]},
                                 {"seed": float("nan"), "slots": {"n2": {"attitude": float("nan")}}}])
def test_hostile_records_clean_to_a_complete_valid_record(raw):
    record = neighbours.clean(raw)
    assert set(record["slots"]) == set(neighbours.SLOT_IDS)
    for slot in record["slots"].values():
        assert neighbours.ATTITUDE_MIN <= slot["attitude"] <= neighbours.ATTITUDE_MAX and slot["next_trade"] >= 0
    assert record["lease"]["holder"] in ("none", "you") + neighbours.SLOT_IDS
    assert record["events"] == [] or all(e["season"] >= 1 for e in record["events"])
    assert neighbours.clean(record) == record


def test_the_untouched_default_is_not_stored():
    ui = {}
    neighbours.put(ui, neighbours.default())
    assert neighbours.KEY not in ui
    assert neighbours.ensure(ui, 12)["seed"] == 12 and ui[neighbours.KEY]["seed"] == 12


def test_neighbours_are_pure_functions_of_seed_slot_and_season():
    record = neighbours.get(fresh(5))
    a = [neighbours.view(record, sid, 40, 1) for sid in neighbours.SLOT_IDS]
    b = [neighbours.view(record, sid, 40, 1) for sid in neighbours.SLOT_IDS]
    assert a == b
    assert len({v["name"] for v in a}) == 3
    assert all(v["controller"] == "ai" for v in a)
    names_by_seed = {tuple(neighbours.slot_name(seed, sid) for sid in neighbours.SLOT_IDS) for seed in range(1, 40)}
    assert len(names_by_seed) > 3  # different settlements get different neighbours


def test_neighbours_have_their_own_eras_that_advance_with_time_and_never_pass_the_last():
    record = neighbours.get(fresh())
    early = [neighbours.view(record, sid, 1, 0)["era"] for sid in neighbours.SLOT_IDS]
    assert early == ["tribal"] * 3
    late = [neighbours.view(record, sid, 10_000, 0)["era_index"] for sid in neighbours.SLOT_IDS]
    assert late == [len(sim.ERA_ORDER) - 1] * 3
    eras = {neighbours.view(record, sid, 120, 0)["era"] for sid in neighbours.SLOT_IDS}
    assert len(eras) > 1  # different tempos, so different eras at the same time
    for sid in neighbours.SLOT_IDS:
        for season in range(1, 400, 17):
            v = neighbours.view(record, sid, season, 2)
            assert v["need"] in neighbours.RESOURCES and v["offer"] in neighbours.RESOURCES and v["need"] != v["offer"]


def test_a_trade_swaps_resources_warms_the_neighbour_and_has_a_cooldown():
    ui = fresh()
    resources = {"food": 50.0, "materials": 10.0, "knowledge": 10.0}
    record = neighbours.get(ui)
    sid = "n1"
    v = neighbours.view(record, sid, 10, 0)
    resources[v["need"]] = 30.0
    start_need, start_offer = resources[v["need"]], resources[v["offer"]]
    ok, text = neighbours.apply_trade(ui, sid, 10, resources, 0)
    assert ok and v["name"] in text
    assert resources[v["need"]] == start_need - v["give"]
    assert resources[v["offer"]] == start_offer + v["get"]
    slot = neighbours.get(ui)["slots"][sid]
    assert slot["attitude"] == 1 and slot["next_trade"] == 10 + neighbours.TRADE_COOLDOWN
    ok, text = neighbours.apply_trade(ui, sid, 11, resources, 0)
    assert ok is False and "will trade again" in text
    assert neighbours.apply_trade(ui, sid, 10 + neighbours.TRADE_COOLDOWN, resources, 0)[0]


def test_a_trade_needs_the_goods_and_a_warmer_neighbour_gives_a_better_rate():
    ui = fresh()
    ok, text = neighbours.apply_trade(ui, "n2", 5, {"food": 0.0, "materials": 0.0, "knowledge": 0.0}, 0)
    assert ok is False and "You need" in text
    assert neighbours.apply_trade(ui, "zzz", 5, {}, 0)[0] is False
    assert neighbours.trade_rate(5) > neighbours.trade_rate(0) > neighbours.trade_rate(-3) >= 0.4


def test_sharing_a_discovery_returns_knowledge_once_per_discovery_with_a_cooldown():
    ui = fresh()
    costs = {"a": 10.0, "b": 20.0}
    names = {"a": "Alpha", "b": "Beta"}
    ok, text, gained = neighbours.apply_share(ui, "n3", 1, ["a", "b"], costs, names, 0)
    assert ok and "Beta" in text and gained == pytest.approx(6.0, rel=0.3)  # the latest first: 30% of 20, plus any lore bonus
    ok, text, _ = neighbours.apply_share(ui, "n3", 2, ["a", "b"], costs, names, 0)
    assert ok is False and "ready in" in text
    ok, text, gained2 = neighbours.apply_share(ui, "n3", 1 + neighbours.SHARE_COOLDOWN, ["a", "b"], costs, names, 0)
    assert ok and "Alpha" in text
    ok, text, _ = neighbours.apply_share(ui, "n3", 100, ["a", "b"], costs, names, 0)
    assert ok is False and "not already heard" in text
    assert neighbours.apply_share(ui, "n1", 1, [], costs, names, 0)[0] is False
    assert neighbours.apply_share(ui, "n1", 1, ["unknown"], costs, names, 0)[0] is False


def test_the_auction_is_a_deterministic_bidding_contest():
    ui = fresh()
    resources = {"materials": 100.0}
    base = neighbours.bid_base(0)
    assert neighbours.bid_options(0)[0] == ("modest", base)
    ok, text = neighbours.place_bid(ui, base + 7, resources, 3, 0)
    assert ok and resources["materials"] == 100.0 - (base + 7)
    assert neighbours.place_bid(ui, 3, resources, 3, 0)[0] is False  # one bid at a time
    assert neighbours.resolve_auction(ui, neighbours.AUCTION_FIRST - 1, resources, 0) == []
    texts = neighbours.resolve_auction(ui, neighbours.AUCTION_FIRST, resources, 0)
    assert texts and "lease" in texts[0]
    lease = neighbours.get(ui)["lease"]
    assert lease["pending"] == 0 and lease["auctions"] == 1
    assert lease["holder"] == "you"  # the lavish bid beats every rival bid
    assert neighbours.pay_lease(ui, neighbours.AUCTION_FIRST + 1, resources, 0) == neighbours.lease_income(0)
    assert neighbours.pay_lease(ui, neighbours.AUCTION_FIRST + 50, resources, 0) == 0  # the lease ran out
    same = fresh()
    other_resources = {"materials": 100.0}
    neighbours.place_bid(same, base + 7, other_resources, 3, 0)
    assert neighbours.resolve_auction(same, neighbours.AUCTION_FIRST, other_resources, 0) == texts


def test_a_lost_bid_is_returned_and_a_rival_holds_the_lease():
    ui = fresh()
    resources = {"materials": 50.0}
    neighbours.place_bid(ui, 1, resources, 3, 0)
    assert resources["materials"] == 49.0
    texts = neighbours.resolve_auction(ui, neighbours.AUCTION_FIRST, resources, 0)
    assert "returned" in texts[0] and resources["materials"] == 50.0
    assert neighbours.get(ui)["lease"]["holder"] in neighbours.SLOT_IDS
    assert neighbours.pay_lease(ui, neighbours.AUCTION_FIRST + 1, resources, 0) == 0
    assert neighbours.place_bid(fresh(), 0, {"materials": 5.0}, 1, 0)[0] is False
    assert neighbours.place_bid(fresh(), 9, {"materials": 1.0}, 1, 0)[0] is False


def test_an_unattended_auction_is_not_replayed_one_by_one():
    ui = fresh()
    neighbours.resolve_auction(ui, 205, {"materials": 0.0}, 0)
    lease = neighbours.get(ui)["lease"]
    assert lease["auctions"] == (205 - neighbours.AUCTION_FIRST) // neighbours.AUCTION_PERIOD + 1
    assert neighbours.next_auction_season(neighbours.get(ui)) > 205


def test_the_ai_controller_is_a_registered_slot_controller():
    assert neighbours.CONTROLLERS["ai"] is neighbours.ai_bid
    bids = {neighbours.ai_bid(7, sid, n, 0, 1) for sid in neighbours.SLOT_IDS for n in range(5)}
    assert min(bids) >= 1 and len(bids) > 1
    assert neighbours.ai_bid(7, "n1", 0, 5, 1) <= neighbours.ai_bid(7, "n1", 0, 0, 1)  # friends ask less


def test_the_map_names_every_place_and_does_not_rely_on_colour():
    record = neighbours.get(fresh())
    views = [neighbours.view(record, sid, 30, 0) for sid in neighbours.SLOT_IDS]
    svg = neighbours.map_svg(views, record, 30, "Reed Ford")
    for v in views:
        assert v["name"] in svg and v["era_label"] in svg and v["attitude_word"] in svg
    assert "Salt Flats" in svg and "Reed Ford" in svg and "<script" not in svg
    cold = dict(views[0], attitude=-2, attitude_word="cold")
    assert "nb-road--cold" in neighbours.map_svg([cold] + views[1:], record, 30, "x")
    assert "Needs" not in svg and neighbours.map_caption(views).count("needs") == 3


def test_after_season_does_nothing_until_the_neighbours_are_met():
    assert neighbours.after_season({}, 20, {"materials": 0.0}, 0) == []
    ui = fresh()
    resources = {"materials": 0.0}
    out = neighbours.after_season(ui, neighbours.AUCTION_FIRST, resources, 0)
    assert out and "lease" in out[0]


# --- in the game -----------------------------------------------------------------------------
def test_the_panel_builds_a_map_and_three_cards(game_env):
    el = game_env.elements
    el["neighbours-toggle-button"].dispatch("click", None)
    assert el["neighbours-panel"].hidden is False
    assert "<svg" in el["neighbours-map"].innerHTML and "Salt Flats" in el["neighbours-map"].innerHTML
    assert len(el["neighbours-list"].children) == 3
    for sid in neighbours.SLOT_IDS:
        assert f"neighbour-{sid}-trade-button" in el and f"neighbour-{sid}-share-button" in el
    assert "Rival bids usually fall" in el["neighbours-bids"].children[0].innerText
    assert "Nobody holds the lease" in el["neighbours-lease"].innerText


def test_trading_in_the_game_changes_the_stores(game_env):
    module = game_env.module
    el = game_env.elements
    el["neighbours-toggle-button"].dispatch("click", None)
    record = neighbours.get(module.campaign.ui)
    v = neighbours.view(record, "n1", game_env.state.season, 0)
    game_env.state.resources[v["need"]] = 40.0
    module.render()
    start_offer = game_env.state.resources[v["offer"]]
    el["neighbour-n1-trade-button"].dispatch("click", None)
    assert game_env.state.resources[v["offer"]] == pytest.approx(start_offer + v["get"])
    assert "Traded with" in el["neighbours-status"].innerText
    assert el["neighbour-n1-trade-button"].disabled is True  # cool-down


def test_sharing_a_discovery_in_the_game_pays_knowledge(game_env):
    module = game_env.module
    el = game_env.elements
    game_env.state.resources["knowledge"] = 50.0
    module.tree.research("fire_keeping", game_env.state.resources)
    el["neighbours-toggle-button"].dispatch("click", None)
    assert "Share" in el["neighbour-n2-share-button"].innerText and el["neighbour-n2-share-button"].disabled is False
    before = game_env.state.resources["knowledge"]
    el["neighbour-n2-share-button"].dispatch("click", None)
    assert game_env.state.resources["knowledge"] > before
    assert el["neighbour-n2-share-button"].disabled is True


def test_bidding_and_the_lease_pay_out_through_real_seasons(game_env):
    module = game_env.module
    el = game_env.elements
    el["neighbours-toggle-button"].dispatch("click", None)
    game_env.state.resources["materials"] = 200.0
    module.render()
    el["neighbours-bid-lavish-button"].dispatch("click", None)
    assert neighbours.get(module.campaign.ui)["lease"]["pending"] > 0
    assert el["neighbours-bid-modest-button"].disabled is True
    game_env.state.season = neighbours.AUCTION_FIRST - 1
    game_env.advance_season()
    lease = neighbours.get(module.campaign.ui)["lease"]
    assert lease["holder"] == "you" and lease["auctions"] == 1
    assert any("lease on the Salt Flats" in e.text for e in module.chronicle.entries)
    game_env.advance_season()
    assert "You hold the lease" in el["neighbours-lease"].innerText


def test_neighbours_rest_in_a_challenge_run_and_during_a_look_back(game_env):
    module = game_env.module
    el = game_env.elements
    module._challenge_utc_today_override = "2026-10-08"
    el["challenge-toggle-button"].dispatch("click", None)
    el["challenge-daily-start-button"].dispatch("click", None)
    assert challengerun.get(module.campaign.ui) is not None
    el["neighbours-toggle-button"].dispatch("click", None)
    assert "rest" in el["neighbours-note"].innerText.lower()
    assert el["neighbour-n1-trade-button"].disabled is True
    assert el["neighbours-bid-modest-button"].disabled is True
    game_env.state.resources["food"] = 99.0
    el["neighbour-n1-trade-button"].dispatch("click", None)  # ignored
    assert neighbours.get(module.campaign.ui)["slots"]["n1"]["trades"] == 0


def test_saved_neighbours_round_trip(game_env):
    module = game_env.module
    el = game_env.elements
    el["neighbours-toggle-button"].dispatch("click", None)
    module.campaign.ui[neighbours.KEY]["slots"]["n2"]["attitude"] = 3
    data = module.get_state()
    assert module.load_state(data) is True
    assert neighbours.get(module.campaign.ui)["slots"]["n2"]["attitude"] == 3
