"""Batch B #6: the manual kubrow/kavat breeding and imprint log."""

import wf_crafting

from .helpers import all_text, click, find_all, known_state


def test_add_validation_and_the_kubrow_limit_the_wiki_states():
    pets = []
    assert wf_crafting.add_pet(pets, "Rex", "kubrow", 1, "Bite", "second-gen")[0] is True
    assert wf_crafting.add_pet(pets, "rex", "kubrow", 0, "", "")[0] is False
    assert wf_crafting.add_pet(pets, "", "kubrow", 0, "", "")[0] is False
    assert wf_crafting.add_pet(pets, "X", "dog", 0, "", "")[0] is False
    ok, message = wf_crafting.add_pet(pets, "Y", "kubrow", 3, "", "")
    assert ok is False and "only 2 imprints" in message
    assert wf_crafting.add_pet(pets, "Kit", "kavat", 5, "", "")[0] is True  # the Wiki names no Kavat limit
    assert wf_crafting.add_pet(pets, "Z", "kavat", 10, "", "")[0] is False
    for i in range(wf_crafting.PET_MAX):
        wf_crafting.add_pet(pets, f"P{i}", "kavat", 0, "", "")
    assert len(pets) == wf_crafting.PET_MAX


def test_bump_imprint_respects_the_kubrow_limit():
    pets = []
    wf_crafting.add_pet(pets, "Rex", "kubrow", 1, "", "")
    assert wf_crafting.bump_imprint(pets, "rex")[0] is True and pets[0]["i"] == 2
    ok, message = wf_crafting.bump_imprint(pets, "Rex")
    assert ok is False and pets[0]["i"] == 2 and "2 imprints" in message
    assert wf_crafting.bump_imprint(pets, "Nobody")[0] is False
    assert "0 left" in wf_crafting.pet_line(pets[0])


def test_facts_are_sourced_and_dated():
    assert wf_crafting.PET_FACTS_DATE == "2026-09-27"
    assert all(url.startswith("https://wiki.warframe.com/w/") for _text, url in wf_crafting.PET_FACTS)
    joined = " ".join(text for text, _url in wf_crafting.PET_FACTS)
    assert "48 hours" in joined and "1.5 hours" in joined and "10 Kavat Genetic Codes" in joined


def test_ui_log_bump_timer_and_remove(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    assert "48 hours" in all_text(els["pet-facts"]) and "read 2026-09-27" in all_text(els["pet-facts"])
    els["pet-name-input"].value = "Rex"
    els["pet-kind-select"].value = "kubrow"
    els["pet-imprints-input"].value = "1"
    els["pet-mods-input"].value = "Bite, Fetch"
    click(els["pet-add-button"])
    assert m.state["pets"] == [{"n": "Rex", "k": "kubrow", "i": 1, "m": "Bite, Fetch", "t": ""}]
    assert "Rex (kubrow): 1 imprint(s) logged, 1 left. Mods: Bite, Fetch" in all_text(els["pet-list"])
    click(find_all(els["pet-list"], tag="button", text="+1 imprint")[0])
    assert m.state["pets"][0]["i"] == 2
    click(find_all(els["pet-list"], tag="button", text="Imprint timer")[0])
    assert m.state["timers"][-1]["n"] == "Imprint Rex"
    assert "1.5 hour" in els["pet-message"].textContent
    click(find_all(els["pet-list"], tag="button", text="Remove")[0])
    assert m.state["pets"] == []


def test_load_validation_and_round_trip():
    good = {"n": "Rex", "k": "kubrow", "i": 2, "m": "x", "t": "y"}
    pets = wf_crafting.load_pets([good, dict(good, n="Bad", i=3), dict(good, n="Bad2", k="dog"), dict(good, n="rex"),
                                  dict(good, n="Bad3", i=True), dict(good, n="Bad4", m=5), "junk"])
    assert pets == [good]
    assert wf_crafting.load_pets({"a": 1}) == []
    assert wf_crafting.load_pets(wf_crafting.export_pets(pets)) == pets
