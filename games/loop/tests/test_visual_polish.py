"""Milestone 7: visual pass — the before/after chain-flow visual (straight
line vs. closed loop) the plan flagged as worth prioritizing.
"""


def test_chain_flow_message_straight_line_by_default(game_env):
    game_env.module.render()
    assert (
        game_env.elements["chain-flow-message"].innerText
        == "Straight line: 100% of production needs new extraction."
    )


def test_chain_flow_message_partial(game_env):
    game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert "10%" in game_env.elements["chain-flow-message"].innerText


def test_chain_flow_message_closed(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert "Loop closed" in game_env.elements["chain-flow-message"].innerText


def test_chain_flow_gets_closed_class_when_loop_closed(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert "chain-flow--closed" in game_env.elements["chain-flow"].className


def test_chain_flow_not_closed_class_by_default(game_env):
    game_env.module.render()
    assert "chain-flow--closed" not in game_env.elements["chain-flow"].className


def test_extract_stage_marked_inactive_when_closed(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert "chain-stage--inactive" in game_env.elements["stage-extract"].className


def test_extract_stage_active_by_default(game_env):
    game_env.module.render()
    assert "chain-stage--inactive" not in game_env.elements["stage-extract"].className
