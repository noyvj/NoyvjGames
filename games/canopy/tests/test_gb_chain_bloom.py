"""GB-27: several plots reaching maturity within a few ticks ripple their leaf
bursts across the grid in sequence with escalating size (juice only)."""

import re
from pathlib import Path

from .gb_helpers import tile, tile_marks

CSS = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")


def _almost_mature(m, indices):
    for index in indices:
        plot = m.plots[index]
        plot.ticks_intact = m.MATURITY_TICKS - 1
        plot.mature_celebrated = False


def _rank_class(env, index):
    match = re.search(r"plot-chain-bloom-(\d)", tile(env, index).className)
    return int(match.group(1)) if match else None


def test_three_plots_maturing_together_ripple_in_order(game_env):
    m = game_env.module
    _almost_mature(m, [3, 9, 14])
    game_env.tick()
    assert [_rank_class(game_env, i) for i in (3, 9, 14)] == [0, 1, 2]
    assert "plot-chain-bloom" in tile(game_env, 3).className


def test_the_ordinary_burst_is_still_there_and_leaves_are_present(game_env):
    m = game_env.module
    _almost_mature(m, [3, 9, 14])
    game_env.tick()
    marks = tile_marks(game_env, 9)
    assert sum(1 for c in marks if c.startswith("leaf-burst")) == m.LEAF_BURST_COUNT


def test_two_plots_are_not_a_chain(game_env):
    m = game_env.module
    _almost_mature(m, [3, 9])
    game_env.tick()
    assert _rank_class(game_env, 3) is None and _rank_class(game_env, 9) is None
    assert "plot-mature-burst" in tile(game_env, 3).className  # the normal B4 burst remains


def test_a_late_plot_extends_the_chain_with_a_bigger_rank(game_env):
    m = game_env.module
    _almost_mature(m, [3, 9, 14])
    game_env.tick()
    _almost_mature(m, [20])
    game_env.tick()
    assert _rank_class(game_env, 20) == 3
    assert _rank_class(game_env, 3) == 0  # the earlier plots ripple again, in order


def test_plots_outside_the_window_do_not_join(game_env):
    m = game_env.module
    _almost_mature(m, [3, 9])
    game_env.tick()
    game_env.tick(m.CHAIN_BLOOM_WINDOW_TICKS)
    _almost_mature(m, [14])
    game_env.tick()
    assert _rank_class(game_env, 14) is None


def test_the_ripple_plays_once(game_env):
    m = game_env.module
    _almost_mature(m, [3, 9, 14])
    game_env.tick()
    m.render()
    assert _rank_class(game_env, 3) is None


def test_ranks_are_capped(game_env):
    m = game_env.module
    idx = list(range(12))
    _almost_mature(m, idx)
    game_env.tick()
    assert max(_rank_class(game_env, i) for i in idx) == m.CHAIN_BLOOM_MAX_RANK


def test_it_changes_no_numbers(game_env):
    m = game_env.module
    game_env.tick(2)
    before = m.get_state()
    m._register_chain_bloom([1, 2, 3, 4])
    m.render()
    after = m.get_state()
    for key in ("plots", "total_income", "community_relations", "forest_log", "forest_tick"):
        assert before[key] == after[key], key


def test_css_has_every_rank_delay_growing_and_a_reduced_motion_rule():
    sizes = []
    delays = []
    for rank in range(8):
        rule = re.search(rf"\.plot-chain-bloom-{rank} \.leaf-burst \{{([^}}]*)\}}", CSS)
        assert rule, rank
        delays.append(int(re.search(r"animation-delay: (\d+)ms", rule.group(1)).group(1)))
        sizes.append(float(re.search(r"font-size: ([\d.]+)rem", rule.group(1)).group(1)))
    assert delays == sorted(delays) and sizes == sorted(sizes) and len(set(sizes)) == 8
    assert re.search(r"prefers-reduced-motion: reduce\) \{[^@]*\.plot-chain-bloom \.leaf-burst \{ animation: none", CSS)
