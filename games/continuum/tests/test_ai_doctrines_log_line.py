"""Tests for doctrines.log_line()."""

import pytest

import doctrines
import sim


def test_log_line_formats_maritime_in_agrarian_correctly():
    line = doctrines.log_line("agrarian", "maritime")
    expected = f"Doctrine of the {doctrines.DOCTRINES['maritime']['label']} adopted for the {sim.ERA_LABEL['agrarian']} era."
    assert line == expected


def test_log_line_formats_scholarly_in_classical_correctly():
    line = doctrines.log_line("classical", "scholarly")
    expected = f"Doctrine of the {doctrines.DOCTRINES['scholarly']['label']} adopted for the {sim.ERA_LABEL['classical']} era."
    assert line == expected


def test_log_line_handles_caravan_in_medieval():
    line = doctrines.log_line("medieval", "caravan")
    assert "Doctrine of the" in line
    assert f"{doctrines.DOCTRINES['caravan']['label']}" in line
    assert "era." in line


def test_log_line_raises_keyerror_for_unknown_era():
    with pytest.raises(KeyError):
        doctrines.log_line("nonexistent_era", "maritime")
