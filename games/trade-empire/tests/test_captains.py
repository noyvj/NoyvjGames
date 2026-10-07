"""J-7/J-8 -- Fleet Captains: a veteran hauler earns a seat, the player picks a
captain from a visible roster, every perk has a trade-off, a captain moves
once per charter, and the roster is remembered across charters."""

import types

import pytest

SHIP = "1"


def _veteran(module, ship_id=SHIP):
    ship = module.ships[ship_id]
    ship.route_legs = module.VETERAN_ROUND_TRIPS * 2
    module.captain_note_veterans()
    return ship


def _trip(game_env, destination="ferrum", ship_id=SHIP):
    game_env.load(ship_id=ship_id)
    game_env.depart(destination, ship_id=ship_id)
    game_env.tick(game_env.module.TRAVEL_TICKS + 2)


def _set_effects(module, classes):
    from tests.fakes import FakeClassList  # noqa: PLC0415
    html = types.SimpleNamespace(classList=FakeClassList())
    for name in classes:
        html.classList.add(name)
    module.document.documentElement = html
    return html


# ----------------------------------------------------------------- roster

def test_roster_has_four_named_captains_each_with_a_perk_a_tradeoff_and_a_quote(game_env):
    m = game_env.module
    assert set(m.CAPTAINS) == {"frugal", "lucky", "night_owl", "perfectionist"}
    for captain in m.CAPTAINS.values():
        for field in ("label", "name", "perk", "tradeoff", "quote"):
            assert captain[field].strip(), field
    assert len({c["name"] for c in m.CAPTAINS.values()}) == 4


def test_nothing_changes_without_a_captain(game_env):
    m = game_env.module
    ship = m.ships[SHIP]
    assert m.captain_cargo_multiplier(ship) == 1.0
    assert m.captain_adjusted_ticks(ship, 5) == 5
    assert m.captain_proceeds_multiplier(ship, "ferrum", m.ORE) == 1.0


# -------------------------------------------------------------- earning a seat

def test_a_seat_is_earned_only_by_a_veteran_hauler(game_env):
    m = game_env.module
    assert m.can_assign_captain("frugal", SHIP) is False
    ship = m.ships[SHIP]
    ship.route_legs = m.VETERAN_ROUND_TRIPS * 2 - 1
    m.captain_note_veterans()
    assert m.can_assign_captain("frugal", SHIP) is False
    _veteran(m)
    assert m.can_assign_captain("frugal", SHIP) is True


def test_the_seat_is_kept_after_the_route_streak_resets(game_env):
    m = game_env.module
    ship = _veteran(m)
    ship.route_legs = 1  # changed route: no longer a veteran right now
    m.captain_note_veterans()
    assert ship.is_veteran is False and m.captain_is_earned(SHIP) is True


def test_an_unpurchased_ship_cannot_hold_a_seat(game_env):
    m = game_env.module
    m.ships["5"].route_legs = 20
    m.captain_note_veterans()
    assert m.can_assign_captain("frugal", "5") is False


def test_a_veteran_is_noticed_by_the_tick(game_env):
    m = game_env.module
    m.ships[SHIP].route_legs = 10
    game_env.tick()
    assert SHIP in m.captain_earned


# ----------------------------------------------------------------- assigning

def test_assigning_posts_the_captain_and_remembers_them(game_env):
    m = game_env.module
    _veteran(m)
    assert m.assign_captain("lucky", SHIP) is True
    assert m.ships[SHIP].captain == "lucky"
    assert "lucky" in m.captains_met
    assert m.captain_ship_for("lucky") is m.ships[SHIP]


def test_one_captain_per_ship_and_unknown_captains_are_refused(game_env):
    m = game_env.module
    _veteran(m)
    m.assign_captain("lucky", SHIP)
    assert m.assign_captain("frugal", SHIP) is False
    assert m.assign_captain("bogus", SHIP) is False
    assert m.can_assign_captain(["unhashable"], SHIP) is False


