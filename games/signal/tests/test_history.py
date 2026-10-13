import datetime
from game import recent_history, reset_engine, utc_today


def test_recent_history_empty():
    """Initially returns no history."""
    reset_engine()
    assert recent_history("easy") == []


def test_recent_history_with_results():
    """Returns results and par for the last n days."""
    reset_engine()
    today = utc_today()
    from game import S
    S["days"][today] = {"easy": "won"}

    hist = recent_history("easy", 1)
    assert len(hist) == 1
    assert hist[0]["date"] == today
    assert hist[0]["result"] == "won"
    assert "par" in hist[0]


def test_recent_history_skips_missing_days():
    """Skips days that haven't been played yet."""
    reset_engine()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    from game import S
    S["days"][yesterday] = {"easy": "lost"}

    hist = recent_history("easy", 3)
    assert len(hist) == 1
    assert hist[0]["date"] == yesterday
