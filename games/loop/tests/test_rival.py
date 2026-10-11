"""GH-5 / FY-38: the scripted Rival Corporation you can race (opt-in)."""

import json

import pytest


def rival_on(env):
    env.elements["rival-button"].dispatch("click", None)
    assert env.chain.rival_on is True


def lines(env):
    return env.elements["rival-lines"].innerHTML


def test_the_rival_is_a_pure_function_of_the_cycle_number(game_env):
    m = game_env.module
    assert m.rival_funds_after(0) == m.STARTING_FUNDS
    assert [m.rival_funds_after(n) for n in range(0, 8)] == [m.rival_funds_after(n) for n in range(0, 8)]
    # first cycle: 250 revenue, 50 units x 2.0 at no damage
    assert m.rival_funds_after(1) == pytest.approx(300 + 250 - 100)
    assert m.rival_extracted_after(4) == 200


def test_the_rival_is_ahead_early_then_stalls_as_its_damage_climbs(game_env):
    m = game_env.module
    profits = [m.rival_profit_in_cycle(n) for n in range(1, 16)]
    assert profits[0] == pytest.approx(150)
    assert all(a > b for a, b in zip(profits[:10], profits[1:11]))  # strictly falling at first
    assert profits[10] == pytest.approx(0, abs=1e-6) and profits[14] == pytest.approx(0, abs=1e-6)
    assert m.rival_funds_after(40) == pytest.approx(m.rival_funds_after(12))  # a plateau: no more profit
    assert m.rival_funds_after(40) < 2000


def test_the_rival_is_off_and_hidden_by_default(game_env):
    assert game_env.chain.rival_on is False
    assert game_env.elements["rival-race"].hidden is True
    assert game_env.elements["rival-button"].innerText == "Rival Corporation: off"
    assert "Rival Corporation" in game_env.elements["rival-status"].innerText
    assert game_env.elements["rival-lines"].innerHTML == ""
    assert "rival_on" not in game_env.module.get_state()


def test_switching_it_on_shows_the_race(game_env):
    rival_on(game_env)
    assert game_env.elements["rival-race"].hidden is False
    assert game_env.elements["rival-button"].attributes["aria-pressed"] == "true"
    assert "Advance a cycle" in lines(game_env)


def test_the_comparison_lines_report_both_funds_and_the_gap(game_env):
    chain = game_env.chain
    rival_on(game_env)
    game_env.invest_circularity("repair")  # 20 funds spent, so the first cycle starts behind
    chain.advance_cycle()
    game_env.module.render()
    text = lines(game_env)
    assert f"you have {chain.funds:.0f} funds" in text
    assert f"has {game_env.module.rival_funds_after(1):.0f}" in text
    assert "behind" in text and "looks ahead early" in text
    assert "units" in text
    level = game_env.module.rival_lines()
    assert level and "You are" in level[0]


def test_bars_are_scaled_against_the_larger_of_the_two(game_env):
    chain = game_env.chain
    rival_on(game_env)
    chain.advance_cycle()
    you, rival = game_env.module.rival_bar_widths()
    assert max(you, rival) == 100 and 0 <= min(you, rival) <= 100
    assert game_env.elements["rival-bar-you"].style.width == f"{you}%"


def test_a_linear_player_never_pulls_ahead_but_a_circular_one_does(game_env):
    chain = game_env.chain
    rival_on(game_env)
    for _ in range(6):
        chain.advance_cycle()
    assert chain.rival_crossover_cycle is None  # mirrors the rival exactly: never strictly ahead
    game_env.reset_chain()
    chain = game_env.chain
    rival_on(game_env)
    chain.funds = 5000.0
    for _ in range(10):
        game_env.invest_circularity("recycle")
    chain.advance_cycle()
    assert chain.rival_crossover_cycle == 1


def test_the_crossover_is_remembered_and_never_moves(game_env):
    chain = game_env.chain
    rival_on(game_env)
    chain.funds = 5000.0
    for _ in range(10):
        game_env.invest_circularity("recycle")
    chain.advance_cycle()
    chain.advance_cycle()
    assert chain.rival_crossover_cycle == 1
    game_env.module.render()
    assert "pulled ahead of Rival Corporation on cycle 1" in lines(game_env)


def test_the_crossover_moment_is_an_achievement_toast_shown_once(game_env):
    chain = game_env.chain
    rival_on(game_env)
    chain.funds = 5000.0
    for _ in range(10):
        game_env.invest_circularity("recycle")
    game_env.timers.flush()
    game_env.advance_cycle()
    assert "Overtaken" in game_env.elements["achievement-toast-text"].innerText
    game_env.timers.flush()
    game_env.advance_cycle()
    assert game_env.elements["achievement-toast"].hidden is True


def test_without_the_switch_nothing_is_ever_recorded(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(10):
        game_env.invest_circularity("recycle")
    chain.advance_cycle()
    assert chain.rival_crossover_cycle is None


def test_the_overtaken_achievement_follows_the_crossover(game_env):
    m = game_env.module
    chain = game_env.chain
    assert "rival_overtaken" not in m.achievement_ids_earned()
    chain.rival_crossover_cycle = 3
    assert "rival_overtaken" in m.achievement_ids_earned()


def test_achievement_and_story_chapter_exist():
    from pathlib import Path
    here = Path(__file__).resolve().parent.parent
    assert "rival_overtaken" in {a["id"] for a in json.loads((here / "achievements.json").read_text())["achievements"]}
    assert "rival_overtaken" in {c["id"] for c in json.loads((here / "story.json").read_text())["chapters"]}


def test_extraction_comparison_names_the_difference(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(10):
        game_env.invest_circularity("recycle")
    rival_on(game_env)
    chain.advance_cycle()
    game_env.module.render()
    assert "you have dug up 0, 50 fewer" in lines(game_env)


def test_save_round_trip_and_defaults(game_env):
    m = game_env.module
    rival_on(game_env)
    game_env.chain.rival_crossover_cycle = 7
    saved = json.loads(json.dumps(m.get_state()))
    assert saved["rival_on"] is True and saved["rival_crossover_cycle"] == 7
    game_env.chain.rival_on = False
    game_env.chain.rival_crossover_cycle = None
    m.load_state(saved)
    assert game_env.chain.rival_on is True and game_env.chain.rival_crossover_cycle == 7
    state = m.get_state()
    state.pop("rival_on"), state.pop("rival_crossover_cycle")
    m.load_state(state)
    assert game_env.chain.rival_on is False and game_env.chain.rival_crossover_cycle is None


@pytest.mark.parametrize("bad", ["3", 0, -1, 2.5, True, None, [], 10**7])
def test_bad_saved_crossover_loads_as_unset(game_env, bad):
    m = game_env.module
    state = m.get_state()
    state["rival_crossover_cycle"] = bad
    state["rival_on"] = bad
    m.load_state(state)
    assert game_env.chain.rival_crossover_cycle is None
    assert game_env.chain.rival_on is (bad is True)
