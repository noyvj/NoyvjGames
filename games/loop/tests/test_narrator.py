"""GH-19: a wry, deterministic narrator ticker under the chain, hidden by the Story switch."""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
INDEX = (HERE / "index.html").read_text(encoding="utf-8")


def line(env):
    return env.elements["narrator-line"].innerText


def test_a_fresh_chain_opens_with_the_opening_topic(game_env):
    assert game_env.module.narrator_topic() == "opening"
    assert line(game_env) in game_env.module.NARRATOR_LINES["opening"]


def test_the_topic_follows_the_chain(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 2000.0
    game_env.advance_cycle()
    assert module.narrator_topic() == "idle"
    game_env.invest_circularity("repair")
    assert module.narrator_topic() == "started"  # 3 of 50 units
    for _ in range(4):
        game_env.invest_circularity("recycle")
    assert module.narrator_topic() == "progress"
    for _ in range(4):
        game_env.invest_circularity("recycle")
    assert module.narrator_topic() == "almost"
    for _ in range(4):
        game_env.invest_circularity("recycle")
    assert chain.is_loop_closed()
    assert module.narrator_topic() == "closed"


def test_a_streak_gets_its_own_comment_with_the_number(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(12):
        game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    game_env.advance_cycle()
    assert chain.closed_loop_streak == 2
    assert game_env.module.narrator_topic() == "streak"
    assert "2" in line(game_env)


def test_damage_with_an_open_loop_is_called_out(game_env):
    chain = game_env.chain
    game_env.advance_cycle()
    chain.total_extracted = 300.0  # 60% damage
    game_env.module.render()
    assert game_env.module.narrator_topic() == "damage"
    assert "60%" in line(game_env)


def test_shocks_and_the_rival_have_their_own_topics(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 500.0
    game_env.advance_cycle()
    chain.market_shocks = True
    chain.cycle_number = 4  # a shock is announced for cycle 5
    assert module.narrator_topic() == "shock"
    chain.market_shocks = False
    chain.rival_on = True
    chain.funds = 1.0
    assert module.narrator_topic() == "rival_ahead"
    chain.funds = 10_000.0
    assert module.narrator_topic() == "rival_behind"


def test_the_same_position_always_reads_the_same(game_env):
    first = game_env.module.narrator_line()
    assert game_env.module.narrator_line() == first
    assert game_env.module.narrator_line() == first


def test_every_template_fills_in_without_error(game_env):
    module = game_env.module
    for topic, variants in module.NARRATOR_LINES.items():
        assert len(variants) >= 2, topic
        for template in variants:
            text = template.format(n=3, extracted="10", pct="40", damage="20", streak=2, rival="R")
            assert "{" not in text and text.strip()


def test_the_ticker_keeps_the_last_few_lines_newest_first(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    seen = [line(game_env)]
    for kind in ("repair", "recycle", "recycle", "recycle"):
        game_env.invest_circularity(kind)
        seen.append(line(game_env))
    history = game_env.module.narrator_history
    assert len(history) <= game_env.module.NARRATOR_HISTORY_MAX
    assert history[-1] == line(game_env)
    html = game_env.elements["narrator-history"].innerHTML
    older = history[:-1]
    assert html.count("<li>") == len(older)
    if older:  # newest of the older lines comes first
        assert html.startswith("<li>" + escape(older[-1]))


def test_the_ticker_never_repeats_the_same_line_twice_in_a_row(game_env):
    game_env.module.render()
    game_env.module.render()
    game_env.module.render()
    history = game_env.module.narrator_history
    assert all(a != b for a, b in zip(history, history[1:]))


def test_the_narrator_comes_with_no_save_state(game_env):
    game_env.module.render()
    state = game_env.module.get_state()
    assert not any("narrator" in key for key in state)


def test_the_ticker_is_hidden_by_the_story_switch():
    assert 'id="narrator-ticker"' in INDEX
    assert "#narrator-ticker" in INDEX.split("story-toggle.js")[1].split("</script>")[0]
