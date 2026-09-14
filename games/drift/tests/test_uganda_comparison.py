"""Addendum I3: an explicit in-play comparison tying the player's own
integration coverage back to the Uganda policy model already referenced
in index.html's static context blurb. Deliberately structural (broad
access vs. narrow access) rather than a fabricated precise Ugandan
percentage -- see game.py's uganda_comparison_message() docstring and
CLAUDE.md's sensitivity note.
"""


def test_low_coverage_reads_as_short_of_standard(game_env):
    message = game_env.module.uganda_comparison_message(game_env.region)
    assert "still well short of" in message
    assert "0%" in message


def test_mid_coverage_reads_as_partway(game_env):
    region = game_env.region
    region.total_arrivals = 100.0
    region.integrated_population = 50.0
    message = game_env.module.uganda_comparison_message(region)
    assert "partway toward" in message
    assert "50%" in message


def test_high_coverage_reads_as_matching_standard(game_env):
    region = game_env.region
    region.total_arrivals = 100.0
    region.integrated_population = 90.0
    message = game_env.module.uganda_comparison_message(region)
    assert "matching the broad-access standard" in message
    assert "90%" in message


def test_render_populates_uganda_comparison_display(game_env):
    game_env.module.render()
    text = game_env.elements["uganda-comparison-display"].innerText
    assert "Uganda's model" in text
