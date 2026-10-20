"""Tests for story.notebook() -- the keeper's notebook of mysteries and oddities."""

import story
import mysteries
from state import Keep


def test_notebook_empty():
    """When no beats or trifles have been recorded, the notebook lists all mysteries as begun=False and shows no trifles."""
    k = Keep(1)
    nb = story.notebook(k)
    assert nb["mysteries_total"] == len(mysteries.MYSTERIES)
    assert nb["trifles_total"] == len(mysteries.TRIFLES)
    for row in nb["mysteries"]:
        assert row["begun"] is False
        assert row["solved"] is False
        assert row["title"] == "A mystery you have not begun"
        assert row["summary"] == ""
        assert row["entries"] == []
    assert nb["trifles"] == []


def test_notebook_with_shown_beats_and_explained_trifle():
    """When a mystery beat and a trifle are recorded, the notebook reflects them correctly."""
    k = Keep(2)
    first_mid = list(mysteries.MYSTERIES.keys())[0]
    first_beat_id = mysteries.MYSTERIES[first_mid]["beats"][0]["id"]
    k.story["beats"].append([first_beat_id, 10])

    first_tid = mysteries.TRIFLE_ORDER[0]
    k.story.setdefault("trifles", {})[first_tid] = 5
    k.story.setdefault("explained", []).append(first_tid)

    nb = story.notebook(k)

    mystery_row = next(r for r in nb["mysteries"] if r["id"] == first_mid)
    assert mystery_row["begun"] is True
    assert mystery_row["solved"] is False
    assert len(mystery_row["entries"]) == 1
    assert mystery_row["entries"][0]["night"] == 10

    trifle_row = next(t for t in nb["trifles"] if t["id"] == first_tid)
    assert trifle_row["odd"] == mysteries.TRIFLES[first_tid]["odd"]
    assert trifle_row["explained"] is True
    assert trifle_row["resolve"] == mysteries.TRIFLES[first_tid]["resolve"]


def test_notebook_unexplained_trifle():
    """A shown trifle that has not yet passed its delay shows explained=False and an empty resolve."""
    k = Keep(3)
    tid = mysteries.TRIFLE_ORDER[0]
    k.story.setdefault("trifles", {})[tid] = 15

    nb = story.notebook(k)
    trifle_row = next(t for t in nb["trifles"] if t["id"] == tid)
    assert trifle_row["explained"] is False
    assert trifle_row["resolve"] == ""
