"""Batch B #3: the crafting tracker, with import-marked ownership where the file allows it."""

import json

import wf_crafting

from .helpers import all_text, click, find_all, known_state

NAMES = ["Ferrite", "Plastids", "Tear Azurite"]


def test_add_craft_and_need_validation():
    crafts = []
    assert wf_crafting.add_craft(crafts, "Excalibur Prime", "warframe")[0] is True
    assert wf_crafting.add_craft(crafts, "excalibur prime", "warframe")[0] is False
    assert wf_crafting.add_craft(crafts, "", "weapon")[0] is False
    assert wf_crafting.add_craft(crafts, "X", "vehicle")[0] is False
    assert wf_crafting.add_need(crafts, "Nope", "Neuroptics", 1)[0] is False
    assert wf_crafting.add_need(crafts, "Excalibur Prime", "Neuroptics", 0)[0] is False
    assert wf_crafting.add_need(crafts, "Excalibur Prime", "Neuroptics", 1, NAMES)[0] is True
    assert wf_crafting.add_need(crafts, "Excalibur Prime", "neuroptics", 1, NAMES)[0] is False
    assert wf_crafting.add_need(crafts, "excalibur prime", "tear azurite", 10, NAMES)[0] is True
    assert crafts[0]["needs"][1]["n"] == "Tear Azurite"  # a tracked resource takes the tracker's own spelling
    for i in range(wf_crafting.NEED_MAX):
        wf_crafting.add_need(crafts, "Excalibur Prime", f"C{i}", 1)
    assert len(crafts[0]["needs"]) == wf_crafting.NEED_MAX
    for i in range(wf_crafting.CRAFT_MAX):
        wf_crafting.add_craft(crafts, f"Item {i}", "weapon")
    assert len(crafts) == wf_crafting.CRAFT_MAX


def test_progress_reads_linked_resources_from_the_live_inventory():
    crafts = []
    wf_crafting.add_craft(crafts, "Kronsh", "weapon")
    wf_crafting.add_need(crafts, "Kronsh", "Ferrite", 100, NAMES)
    wf_crafting.add_need(crafts, "Kronsh", "Neuroptics", 2, NAMES)
    inventory = {"Ferrite": {"built": 60, "raw": 15}}
    info = wf_crafting.craft_progress(crafts[0], inventory, NAMES)
    ferrite, neuro = info["needs"]
    assert ferrite["linked"] and ferrite["have"] == 75 and ferrite["short"] == 25
    assert not neuro["linked"] and neuro["have"] == 0 and neuro["short"] == 2
    assert info["pct"] == round(75 / 102 * 100) and not info["ready"] and not info["owned"]
    wf_crafting.set_have(crafts[0], 1, 2)
    inventory["Ferrite"]["built"] = 100
    info = wf_crafting.craft_progress(crafts[0], inventory, NAMES)
    assert info["ready"] and info["pct"] == 100 and info["source"] == ""


def test_owned_tick_and_import_mark_your_untick_wins():
    crafts = []
    wf_crafting.add_craft(crafts, "Excalibur Prime", "warframe")
    assert wf_crafting.craft_progress(crafts[0], {}, NAMES)["owned"] is False
    wf_crafting.mark_imported(crafts, {"excaliburprime"})
    info = wf_crafting.craft_progress(crafts[0], {}, NAMES)
    assert info["owned"] and info["source"] == "import" and info["pct"] == 100
    wf_crafting.set_owned(crafts[0], False)
    assert crafts[0]["imp"] is False and not wf_crafting.craft_progress(crafts[0], {}, NAMES)["owned"]
    wf_crafting.set_owned(crafts[0], True)
    assert wf_crafting.craft_progress(crafts[0], {}, NAMES)["source"] == "ticked"


def test_owned_tails_reads_the_equipment_arrays_and_tolerates_junk():
    data = {"Suits": [{"ItemType": "/Lotus/Powersuits/Excalibur/ExcaliburPrime"}, {"ItemType": ""}, "x", {"foo": 1}],
            "LongGuns": [{"ItemType": "/Lotus/Weapons/Tenno/Rifle/Rifle/"}], "Melee": "not a list",
            "MiscItems": [{"ItemType": "/Lotus/Items/Ferrite", "ItemCount": 5}]}
    tails, seen = wf_crafting.owned_tails(data)
    assert tails == {"excaliburprime", "rifle"} and seen == 2  # MiscItems is resources, not owned equipment
    assert wf_crafting.owned_tails([]) == (set(), 0) and wf_crafting.owned_tails({"Suits": 5}) == (set(), 0)


