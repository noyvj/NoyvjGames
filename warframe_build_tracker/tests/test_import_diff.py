"""Batch B #8: what changed since the previous import."""

import json

import wf_insight

from .helpers import known_state


def _file(**counts):
    """An inventory.json whose MiscItems carry tracked resources by their internal path tail."""
    return json.dumps({"MiscItems": [
        {"ItemType": f"/Lotus/Types/Items/MiscItems/{name}", "ItemCount": count} for name, count in counts.items()]})


def test_diff_needs_two_imports():
    imports = wf_insight.default_imports()
    assert "No import yet" in wf_insight.diff_text(imports)
    assert wf_insight.diff_data(imports) is None
    wf_insight.record_import(imports, "2026-09-27 10:00", {"Ferrite": 100})
    assert wf_insight.diff_data(imports) is None and "One import so far" in wf_insight.diff_text(imports)


def test_new_forward_down_and_unchanged():
    imports = wf_insight.default_imports()
    wf_insight.record_import(imports, "2026-09-27 10:00", {"Ferrite": 100, "Plastids": 50, "Circuits": 20, "Rubedo": 5})
    wf_insight.record_import(imports, "2026-09-28 10:00",
                             {"Ferrite": 130, "Plastids": 10, "Circuits": 20, "Rubedo": 0, "Iradite": 7}, ["Excalibur Prime"])
    data = wf_insight.diff_data(imports)
    assert data["new"] == [{"name": "Iradite", "count": 7}]
    assert [(r["name"], r["delta"]) for r in data["up"]] == [("Ferrite", 30)]
    assert [(r["name"], r["delta"]) for r in data["down"]] == [("Plastids", -40), ("Rubedo", -5)]
    assert data["unchanged"] == 1 and data["from"] == "2026-09-27 10:00" and data["owned"] == ["Excalibur Prime"]
    text = wf_insight.diff_text(imports)
    assert "New: Iradite 7." in text and "Ticked forward: Ferrite +30 (100 to 130)" in text
    assert "Went down (spent): Plastids -40 (50 to 10), Rubedo -5" in text
    assert "Newly marked owned by the import: Excalibur Prime." in text and "1 matched resource(s) unchanged." in text


def test_a_resource_that_was_zero_counts_as_new():
    imports = wf_insight.default_imports()
    wf_insight.record_import(imports, "2026-09-27 10:00", {"Ferrite": 0})
    wf_insight.record_import(imports, "2026-09-28 10:00", {"Ferrite": 5})
    assert wf_insight.diff_data(imports)["new"] == [{"name": "Ferrite", "count": 5}]
    wf_insight.record_import(imports, "2026-09-29 10:00", {"Ferrite": 5})
    assert "No counts changed." in wf_insight.diff_text(imports)


def test_real_imports_record_and_the_tab_shows_the_diff(game_env):
    m = game_env.module
    known_state(m)
    m.state["imports"] = wf_insight.default_imports()
    m.import_last_data(_file(Ferrite=100, Plastids=50))
    assert "One import so far" in game_env.elements["diff-text"].textContent
    m.import_last_data(_file(Ferrite=150, Plastids=50, Circuits=9))
    text = game_env.elements["diff-text"].textContent
    assert "Ticked forward: Ferrite +50 (100 to 150)" in text and "New: Circuits 9." in text
    assert m.state["imports"]["last"]["c"]["Ferrite"] == 150 and m.state["imports"]["prev"]["c"]["Ferrite"] == 100
    # imports never touch part-owned counts or the raw bucket, and the diff changes no needs
    assert all(p["owned"] == p["target"] for p in m.state["parts"].values())


def test_load_validation_and_round_trip():
    tracked = {"Ferrite", "Plastids"}
    snap = {"t": "2026-09-27 10:00", "c": {"Ferrite": 5, "Nope": 1, "Plastids": -1, "x": "y"}, "o": ["A", 5, ""]}
    loaded = wf_insight.load_imports({"last": snap, "prev": dict(snap, t="bad")}, tracked)
    assert loaded["last"] == {"t": "2026-09-27 10:00", "c": {"Ferrite": 5}, "o": ["A"]} and loaded["prev"] is None
    assert wf_insight.load_imports({"prev": snap}, tracked) == wf_insight.default_imports()  # prev alone is meaningless
    assert wf_insight.load_imports("junk", tracked) == wf_insight.default_imports()
    assert wf_insight.export_imports(wf_insight.default_imports()) == {}
    assert wf_insight.load_imports(wf_insight.export_imports(loaded), tracked) == loaded