def test_moving_a_captain_uses_the_once_per_charter_move_and_frees_the_old_ship(game_env):
    m = game_env.module
    _veteran(m, "1")
    _veteran(m, "2")
    _veteran(m, "3")
    m.assign_captain("frugal", "1")
    assert m.assign_captain("frugal", "2") is True  # the move
    assert m.ships["1"].captain is None and m.ships["2"].captain == "frugal"
    assert m.assign_captain("frugal", "3") is False  # no second move
    assert m.ships["2"].captain == "frugal"


def test_releasing_then_reposting_also_counts_as_the_move(game_env):
    m = game_env.module
    _veteran(m, "1")
    _veteran(m, "2")
    m.assign_captain("night_owl", "1")
    assert m.release_captain("night_owl") is True
    assert m.ships["1"].captain is None
    assert m.assign_captain("night_owl", "2") is True
    assert m.release_captain("night_owl") is True
    assert m.assign_captain("night_owl", "1") is False
    assert m.release_captain("night_owl") is False  # nobody serving


# ------------------------------------------------------------------- effects

def test_frugal_trades_cargo_for_proceeds(game_env):
    m = game_env.module
    ship = _veteran(m)
    ship.location = "aurum"
    ship.cargo_qty = 0
    ship.load()
    plain = ship.cargo_qty
    ship.cargo_qty, ship.cargo_good = 0, None
    m.assign_captain("frugal", SHIP)
    ship.load()
    assert ship.cargo_qty == max(1, round(plain * m.FRUGAL_CARGO)) < plain
    assert m.captain_proceeds_multiplier(ship, "ferrum", m.ORE) == pytest.approx(1 + m.FRUGAL_PROCEEDS)


def test_lucky_trader_pays_extra_on_every_fourth_delivery_only(game_env):
    m = game_env.module
    ship = _veteran(m)
    m.assign_captain("lucky", SHIP)
    multipliers = []
    for _ in range(8):
        multipliers.append(m.captain_proceeds_multiplier(ship, "ferrum", m.ORE))
        ship.captain_deliveries += 1
    assert multipliers[3] == pytest.approx(1 + m.LUCKY_BONUS) and multipliers[7] == pytest.approx(1 + m.LUCKY_BONUS)
    assert all(x == pytest.approx(1 + m.LUCKY_OFF_BEAT) for i, x in enumerate(multipliers) if i % 4 != 3)
    average = sum(multipliers[:4]) / 4
    assert 1.0 < average < 1.15  # a small average gain, not a jackpot


def test_lucky_delivery_count_advances_on_real_sales_and_resets_on_repost(game_env):
    m = game_env.module
    ship = _veteran(m)
    m.assign_captain("lucky", SHIP)
    _trip(game_env)
    assert ship.captain_deliveries == 1
    m.release_captain("lucky")
    assert ship.captain_deliveries == 0


def test_night_owl_shaves_a_tick_from_long_trips_only(game_env):
    m = game_env.module
    ship = _veteran(m)
    m.assign_captain("night_owl", SHIP)
    assert m.captain_adjusted_ticks(ship, 5) == 4
    assert m.captain_adjusted_ticks(ship, m.NIGHT_OWL_MIN_TICKS) == m.NIGHT_OWL_MIN_TICKS - 1
    assert m.captain_adjusted_ticks(ship, m.NIGHT_OWL_MIN_TICKS - 1) == m.NIGHT_OWL_MIN_TICKS - 1
    assert m.captain_proceeds_multiplier(ship, "ferrum", m.ORE) == pytest.approx(1 + m.NIGHT_OWL_PROCEEDS)
    ship.location = "aurum"
    ship.cargo_good, ship.cargo_qty = m.ORE, 5
    ship.depart("ferrum")
    assert ship.transit_total_ticks == m.TRAVEL_TICKS - 1


def test_night_owl_never_makes_a_trip_shorter_than_one_tick(game_env):
    m = game_env.module
    ship = _veteran(m)
    m.assign_captain("night_owl", SHIP)
    assert m.captain_adjusted_ticks(ship, 1) == 1


