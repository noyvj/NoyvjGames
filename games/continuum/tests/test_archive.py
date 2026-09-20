"""K18 settlement archive (archive.py + game.py wiring) and K20 card payload."""

import json
import sys
import types

import archive
import save
import sim

GOOD_THUMB = archive.THUMB_PREFIX + "QUJD"


def _rec(**over):
    base = {
        "saved_on": "2026-09-21", "era": "tribal", "seasons": 5, "peak_population": 9,
        "peak_score": 80.0, "rank": "Gold", "scenario": "standard", "hard_mode": False,
        "achievements": 2, "thumb": GOOD_THUMB,
    }
    base.update(over)
    return base


def test_valid_record_round_trips():
    assert archive.clean_record(_rec()) == _rec()


def test_bad_records_are_dropped():
    for bad in (None, 5, "x", [], _rec(era="mars"), _rec(saved_on="yesterday"), _rec(seasons="a"),
                _rec(seasons=None), _rec(peak_population=float("nan")), _rec(achievements=None)):
        assert archive.clean_record(bad) is None


def test_fields_are_coerced_safely():
    r = archive.clean_record(_rec(peak_score=float("inf"), rank="Platinum", scenario="nope", hard_mode="yes", seasons=10**12))
    assert r["peak_score"] is None and r["rank"] is None
    assert r["scenario"] == sim.DEFAULT_SCENARIO and r["hard_mode"] is False
    assert r["seasons"] == 10**7
    assert archive.clean_record(_rec(peak_score=500))["peak_score"] == 100.0


def test_thumbnails_are_validated():
    assert archive.clean_thumbnail("javascript:alert(1)") == ""
    assert archive.clean_thumbnail(archive.THUMB_PREFIX + "<script>") == ""
    assert archive.clean_thumbnail(archive.THUMB_PREFIX + "A" * archive.MAX_THUMB_CHARS) == ""
    assert archive.clean_thumbnail(12) == ""
    assert archive.clean_thumbnail(GOOD_THUMB) == GOOD_THUMB


def test_clean_records_handles_garbage_and_caps():
    assert archive.clean_records("not json") == []
    assert archive.clean_records("{}") == []
    assert archive.clean_records(None) == []
    assert archive.clean_records("[" * 100000) == []
    many = [_rec(seasons=i + 1) for i in range(30)]
    out = archive.clean_records(json.dumps(many + ["junk"]))
    assert len(out) == archive.MAX_RECORDS
    assert out[-1]["seasons"] == 30


def test_add_and_remove():
    records = archive.add_record([], _rec())
    records = archive.add_record(records, {"bad": 1})
    assert len(records) == 1
    assert archive.remove_record(records, 5) == records
    assert archive.remove_record(records, True) == records
    assert archive.remove_record(records, 0) == []


def test_make_record_from_a_campaign():
    c = save.Campaign()
    c.state.hard_mode = True
    rec = archive.make_record(c, 3, "2026-09-21")
    assert rec["era"] == "tribal" and rec["hard_mode"] is True and rec["achievements"] == 3
    lines = archive.card_lines(rec)
    assert lines[0].startswith("Tribal era") and any("Hard Mode" in l for l in lines)


class FakeStorage:
    def __init__(self):
        self.data = {}
        self.fail = False

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        if self.fail:
            raise RuntimeError("quota")
        self.data[key] = value


def _install_window(capture=None, download=None):
    storage = FakeStorage()
    win = types.SimpleNamespace(localStorage=storage)
    if capture is not None:
        win.ContinuumVisual = types.SimpleNamespace(capture=capture)
    if download is not None:
        win.ContinuumCard = types.SimpleNamespace(download=download)
    sys.modules["js"].window = win
    return storage


def _open(env):
    env.elements["summary-toggle-button"].dispatch("click", None)


def _panel_ids(env):
    ids = []
    def walk(el):
        for ch in el.children:
            if getattr(ch, "id", None):
                ids.append(ch.id)
            walk(ch)
    walk(env.elements["summary-panel"])
    return ids


def _find(env, wanted):
    def walk(el):
        for ch in el.children:
            if getattr(ch, "id", None) == wanted:
                return ch
            found = walk(ch)
            if found:
                return found
    return walk(env.elements["summary-panel"])


def test_archive_add_persist_delete_and_clear(game_env):
    e = game_env
    storage = _install_window(capture=lambda w, q: GOOD_THUMB)
    _open(e)
    _find(e, "archive-add-button").dispatch("click", None)
    stored = json.loads(storage.data[archive.STORAGE_KEY])
    assert len(stored) == 1 and stored[0]["thumb"] == GOOD_THUMB
    _find(e, "archive-add-button").dispatch("click", None)
    assert len(json.loads(storage.data[archive.STORAGE_KEY])) == 2
    _find(e, "archive-delete-0-button").dispatch("click", None)
    assert len(json.loads(storage.data[archive.STORAGE_KEY])) == 1
    clear = _find(e, "archive-clear-button")
    clear.dispatch("click", None)
    assert len(json.loads(storage.data[archive.STORAGE_KEY])) == 1  # needs a second, confirming click
    _find(e, "archive-clear-button").dispatch("click", None)
    assert json.loads(storage.data[archive.STORAGE_KEY]) == []


def test_archive_survives_corrupt_storage_and_full_storage(game_env):
    e = game_env
    storage = _install_window()
    storage.data[archive.STORAGE_KEY] = "{{{corrupt"
    _open(e)
    assert "archive-add-button" in _panel_ids(e)
    storage.fail = True
    _find(e, "archive-add-button").dispatch("click", None)  # quota error must not raise
    assert e.elements["summary-panel"].hidden is False


def test_archive_without_a_window_still_renders(game_env):
    e = game_env
    _open(e)
    assert "archive-add-button" in _panel_ids(e)
    _find(e, "archive-add-button").dispatch("click", None)
    _find(e, "archive-card-current-button").dispatch("click", None)


def test_capture_result_is_validated_before_storing(game_env):
    e = game_env
    storage = _install_window(capture=lambda w, q: "data:image/svg+xml;base64,PHN2Zz4=")
    _open(e)
    _find(e, "archive-add-button").dispatch("click", None)
    assert json.loads(storage.data[archive.STORAGE_KEY])[0]["thumb"] == ""


def test_card_download_payload(game_env):
    e = game_env
    seen = []
    _install_window(capture=lambda w, q: GOOD_THUMB, download=seen.append)
    _open(e)
    _find(e, "archive-card-current-button").dispatch("click", None)
    payload = json.loads(seen[0])
    assert payload["title"] == "Continuum" and payload["thumb"] == GOOD_THUMB
    assert payload["lines"][0].startswith("Tribal era")
    assert payload["filename"].startswith("continuum-card-tribal-")
