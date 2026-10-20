"""Tests for statlog.row_dict().

Verifies that row_dict correctly maps COLUMN_KEYS to values from a row list,
preserves numeric types, and documents its length assumption."""

import pytest

import statlog


def _valid_row():
    """A row built exactly like the game does."""
    return statlog._row_from({"season": 1})


def test_row_dict_maps_keys_to_values_correctly():
    row = _valid_row()
    result = statlog.row_dict(row)
    assert list(result.keys()) == statlog.COLUMN_KEYS
    for i, key in enumerate(statlog.COLUMN_KEYS):
        assert result[key] == row[i]


def test_row_dict_preserves_float_values():
    # Modify a valid row to include specific floats
    row = statlog._row_from({"season": 1})
    row[0] = 0.5
    row[1] = 1.25
    row[2] = -3.7
    result = statlog.row_dict(row)
    assert result[statlog.COLUMN_KEYS[0]] == 0.5
    assert result[statlog.COLUMN_KEYS[1]] == 1.25
    assert result[statlog.COLUMN_KEYS[2]] == -3.7


def test_row_dict_with_shorter_row_raises_index_error():
    """Edge case: row_dict assumes len(row) >= len(COLUMN_KEYS)."""
    short_row = [1.0, 2.0]
    with pytest.raises(IndexError):
        statlog.row_dict(short_row)
