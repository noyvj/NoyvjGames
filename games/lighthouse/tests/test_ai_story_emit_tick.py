"""Tests for story.emit_tick()."""

import sim
import story
import unease
import mysteries
from state import Keep


def test_emit_tick_quiet_skips():
    """Quiet mode should return early without adding logs or modifying state."""
    k = Keep(2)
    k.quiet = True
    sim.to_evening(k)
    before_log_len = len(k.log)
    story.emit_tick(k, 1)
    assert len(k.log) == before_log_len


def test_emit_tick_records_trifle_at_matching_tick():
    """When the tick matches a trifle's phase, it should be recorded and logged."""
    k = Keep(2)
    sim.to_evening(k)

    tid = next(t for t in mysteries.TRIFLES if mysteries.TRIFLES[t]["at"] != "morning")
    k.story["tonight"] = tid

    phase = mysteries.TRIFLES[tid]["at"]
    tick = unease.beat_tick(k.night, phase)

    before_trifles = dict(k.story["trifles"])
    story.emit_tick(k, tick)

    assert tid in k.story["trifles"], "Trifle should be recorded"
    assert k.story["trifles"][tid] == k.night, "Trifle night should match current night"
    new_logs = k.log[len(before_trifles):]
    assert any(e[1] == "odd" for e in new_logs), "Should log the trifle as odd"


def test_emit_tick_fires_beat_at_matching_tick():
    """When the tick matches a beat's phase, it should fire and add to logs."""
    k = Keep(2)
    sim.to_evening(k)

    target_tick = None
    target_night = k.night
    # Find a night that has at least one non-morning beat for this seed
    for n in range(1, 50):
        for mid, beat in unease.beats_on(k.seed, n):
            if beat["at"] != "morning":
                target_tick = unease.beat_tick(n, beat["at"])
                target_night = n
                break
        if target_tick:
            break

    assert target_tick is not None, "Could not find a night with a non-morning beat for this seed"
    k.night = target_night

    before_log_len = len(k.log)
    story.emit_tick(k, target_tick)

    assert len(k.log) > before_log_len, "A beat should have fired and added a log entry"