def test_perfectionist_rewards_the_neediest_colony_and_taxes_the_comfortable_one(game_env):
    m = game_env.module
    ship = _veteran(m)
    m.assign_captain("perfectionist", SHIP)
    state = m.colony_states["ferrum"]  # needs ore
    state.need_satisfaction = 0.3
    assert m.captain_proceeds_multiplier(ship, "ferrum", m.ORE) == pytest.approx(1 + m.PERFECTIONIST_BONUS)
    state.need_satisfaction = 0.75
    assert m.captain_proceeds_multiplier(ship, "ferrum", m.ORE) == 1.0
    state.need_satisfaction = 0.95
    assert m.captain_proceeds_multiplier(ship, "ferrum", m.ORE) == pytest.approx(1 + m.PERFECTIONIST_PENALTY)


def test_a_real_sale_uses_the_captain_multiplier(game_env):
    m = game_env.module
    ship = _veteran(m)
    m.assign_captain("frugal", SHIP)
    m.market_multiplier[m.ORE] = 1.0
    m.colony_states["ferrum"].need_satisfaction = 0.5
    ship.location = "aurum"
    ship.cargo_good, ship.cargo_qty = m.ORE, 10
    ship.depart("ferrum")
    before = m.total_profit
    game_env.tick(m.TRAVEL_TICKS)
    earned = ship.total_earned
    expected = int(round(10 * m.SELL_PRICE[m.ORE] * (1 + m.FRUGAL_PROCEEDS)))
    assert earned == expected and m.total_profit >= before + expected


# ---------------------------------------------------------------------- save

def test_captains_round_trip_through_a_save(game_env):
    m = game_env.module
    ship = _veteran(m)
    m.assign_captain("lucky", SHIP)
    ship.captain_deliveries = 2
    saved = m.get_state()
    assert saved["captains"]["met"] == ["lucky"]
    ship.captain, ship.captain_deliveries = None, 0
    m.captain_earned.clear()
    m.captains_met.clear()
    m.captain_assignments["lucky"] = 0
    m.load_state(saved)
    assert ship.captain == "lucky" and ship.captain_deliveries == 2
    assert SHIP in m.captain_earned and m.captain_assignments["lucky"] == 1 and "lucky" in m.captains_met


def test_a_fresh_game_writes_no_captains_key(game_env):
    assert "captains" not in game_env.module.get_state()


@pytest.mark.parametrize("bad_captain", ["bogus", 5, None, ["lucky"], True])
def test_a_tampered_captain_id_is_dropped(game_env, bad_captain):
    m = game_env.module
    _veteran(m)
    saved = m.get_state()
    saved["ships"][SHIP]["captain"] = bad_captain
    m.load_state(saved)
    assert m.ships[SHIP].captain is None


def test_a_captain_on_a_ship_with_no_earned_seat_is_dropped(game_env):
    m = game_env.module
    saved = m.get_state()
    saved["ships"]["2"]["captain"] = "frugal"
    m.load_state(saved)
    assert m.ships["2"].captain is None


def test_the_same_captain_on_two_ships_keeps_only_the_first(game_env):
    m = game_env.module
    _veteran(m, "1")
    _veteran(m, "2")
    saved = m.get_state()
    saved["ships"]["1"]["captain"] = "frugal"
    saved["ships"]["2"]["captain"] = "frugal"
    m.load_state(saved)
    assert [m.ships[i].captain for i in ("1", "2")] == ["frugal", None]


def test_a_captain_on_an_unpurchased_ship_is_dropped(game_env):
    m = game_env.module
    saved = m.get_state()
    saved["captains"] = {"earned": ["5"], "assignments": {}, "met": []}
    saved["ships"]["5"]["captain"] = "frugal"
    m.load_state(saved)
    assert m.ships["5"].captain is None


@pytest.mark.parametrize("bad", [None, 5, "x", [], {"earned": "1", "assignments": [], "met": 7},
                                 {"earned": [["a"]], "assignments": {"frugal": True, "lucky": 99}, "met": [["x"], "bogus"]}])
def test_tampered_captains_blocks_fall_back_safely(game_env, bad):
    m = game_env.module
    saved = m.get_state()
    saved["captains"] = bad
    m.load_state(saved)
    assert m.captain_earned == set()
    assert all(0 <= v <= 1 + m.CAPTAIN_SWAPS_PER_CHARTER for v in m.captain_assignments.values())
    assert m.captains_met <= set(m.CAPTAINS)


# -------------------------------------------------------------- renewal, achievements

