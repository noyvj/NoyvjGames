"""Tests for neighbours.lease_text()."""


import neighbours


def test_player_holds_lease_within_duration():
    """Normal case: player holds the lease and the season is within its duration."""
    ui = neighbours.ensure({}, 7)
    record = neighbours.get(ui)
    record["lease"]["holder"] = "you"
    record["lease"]["until"] = 100
    text = neighbours.lease_text(record, 50)
    assert f"You hold the lease on {neighbours.SITE_NAME} until season 100." in text


def test_rival_holds_lease_within_duration():
    """Normal case: a rival holds the lease and the season is within its duration."""
    ui = neighbours.ensure({}, 7)
    record = neighbours.get(ui)
    record["seed"] = 7  # ensure seed matches what slot_name expects
    record["lease"]["holder"] = "n2"
    record["lease"]["until"] = 200
    text = neighbours.lease_text(record, 150)
    assert f"{neighbours.slot_name(7, 'n2')} holds the lease on {neighbours.SITE_NAME} until season 200." in text


def test_no_lease_and_auction_settled_this_season():
    """Edge case: no active lease, a pending bid exists, and the auction settles this season."""
    ui = neighbours.ensure({}, 7)
    record = neighbours.get(ui)
    record["lease"]["holder"] = "none"
    record["lease"]["until"] = 10
    record["lease"]["pending"] = 5
    text = neighbours.lease_text(record, 8)
    assert "Nobody holds the lease" in text
    assert "Your bid of 5 materials is in." in text
    assert "The auction is settled this season." in text
