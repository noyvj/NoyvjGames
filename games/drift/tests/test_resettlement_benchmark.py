"""I9: a real-world resettlement-outcome benchmark comparison -- a
genuine, sourced statistic (Migration Policy Institute: 89% employment
among working-age refugees resettled in the U.S. within the previous
five years, as of 2023), kept factual/institutional per this game's own
sensitivity note, distinct from the structural Uganda-policy comparison.
"""


def test_benchmark_message_cites_the_source_and_figure(game_env):
    message = game_env.module.resettlement_benchmark_message(game_env.region)
    assert "89%" in message
    assert "Migration Policy Institute" in message


def test_benchmark_flags_it_is_a_different_measurement(game_env):
    message = game_env.module.resettlement_benchmark_message(game_env.region)
    assert "not the same measurement" in message


def test_display_starts_below_the_benchmark(game_env):
    display = game_env.elements["resettlement-benchmark-display"]
    assert "below" in display.innerText


def test_display_updates_to_at_or_above_once_coverage_clears_benchmark(game_env):
    region = game_env.region
    region.total_arrivals = 100.0
    region.integrated_population = 95.0  # 95% coverage, above the 89% benchmark
    game_env.module.render()
    display = game_env.elements["resettlement-benchmark-display"]
    assert "at or above" in display.innerText


def test_benchmark_source_is_in_the_info_page(game_env):
    sources = game_env.module.INFO_PAGE["sources"]
    assert any("Migration Policy Institute" in s["label"] and "Faring" in s["label"] for s in sources)