def test_a_renewal_resets_postings_but_the_roster_is_remembered(game_env):
    m = game_env.module
    _veteran(m)
    m.assign_captain("frugal", SHIP)
    m.endgame_reached = True
    assert m.found_new_corporation() is True
    assert m.ships[SHIP].captain is None
    assert m.captain_earned == set() and m.captain_assignments["frugal"] == 0
    assert m.captains_met == {"frugal"}


def test_captain_achievements_follow_the_roster(game_env):
    m = game_env.module
    assert "captains_table" not in m.achievement_ids_earned()
    for i, perk in enumerate(m.CAPTAINS):
        ship_id = str(i + 1)
        _veteran(m, ship_id)
        m.assign_captain(perk, ship_id)
        if i == 0:
            assert "captains_table" in m.achievement_ids_earned()
            assert "full_roster" not in m.achievement_ids_earned()
    assert "full_roster" in m.achievement_ids_earned()
    summary = {a["id"]: a for a in m.achievements_summary()}
    assert summary["full_roster"]["progress"] == (4, 4)


# ------------------------------------------------------------------------ UI

def test_the_panel_toggles_and_exposes_aria_expanded(game_env):
    e = game_env.elements
    game_env.toggle_captains()
    assert e["captains-panel"].hidden is False
    assert e["captains-toggle-button"].attributes["aria-expanded"] == "true"
    game_env.toggle_captains()
    assert e["captains-panel"].hidden is True
    assert e["captains-toggle-button"].attributes["aria-expanded"] == "false"


def test_assign_buttons_show_only_where_a_posting_is_possible(game_env):
    m = game_env.module
    e = game_env.elements
    game_env.toggle_captains()
    assert all(e[f"captain-frugal-ship-{s}-button"].hidden for s in m.ships)
    _veteran(m)
    m.render()
    assert e["captain-frugal-ship-1-button"].hidden is False
    assert e["captain-frugal-ship-2-button"].hidden is True
    assert e["captain-frugal-ship-1-button"].innerText == "Post to Ship 1"


def test_clicking_posts_a_captain_and_the_ship_panel_shows_it_with_its_quote(game_env):
    m = game_env.module
    e = game_env.elements
    _veteran(m)
    game_env.toggle_captains()
    e["captain-lucky-ship-1-button"].dispatch("click")
    assert m.ships[SHIP].captain == "lucky"
    assert e["ship-1-captain"].hidden is False
    assert "Captain Joss Marrow" in e["ship-1-captain-text"].innerText
    assert m.CAPTAINS["lucky"]["quote"] in e["ship-1-captain-quote"].innerText
    assert "Ship 1" in e["captain-lucky-status"].innerText
    assert e["captain-lucky-release-button"].hidden is False
    e["captain-lucky-release-button"].dispatch("click")
    assert m.ships[SHIP].captain is None
    assert "seat earned" in e["ship-1-captain-text"].innerText


def test_ship_captain_line_is_hidden_until_a_seat_is_earned(game_env):
    m = game_env.module
    assert game_env.elements["ship-1-captain"].hidden is True
    _veteran(m)
    m.render()
    assert game_env.elements["ship-1-captain"].hidden is False


def test_a_move_is_labelled_and_asks_to_confirm(game_env):
    m = game_env.module
    e = game_env.elements
    _veteran(m, "1")
    _veteran(m, "2")
    m.assign_captain("frugal", "1")
    m.release_captain("frugal")
    asked = []
    m._confirm_dialog_ask = lambda *a, **k: asked.append(a)
    game_env.toggle_captains()
    assert e["captain-frugal-ship-2-button"].innerText == "Move to Ship 2"
    e["captain-frugal-ship-2-button"].dispatch("click")
    assert asked and "once per charter" in asked[0][1]
    assert m.ships["2"].captain is None  # waits for the confirmation


def test_summary_text_counts_seats_and_the_roster(game_env):
    m = game_env.module
    assert "none yet" in m.captains_summary_text()
    _veteran(m)
    m.assign_captain("frugal", SHIP)
    text = m.captains_summary_text()
    assert "Ship 1" in text and "1 of 4 captains posted" in text and "1 of 4 captains met" in text
