"""Hub-safe badge ids and entries from shared/seasonal_events.py (W-4)."""

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import seasonal_events as se  # noqa: E402

HUB_ID = re.compile(r"^[a-z0-9-]{1,64}$")  # script.js sanitizeEventBadges


def test_hub_badge_ids_never_contain_underscores():
    for event in se.DEFAULT_EVENTS:
        slug = se.hub_badge_id(dict(event, year=2026))
        assert HUB_ID.match(slug), slug
    ny = dict(se.DEFAULT_EVENTS[0], year=2027)
    assert se.badge_id(ny) == "new_year-2027", "the engine's own id is unchanged"
    assert se.hub_badge_id(ny) == "new-year-2027"
    assert se.hub_badge_id({"id": "halloween"}, 2026) == "halloween-2026"


def test_badge_entry_matches_the_hub_contract():
    event = se.active_events(date(2026, 10, 31))[0]
    entry = se.badge_entry(event, date(2026, 10, 31).isoformat())
    assert entry == {"id": "halloween-2026", "label": "Halloween 2026", "earned_at": "2026-10-31"}
    assert HUB_ID.match(entry["id"]) and len(entry["label"]) <= 60 and len(entry["earned_at"]) <= 32
    custom = se.badge_entry(event, "2026-10-31", label="Night of Storms")
    assert custom["label"] == "Night of Storms" and custom["id"] == "halloween-2026"
    long = se.badge_entry(event, "2026-10-31", label="x" * 100)
    assert len(long["label"]) == 60
