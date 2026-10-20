import festival


def test_day_rules_returns_only_relevant_keys_for_twin():
    assert festival.day_rules("twin") == {"twin": True}


def test_day_rules_filters_out_non_rule_keys_for_harvest():
    # harvest has critic_weight which should be ignored by day_rules
    expected = {"crate_t2": {"produce": (1, 2)}}
    assert festival.day_rules("harvest") == expected


def test_day_rules_collects_multiple_rule_keys_for_kite():
    rules = festival.day_rules("kite")
    assert rules["board_height"] == 5 and rules["combo_floor"] == 2


def test_day_rules_handles_festivals_with_single_matching_key_as_edge_case():
    # slow only has pay_pct from the rule keys; patience_pct is ignored
    assert festival.day_rules("slow") == {"pay_pct": 80}