def test_import_marks_matching_crafts_and_reports_it(game_env):
    m = game_env.module
    known_state(m)
    wf_crafting.add_craft(m.state["crafts"], "Excalibur Prime", "warframe")
    wf_crafting.add_craft(m.state["crafts"], "Braton Prime", "weapon")
    summary = m.import_last_data(json.dumps({
        "MiscItems": [{"ItemType": "/Lotus/Types/Items/MiscItems/Ferrite", "ItemCount": 10}],
        "Suits": [{"ItemType": "/Lotus/Powersuits/Excalibur/ExcaliburPrime"}],
        "LongGuns": [{"ItemType": "/Lotus/Weapons/Tenno/Rifle/Rifle"}]}))
    crafts = {c["n"]: c for c in m.state["crafts"]}
    assert crafts["Excalibur Prime"]["imp"] is True and crafts["Braton Prime"]["imp"] is False
    assert "1 of your crafting items were marked owned (Excalibur Prime)" in summary
    assert "2 owned item(s)" in game_env.elements["craft-import-note"].textContent
    # a craft added after the import is checked against the same file's owned items
    game_env.elements["craft-kind-select"].value = "warframe"
    game_env.elements["craft-name-input"].value = "excalibur prime"
    click(game_env.elements["craft-add-button"])  # duplicate: rejected
    assert "already" in game_env.elements["craft-message"].textContent
    game_env.elements["craft-name-input"].value = "Rifle"
    click(game_env.elements["craft-add-button"])
    assert {c["n"]: c["imp"] for c in m.state["crafts"]}["Rifle"] is True


def test_import_without_crafts_adds_nothing_to_the_summary(game_env):
    m = game_env.module
    summary = m.import_last_data(json.dumps({"MiscItems": []}))
    assert "crafting items" not in summary


def test_ui_add_item_component_have_and_remove(game_env):
    m = game_env.module
    known_state(m, inventory={"Ferrite": {"built": 50, "raw": 0}})
    els = game_env.elements
    els["craft-name-input"].value = "Kronsh Test"
    els["craft-kind-select"].value = "weapon"
    click(els["craft-add-button"])
    els["craft-need-item-input"].value = "kronsh test"
    els["craft-need-name-input"].value = "Ferrite"
    els["craft-need-qty-input"].value = "80"
    click(els["craft-need-add-button"])
    els["craft-need-name-input"].value = "Neuroptics"
    els["craft-need-qty-input"].value = "1"
    click(els["craft-need-add-button"])
    text = all_text(els["craft-list"])
    assert "Kronsh Test (Weapon)" in text and "Ferrite: 50/80 (from your inventory), short 30" in text
    assert "Neuroptics: 0/1, short 1" in text
    box = find_all(els["craft-list"], tag="input", class_name="craft-have-input")[0]
    box.value = "1"
    box.dispatch("change", None)
    assert m.state["crafts"][0]["needs"][1]["h"] == 1 and "Neuroptics: 1/1" in all_text(els["craft-list"])
    tick = [b for b in find_all(els["craft-list"], tag="input") if b.attributes.get("aria-label") == "Owned: Kronsh Test"][0]
    tick.checked = True
    tick.dispatch("change", None)
    assert m.state["crafts"][0]["own"] is True and "Owned." in all_text(els["craft-list"])
    click(find_all(els["craft-list"], tag="button", text="Remove item")[0])
    assert m.state["crafts"] == []


def test_crafts_do_not_change_needs(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0}})
    before = m.calculate()
    wf_crafting.add_craft(m.state["crafts"], "Thing", "weapon")
    wf_crafting.add_need(m.state["crafts"], "Thing", "Ferrite", 9999, list(m.RESOURCE_LOCATIONS))
    m.render()
    assert m.calculate() == before


def test_load_validation():
    good = {"n": "A", "k": "weapon", "own": False, "imp": True, "needs": [
        {"n": "X", "q": 2, "h": 1}, {"n": "Y", "q": 0, "h": 0}, {"n": "Z", "q": 1, "h": -1}, {"n": "x", "q": 1, "h": 0}]}
    crafts = wf_crafting.load_crafts([good, dict(good, k="ship"), dict(good, own="no"), "junk", dict(good, n="a")])
    assert len(crafts) == 1 and crafts[0]["needs"] == [{"n": "X", "q": 2, "h": 1}] and crafts[0]["imp"] is True
    assert wf_crafting.load_crafts({"a": 1}) == [] and wf_crafting.load_crafts(None) == []
    assert wf_crafting.load_crafts(wf_crafting.export_crafts(crafts)) == crafts
