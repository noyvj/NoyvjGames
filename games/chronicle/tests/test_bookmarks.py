import json

import pytest
from core import S, MAX_BOOKMARKS
from game import handle


@pytest.fixture(autouse=True)
def reset_engine():
    from core import reset_engine as re
    re()
    yield


def p(action, **kwargs):
    return json.loads(handle({"action": action, **kwargs}))


def test_bookmark_name():
    p("start", section="s1")
    res = p("bookmark", name="Nice")
    assert res["ok"] is True
    assert S["bookmarks"] == [{"name": "Nice", "set": "presidents-sample", "section": "s1", "round": 0}]


def test_replace_same_name():
    p("start", section="s1")
    p("bookmark", name="Nice")
    res = p("bookmark", name="Nice")
    assert res["ok"] is True
    assert len(S["bookmarks"]) == 1


def test_empty_spaces_max_length_names():
    p("start", section="s1")
    assert p("bookmark", name="")["ok"] is False
    assert p("bookmark", name="   ")["ok"] is False
    assert p("bookmark", name="a" * 31)["ok"] is False


def test_full_shelf():
    p("start", section="s1")
    for i in range(MAX_BOOKMARKS):
        res = p("bookmark", name=f"b{i}")
        assert res["ok"] is True
    assert len(S["bookmarks"]) == MAX_BOOKMARKS
    res = p("bookmark", name="b20")
    assert res["ok"] is False
    assert len(S["bookmarks"]) == MAX_BOOKMARKS


def test_unbookmark():
    p("start", section="s1")
    p("bookmark", name="Keep")
    p("bookmark", name="Remove")
    res = p("unbookmark", name="Remove")
    assert res["ok"] is True
    assert len(S["bookmarks"]) == 1
    assert S["bookmarks"][0]["name"] == "Keep"


def test_unbookmark_unknown():
    p("start", section="s1")
    p("bookmark", name="Keep")
    res = p("unbookmark", name="Ghost")
    assert res["ok"] is False
