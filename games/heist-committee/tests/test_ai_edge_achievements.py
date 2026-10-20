import achievements


class _MockContent:
    """Minimal mock matching what achievements.py expects from content."""

    def __init__(self):
        self.target_order = ["t1", "t2"]
        self.complications = [f"c{i}" for i in range(25)]
        self.traits = {"tr1", "tr2"}
        self.crew = {
            "c1": {"role": "hacker", "rival_of": ["c2"]},
            "c2": {"role": "driver", "rival_of": []}
        }


def test_earned_empty_meta_returns_nothing():
    """earned should return an empty list when meta is completely empty."""
    assert achievements.earned({}, _MockContent()) == []


def test_earned_threshold_values_earns_correct_achievements():
    """earned should award exactly the achievements whose thresholds are met."""
    meta = {
        "jobs_done": 1, "jobs_clean": 1,
        "best": {"chain_links": 5, "absorbed": 3},
        "relationships": {"c1|c2": "friends"},
        "flags": ["everyone_home", "full_house", "over_planner", "minimalist"],
        "cat_targets": ["t1", "t2"],
        "finished_targets": ["the_affineur"],
        "reputation": 20,
        "seen_complications": [f"c{i}" for i in range(20)]
    }
    earned_ids = achievements.earned(meta, _MockContent())
    assert set(earned_ids) == {"first_job", "nobody_saw", "chain_reaction", "absorbed",
                               "old_rivals", "everyone_home", "full_house",
                               "over_planner", "minimalist", "cat_job", "paid_in_cheese",
                               "rich_and_infamous", "committee_meeting"}


def test_earned_below_thresholds_earns_fewer():
    """earned should not award achievements when values are just below thresholds."""
    meta = {
        "jobs_done": 0, "jobs_clean": 0,
        "best": {"chain_links": 4, "absorbed": 2},
        "relationships": {},
        "flags": [],
        "cat_targets": ["t1"],
        "finished_targets": [],
        "reputation": 19,
        "seen_complications": [f"c{i}" for i in range(19)]
    }
    assert achievements.earned(meta, _MockContent()) == []


def test_view_with_empty_meta_marks_all_unearned():
    """view should return all achievements marked as unearned when meta is empty."""
    content = _MockContent()
    view_list = achievements.view({}, content)
    assert len(view_list) == 14
    assert all(not a["earned"] for a in view_list)


def test_view_with_full_meta_marks_all_earned():
    """view should return all achievements marked as earned when meta satisfies all conditions."""
    content = _MockContent()
    full_meta = {
        "jobs_done": 1, "jobs_clean": 1,
        "best": {"chain_links": 5, "absorbed": 3},
        "relationships": {"c1|c2": "friends"},
        "flags": ["everyone_home", "full_house", "over_planner", "minimalist"],
        "cat_targets": ["t1", "t2"],
        "finished_targets": ["the_affineur"],
        "reputation": 20,
        "seen_complications": [f"c{i}" for i in range(20)],
        "retries": {"job1": 5}
    }
    view_list = achievements.view(full_meta, content)
    assert all(a["earned"] for a in view_list)


def test_job_flags_empty_inputs_returns_empty_list():
    """job_flags should return an empty list when crew_ids is empty."""
    outcome = {"cells_used": 0, "cells_total": 10, "escaped": False, "max_actions_in_a_beat": 5, "sidelined": False}
    assert achievements.job_flags(_MockContent(), [], outcome) == []


def test_job_flags_boundary_max_actions_in_a_beat():
    """job_flags should award minimalist at exactly 3 actions but not at 4."""
    content = _MockContent()
    outcome_base = {"cells_used": 10, "cells_total": 10, "escaped": True, "sidelined": False}

    flags_at_3 = achievements.job_flags(content, ["c1", "c2"], {**outcome_base, "max_actions_in_a_beat": 3})
    assert "minimalist" in flags_at_3

    flags_at_4 = achievements.job_flags(content, ["c1", "c2"], {**outcome_base, "max_actions_in_a_beat": 4})
    assert "minimalist" not in flags_at_4


def test_job_flags_cells_used_boundary():
    """job_flags should award over_planner only when cells_used exactly equals cells_total."""
    content = _MockContent()
    outcome_base = {"cells_used": 10, "cells_total": 10, "escaped": True, "max_actions_in_a_beat": 5, "sidelined": False}

    flags_full = achievements.job_flags(content, ["c1", "c2"], {**outcome_base})
    assert "over_planner" in flags_full

    flags_partial = achievements.job_flags(content, ["c1", "c2"], {**outcome_base, "cells_used": 9})
    assert "over_planner" not in flags_partial
