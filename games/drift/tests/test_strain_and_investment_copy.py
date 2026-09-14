"""Addendum I6, I7, I20: three small copy-clarity additions that surface
information previously only available inside a details toggle or by
inference:

- I6: a one-line consequence description per strain level (not just the
  colour/label change on the strain bar).
- I7: a one-line effect summary directly on each capacity investment row.
- I20: the economic health gauge's funds-to-score scale reference point.
"""


def test_strain_consequence_message_stable(game_env):
    message = game_env.module.strain_consequence_message(game_env.region)
    assert "keeping pace" in message


def test_strain_consequence_message_strained(game_env):
    region = game_env.region
    region.total_arrivals = 100.0
    region.capacity["housing"] = 50.0  # shortfall 50/100 = 0.5 -> strained (0.25 <= x < 0.6)
    message = game_env.module.strain_consequence_message(region)
    assert region.strain_level() == "strained"
    assert "shortfalls are starting to bite".lower() in message.lower()


def test_strain_consequence_message_critical(game_env):
    region = game_env.region
    region.total_arrivals = 100.0
    # capacity stays at 0 -> shortfall/total = 1.0 -> critical
    message = game_env.module.strain_consequence_message(region)
    assert region.strain_level() == "critical"
    assert "badly outpaced" in message


def test_render_sets_strain_consequence_display(game_env):
    game_env.module.render()
    assert (
        game_env.elements["strain-consequence-display"].innerText
        == game_env.module.STRAIN_LEVEL_CONSEQUENCE["stable"]
    )


def test_capacity_effect_summary_covers_all_types(game_env):
    for capacity_type in game_env.module.CAPACITY_TYPES:
        assert capacity_type in game_env.module.CAPACITY_EFFECT_SUMMARY


def test_render_sets_effect_display_per_capacity_row(game_env):
    game_env.module.render()
    for capacity_type in game_env.module.CAPACITY_TYPES:
        el = game_env.elements[f"{capacity_type}-effect-display"]
        assert el.innerText == game_env.module.CAPACITY_EFFECT_SUMMARY[capacity_type]


def test_services_effect_summary_mentions_integration_uniqueness(game_env):
    assert "only capacity" in game_env.module.CAPACITY_EFFECT_SUMMARY["services"]


def test_economic_health_reference_note_cites_the_real_scale(game_env):
    note = game_env.module.economic_health_reference_note()
    assert f"{game_env.module.WELLBEING_FUNDS_SCALE:.0f}" in note


def test_render_sets_economic_health_reference_display(game_env):
    game_env.module.render()
    assert "1000" in game_env.elements["economic-health-reference-display"].innerText
