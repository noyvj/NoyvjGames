"""H21: the material passport (one traced unit's journey)."""


def test_starts_empty_with_a_prompt(game_env):
    m = game_env.module
    m.render()
    assert game_env.chain.passport == []
    assert "hasn't started" in game_env.elements["passport-summary"].innerText


def test_each_cycle_adds_one_entry_with_a_valid_source(game_env):
    m = game_env.module
    for _ in range(5):
        game_env.advance_cycle()
    assert [e["cycle"] for e in game_env.chain.passport] == [1, 2, 3, 4, 5]
    assert all(e["source"] in m.PASSPORT_SOURCES for e in game_env.chain.passport)


def test_a_straight_line_chain_is_always_newly_mined(game_env):
    for _ in range(8):
        game_env.advance_cycle()
    assert {e["source"] for e in game_env.chain.passport} == {"extraction"}
    mined, recovered, longest = game_env.chain.passport_summary()
    assert (mined, recovered, longest) == (8, 0, 0)


def test_a_fully_closed_chain_is_never_newly_mined(game_env):
    game_env.chain.circularity_investment["recycle"] = 40  # far more than needed
    for _ in range(10):
        game_env.advance_cycle()
    assert "extraction" not in {e["source"] for e in game_env.chain.passport}
    assert {e["source"] for e in game_env.chain.passport} == {"recycle"}


def test_the_mix_of_sources_follows_the_supply_mix(game_env):
    game_env.chain.circularity_investment.update({"repair": 3, "reuse": 3, "recycle": 4})
    for _ in range(30):
        game_env.advance_cycle()
    sources = [e["source"] for e in game_env.chain.passport]
    assert len(set(sources)) >= 3
    assert sources.count("recycle") > sources.count("repair") - 6  # recycling supplies the most


def test_the_journey_is_deterministic(game_env):
    c = game_env.chain
    c.circularity_investment.update({"repair": 2, "reuse": 2, "recycle": 2})

    def journey():
        sources = []
        for cycle in range(1, 15):
            c.cycle_number = cycle
            sources.append(c.passport_source())
        return sources

    assert journey() == journey()


def test_trade_imports_can_appear_as_a_source(game_env):
    game_env.chain.trade_link_investment = 10
    for _ in range(30):
        game_env.advance_cycle()
    assert "trade" in {e["source"] for e in game_env.chain.passport}


def test_summary_counts_and_longest_run(game_env):
    game_env.chain.passport = [
        {"cycle": 1, "source": "extraction"}, {"cycle": 2, "source": "reuse"},
        {"cycle": 3, "source": "repair"}, {"cycle": 4, "source": "extraction"},
        {"cycle": 5, "source": "recycle"},
    ]
    assert game_env.chain.passport_summary() == (2, 3, 2)


def test_history_is_capped(game_env):
    m = game_env.module
    for _ in range(m.PASSPORT_MAX_ENTRIES + 15):
        game_env.advance_cycle()
    assert len(game_env.chain.passport) == m.PASSPORT_MAX_ENTRIES
    assert game_env.chain.passport[-1]["cycle"] == m.PASSPORT_MAX_ENTRIES + 15


def test_render_lists_newest_first_and_at_most_eight(game_env):
    for _ in range(12):
        game_env.advance_cycle()
    rows = game_env.elements["passport-list"].children
    assert len(rows) == 8
    assert rows[0].innerText.startswith("Cycle 12:")
    assert "Unit #1" in game_env.elements["passport-summary"].innerText


def test_save_round_trip_and_empty_omits_key(game_env):
    m = game_env.module
    assert "passport" not in m.get_state()
    for _ in range(4):
        game_env.advance_cycle()
    data = m.get_state()
    assert len(data["passport"]) == 4
    game_env.chain.passport = []
    m.load_state(data)
    assert game_env.chain.passport == data["passport"]


def test_load_drops_bad_entries_and_respects_the_cap(game_env):
    m = game_env.module
    data = m.get_state()
    good = {"cycle": 3, "source": "reuse"}
    data["passport"] = [good, {"cycle": 0, "source": "reuse"}, {"cycle": "2", "source": "reuse"},
                        {"cycle": 4, "source": "nonsense"}, {"cycle": True, "source": "reuse"},
                        "junk", None, {"cycle": 5}, {"source": "repair"}]
    m.load_state(data)
    assert game_env.chain.passport == [good]
    data["passport"] = [{"cycle": n, "source": "repair"} for n in range(1, 200)]
    m.load_state(data)
    assert len(game_env.chain.passport) == m.PASSPORT_MAX_ENTRIES
    data["passport"] = "nope"
    m.load_state(data)
    assert game_env.chain.passport == []


def test_reset_chain_clears_the_passport(game_env):
    game_env.advance_cycle()
    game_env.elements["reset-chain-button"].dispatch("click", None)
    assert game_env.chain.passport == []
