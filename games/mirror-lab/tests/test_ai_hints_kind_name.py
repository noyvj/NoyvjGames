"""Tests for hints.kind_name()."""

import hints


def test_kind_name_mirror_returns_mirror():
    """Normal case: mirror piece returns its plain name."""
    assert hints.kind_name("mirror") == "mirror"


def test_kind_name_filter_s_returns_s_filter():
    """Normal case: short filter maps to 'S filter' with capital letter."""
    assert hints.kind_name("filter_s") == "S filter"


def test_kind_name_filter_l_returns_l_filter():
    """Normal case: long filter maps to 'L filter' with capital letter."""
    assert hints.kind_name("filter_l") == "L filter"


def test_kind_name_absorber_returns_absorber():
    """Normal case: absorber piece returns its plain name."""
    assert hints.kind_name("absorber") == "absorber"
