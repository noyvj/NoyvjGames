"""V-CD-6 (planning/TODO.md, completion-audit section N): a genuinely
visual settlement marker referencing prior-run history, addressing the
finding that E4's legacy system (see tests/test_backlog_e2_e20.py) only
ever produced a text chip row, never anything visual on the settlement
itself. Covers the pure aggregation/tier logic (legacy_category_totals,
legacy_scar_tier, legacy_scar_tiers) and the render()-driven CSS class
each of the three settlement-legacy-scar elements ends up with.
"""


# ---------------------------------------------------------------------------
# Pure logic: category aggregation and tier thresholds.
# ---------------------------------------------------------------------------
def test_legacy_category_totals_all_zero_before_any_run(game_env):
    totals = game_env.module.legacy_category_totals()
    assert totals == {"weather": 0, "non-weather": 0, "social": 0}


def test_legacy_category_totals_aggregate_per_event_type_counts(game_env):
    module = game_env.module
    module.legacy_event_counts.update({
        "flood": 2, "heatwave": 1, "storm": 1,  # weather: 4
        "supply_chain": 3,  # non-weather: 3
        "civil_unrest": 5,  # social: 5
    })
    totals = module.legacy_category_totals()
    assert totals == {"weather": 4, "non-weather": 3, "social": 5}


def test_legacy_scar_tier_thresholds(game_env):
    tier = game_env.module.legacy_scar_tier
    assert tier(0) == 0
    assert tier(1) == 1
    assert tier(2) == 1
    assert tier(3) == 2
    assert tier(5) == 2
    assert tier(6) == 3
    assert tier(50) == 3


def test_legacy_scar_tiers_maps_each_category(game_env):
    module = game_env.module
    module.legacy_event_counts.update({
        "flood": 1,  # weather: 1 -> tier 1
        "supply_chain": 3, "infrastructure_failure": 1,  # non-weather: 4 -> tier 2
        "civil_unrest": 8,  # social: 8 -> tier 3
    })
    assert module.legacy_scar_tiers() == {"weather": 1, "non-weather": 2, "social": 3}


# ---------------------------------------------------------------------------
# render(): the three settlement-legacy-scar elements get the matching
# tier class, and no stale tier class survives an update.
# ---------------------------------------------------------------------------
def _tier_classes(element):
    return {c for c in element.classList._classes if c.startswith("settlement-legacy-scar--tier-")}


def test_scars_untiered_before_any_event_resolves(game_env):
    game_env.module.render()
    for category in ("weather", "non-weather", "social"):
        el = game_env.elements[f"settlement-legacy-scar-{category}"]
        assert _tier_classes(el) == set()


def test_scars_reflect_tiers_after_one_full_run(game_env):
    # One full EVENT_SCHEDULE run weathers: flood x2, heatwave x1, storm x1
    # (weather=4 -> tier 2), supply_chain x1, infrastructure_failure x1
    # (non-weather=2 -> tier 1), civil_unrest x1 (social=1 -> tier 1).
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()
    assert _tier_classes(game_env.elements["settlement-legacy-scar-weather"]) == {"settlement-legacy-scar--tier-2"}
    assert _tier_classes(game_env.elements["settlement-legacy-scar-non-weather"]) == {"settlement-legacy-scar--tier-1"}
    assert _tier_classes(game_env.elements["settlement-legacy-scar-social"]) == {"settlement-legacy-scar--tier-1"}


def test_scars_escalate_across_multiple_runs(game_env):
    for _ in range(2):
        for _ in range(len(game_env.module.EVENT_SCHEDULE)):
            game_env.resolve_event()
        game_env.start_new_run()
    # weather=8 -> tier 3, non-weather=4 -> tier 2, social=2 -> tier 1
    assert _tier_classes(game_env.elements["settlement-legacy-scar-weather"]) == {"settlement-legacy-scar--tier-3"}
    assert _tier_classes(game_env.elements["settlement-legacy-scar-non-weather"]) == {"settlement-legacy-scar--tier-2"}
    assert _tier_classes(game_env.elements["settlement-legacy-scar-social"]) == {"settlement-legacy-scar--tier-1"}


def test_scar_tier_class_does_not_stick_around_when_manually_removed_then_rerendered(game_env):
    module = game_env.module
    module.legacy_event_counts["flood"] = 10
    module.render()
    el = game_env.elements["settlement-legacy-scar-weather"]
    assert _tier_classes(el) == {"settlement-legacy-scar--tier-3"}
    # Simulate a lower total on a later render (e.g. after an import of an
    # older progress code) -- the old, higher tier class must not persist.
    module.legacy_event_counts["flood"] = 1
    module.render()
    assert _tier_classes(el) == {"settlement-legacy-scar--tier-1"}
