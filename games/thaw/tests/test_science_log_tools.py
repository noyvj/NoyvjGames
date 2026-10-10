"""G-18 science-log filter chips, search and plain-text export; G-19 pinning that survives the cap
and rides along in the Highlights recap."""


class FakeTarget:
    def __init__(self, index):
        self._index = index

    def closest(self, _selector):
        return self

    def getAttribute(self, name):
        assert name == "data-pin-index"
        return str(self._index)


class FakeClick:
    def __init__(self, index):
        self.target = FakeTarget(index)


def _fill(m, n=6):
    m.science_log.clear()
    texts = [
        "permafrost began melting at +10.0°.",
        "the feedback loop went critical (2.1x background warming).",
        "intervention delayed reaching +15° warming.",
        "pre-emptive protection (30% dampening) was already in place when melt began.",
        "the one-time emergency rescue was used.",
        "a tipping cascade from the neighboring region added 0.5° of warming.",
    ]
    for i in range(n):
        m.science_log.append({"region": "AB"[i % 2], "round": i + 1, "text": texts[i % len(texts)]})
    m.render()


def test_kind_is_read_from_the_text(game_env):
    m = game_env.module
    assert m.log_kind({"text": "permafrost began melting at +1"}) == "tipping"
    assert m.log_kind({"text": "a tipping cascade ..."}) == "tipping"
    assert m.log_kind({"text": "restoration begins"}) == "milestone"
    assert m.log_kind({"text": "the one-time emergency rescue was used."}) == "invest"
    assert m.log_kind({"text": "something else"}) == "other"


def test_chip_filters_the_list(game_env):
    m = game_env.module
    _fill(m)
    game_env.elements["log-filter-tipping"].dispatch("click")
    assert [e["round"] for _i, e in m.filtered_log()] == [1, 2, 6]
    game_env.elements["log-filter-invest"].dispatch("click")
    assert [e["round"] for _i, e in m.filtered_log()] == [4, 5]
    game_env.elements["log-filter-all"].dispatch("click")
    assert len(m.filtered_log()) == 6


def test_active_chip_is_marked_and_pressed(game_env):
    m = game_env.module
    _fill(m)
    game_env.elements["log-filter-milestone"].dispatch("click")
    chip = game_env.elements["log-filter-milestone"]
    assert "log-chip--on" in chip.className
    assert chip.attributes["aria-pressed"] == "true"
    assert game_env.elements["log-filter-all"].attributes["aria-pressed"] == "false"


def test_search_matches_text_region_and_round(game_env):
    m = game_env.module
    _fill(m)
    game_env.elements["log-search"].value = "  Cascade "
    game_env.elements["log-search"].dispatch("input")
    assert [e["round"] for _i, e in m.filtered_log()] == [6]
    game_env.elements["log-search"].value = "round 2"
    game_env.elements["log-search"].dispatch("input")
    assert [e["round"] for _i, e in m.filtered_log()] == [2]
    game_env.elements["log-search"].value = "zzz"
    game_env.elements["log-search"].dispatch("input")
    assert "No entries match" in game_env.elements["science-log-list"].innerHTML
    assert game_env.elements["science-log-count"].innerText == "6"


def test_search_is_length_limited_and_escaped(game_env):
    m = game_env.module
    m.set_log_query("x" * 500)
    assert len(m.log_query) == 60
    m.science_log.append({"region": "A", "round": 1, "text": "<script>alert(1)</script>"})
    m.set_log_query("")
    assert "<script>" not in m.science_log_html()


def test_pin_and_unpin_through_the_list_click(game_env):
    m = game_env.module
    _fill(m)
    game_env.elements["science-log-list"].dispatch("click", FakeClick(2))
    assert m.science_log[2].get("pinned") is True
    assert 'aria-pressed="true"' in game_env.elements["science-log-list"].innerHTML
    game_env.elements["science-log-list"].dispatch("click", FakeClick(2))
    assert "pinned" not in m.science_log[2]


def test_pinned_chip_shows_only_pins_and_counts_them(game_env):
    m = game_env.module
    _fill(m)
    m.set_log_pinned(0, True)
    m.set_log_pinned(3, True)
    m.render()
    assert "(2)" in game_env.elements["log-filter-pinned"].innerText
    game_env.elements["log-filter-pinned"].dispatch("click")
    assert [e["round"] for _i, e in m.filtered_log()] == [1, 4]


