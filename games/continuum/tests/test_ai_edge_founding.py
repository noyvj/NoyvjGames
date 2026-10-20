"""Edge-case tests for founding.py."""


import founding


def test_legacy_id_for_era_handles_valid_and_invalid_inputs():
    assert founding.legacy_id_for_era("tribal") == "seed_stock"
    assert founding.legacy_id_for_era("relay") == "salvage_kit"
    assert founding.legacy_id_for_era("unknown_era") is None
    assert founding.legacy_id_for_era("") is None
    assert founding.legacy_id_for_era(None) is None


def test_make_legacy_accepts_valid_records_and_rejects_invalid():
    valid_record = {"era": "classical"}
    assert founding.make_legacy(valid_record)["id"] == "builders_plans"

    # Missing era
    assert founding.make_legacy({}) is None

    # Wrong type for era
    assert founding.make_legacy({"era": 123}) is None

    # Era not in LEGACIES
    assert founding.make_legacy({"era": "nonexistent"}) is None


def test_clean_legacy_validates_structure_and_applied_flag():
    valid = {"id": "seed_stock", "from_era": "tribal", "applied": False}
    assert founding.clean_legacy(valid) == valid

    # Missing id
    assert founding.clean_legacy({"from_era": "tribal"}) is None

    # Invalid id
    assert founding.clean_legacy({"id": "fake", "from_era": "tribal"}) is None

    # Wrong from_era for the id
    assert founding.clean_legacy({"id": "seed_stock", "from_era": "space"}) is None

    # applied flag variations
    assert founding.clean_legacy({"id": "seed_stock", "from_era": "tribal", "applied": True})["applied"] is True
    assert founding.clean_legacy({"id": "seed_stock", "from_era": "tribal", "applied": False})["applied"] is False


def test_clean_earned_filters_and_clamps_to_max():
    valid_ids = {"a", "b", "c"}
    raw = ["a", "b", "c", "d", "a"]  # 'd' invalid, 'a' duplicate
    result = founding.clean_earned(raw, valid_ids)
    assert result == ["a", "b", "c"]

    # Empty list
    assert founding.clean_earned([], valid_ids) == []

    # Non-list input
    assert founding.clean_earned("junk", valid_ids) == []

    # Exceeds EARNED_MAX (200)
    large_list = [str(i) for i in range(300)]
    result_large = founding.clean_earned(large_list, valid_ids)
    assert len(result_large) <= founding.EARNED_MAX


def test_refuge_unlocked_checks_both_sources():
    # Unlocked by earned_ids
    assert founding.refuge_unlocked(["reached_space"], []) is True
    assert founding.refuge_unlocked(["reached_relay"], []) is True

    # Unlocked by archive records
    archive = [{"era": "space"}, {"era": "relay"}]
    assert founding.refuge_unlocked([], archive) is True

    # Not unlocked
    assert founding.refuge_unlocked([], []) is False
    assert founding.refuge_unlocked([], [{"era": "tribal"}]) is False


def test_found_new_returns_false_when_revisiting():
    class FakeCampaign:
        revisiting = "past_era"

        def load_dict(self, d):
            return True

    campaign = FakeCampaign()
    assert founding.found_new(campaign, None) is False
