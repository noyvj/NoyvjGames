"""Tests for story.emit_morning()."""

import mysteries
import sim
import unease
from state import Keep
import story


def test_emit_morning_explains_trifle_when_delay_passes():
    """When a trifle's delay has passed, emit_morning explains it, reduces unease, and records it."""
    k = Keep(1)
    sim.to_evening(k)

    tid = mysteries.TRIFLE_ORDER[0]
    safe_night = next(n for n in range(1, 41) if not any(b["at"] == "morning" for _, b in unease.beats_on(k.seed, n)))
    k.night = safe_night

    k.story["trifles"] = {}
    k.story["trifles"][tid] = k.night - 3
    initial_unease = k.story["unease"]

    out = {"beats": []}
    resolved = story.emit_morning(k, out)

    assert resolved is False
    assert any(b["kind"] == "explain" for b in out["beats"])
    assert tid in k.story["explained"]
    assert k.story["unease"] == max(0, initial_unease - 15)
    assert tid in k.meta["story"]["oddities"]


def test_emit_morning_skips_trifle_when_delay_not_met():
    """If the trifle's delay has not passed yet, it is not explained."""
    k = Keep(1)
    sim.to_evening(k)

    tid = mysteries.TRIFLE_ORDER[0]
    safe_night = next(n for n in range(1, 41) if not any(b["at"] == "morning" for _, b in unease.beats_on(k.seed, n)))
    k.night = safe_night

    k.story["trifles"] = {}
    k.story["trifles"][tid] = k.night

    out = {"beats": []}
    story.emit_morning(k, out)

    assert tid not in k.story["explained"]
    assert all(b["kind"] != "explain" for b in out["beats"])


def test_emit_morning_shows_tonight_trifle_if_scheduled_for_morning():
    """If 'tonight' holds a trifle scheduled for morning, it is shown in the output."""
    k = Keep(1)
    sim.to_evening(k)

    morning_trifle = None
    for tid in mysteries.TRIFLE_ORDER:
        if mysteries.TRIFLES[tid]["at"] == "morning":
            morning_trifle = tid
            break
    assert morning_trifle is not None, "Expected at least one trifle scheduled for morning"

    k.night = 5
    k.story["tonight"] = morning_trifle

    out = {"beats": []}
    story.emit_morning(k, out)

    assert any(b["kind"] == "trifle" for b in out["beats"])
    assert morning_trifle in k.story.get("trifles", {})