def test_pin_limit_and_bad_indexes(game_env):
    m = game_env.module
    m.science_log[:] = [{"region": "A", "round": i, "text": "x"} for i in range(m.MAX_PINNED + 3)]
    results = [m.set_log_pinned(i, True) for i in range(m.MAX_PINNED + 3)]
    assert results.count(True) == m.MAX_PINNED
    assert m.set_log_pinned(-1, True) is False
    assert m.set_log_pinned(999, True) is False
    assert m.set_log_pinned(True, True) is False
    assert m.set_log_pinned("1", True) is False
    game_env.elements["science-log-list"].dispatch("click", FakeClick(m.MAX_PINNED + 1))
    assert "up to" in game_env.elements["log-status"].innerText


def test_pinned_entries_survive_the_cap(game_env):
    m = game_env.module
    m.science_log[:] = [{"region": "A", "round": i, "text": "x"} for i in range(m.SCIENCE_LOG_MAX)]
    m.set_log_pinned(0, True)
    m.set_log_pinned(1, True)
    for n in range(30):
        m.science_log.append({"region": "B", "round": 100 + n, "text": "y"})
    m._cap_science_log()
    assert len(m.science_log) == m.SCIENCE_LOG_MAX
    assert [e["round"] for e in m.science_log if e.get("pinned")] == [0, 1]
    assert m.science_log[-1]["round"] == 129


def test_cap_with_every_entry_pinned_still_trims(game_env):
    m = game_env.module
    m.science_log[:] = [{"region": "A", "round": i, "text": "x", "pinned": True} for i in range(60)]
    m._cap_science_log()
    assert len(m.science_log) == m.SCIENCE_LOG_MAX


def test_pins_round_trip_through_a_save(game_env):
    m = game_env.module
    _fill(m)
    m.set_log_pinned(1, True)
    state = m.get_state()
    assert state["science_log"][1]["pinned"] is True
    assert "pinned" not in state["science_log"][0]
    m.science_log.clear()
    assert m.load_state(state)
    assert [e.get("pinned") for e in m.science_log] == [None, True, None, None, None, None]


def test_load_ignores_bad_pin_values_and_extra_pins(game_env):
    m = game_env.module
    entries = [{"region": "A", "round": 1, "text": "a", "pinned": "yes"}]
    entries += [{"region": "A", "round": 2 + i, "text": "b", "pinned": True} for i in range(m.MAX_PINNED + 4)]
    m.load_state({"science_log": entries})
    assert "pinned" not in m.science_log[0]
    assert m.pinned_count() == m.MAX_PINNED


def test_old_saves_without_pins_load_unchanged(game_env):
    m = game_env.module
    m.load_state({"science_log": [{"region": "B", "round": 3, "text": "plain"}]})
    assert m.science_log == [{"region": "B", "round": 3, "text": "plain"}]


def test_pinned_lines_appear_in_the_recap_and_copy_text(game_env):
    m = game_env.module
    _fill(m)
    m.set_log_pinned(0, True)
    m.render()
    html = game_env.elements["highlights-list"].innerHTML
    assert "Pinned, round 1, Region A: permafrost began melting" in html
    assert "Pinned, round 1" in m.highlights_text()
    assert len(m.highlights_lines()) == 3


def test_export_text_is_plain_and_complete(game_env):
    m = game_env.module
    _fill(m, 3)
    text = m.science_log_text()
    assert text.count("\n") == 2
    assert text.startswith("Round 1 - Region A: permafrost began melting")
    m.set_log_pinned(2, True)
    assert m.science_log_text(only_pinned=True).count("\n") == 0


def test_copy_button_falls_back_without_a_clipboard(game_env):
    m = game_env.module
    game_env.elements["log-export-button"].dispatch("click")
    assert game_env.elements["log-status"].innerText == "The log is empty."
    _fill(m, 2)
    game_env.elements["log-export-button"].dispatch("click")
    assert "Copy isn't available" in game_env.elements["log-status"].innerText


def test_player_actions_are_logged_as_invest_lines(game_env):
    m = game_env.module
    m.science_log.clear()
    m.region.funds = 500
    m.region_b.funds = 10
    assert m.route_funds("a", "b")
    m.carbon_bank = 10
    assert m.spend_carbon_credits("c")
    kinds = [m.log_kind(e) for e in m.science_log]
    assert kinds == ["invest", "invest"]
    assert "convoy from Region A" in m.science_log[0]["text"]


def test_rescue_is_logged(game_env):
    m = game_env.module
    m.science_log.clear()
    m.region.temperature = 30.0
    m.region.funds = 400
    m.render()
    game_env.elements["rescue-button"].dispatch("click")
    assert any("emergency rescue" in e["text"] for e in m.science_log)
