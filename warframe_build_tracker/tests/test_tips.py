"""Batch B #7: per-resource farming tips, each read from the resource's own Wiki page."""

import wf_tips

from .helpers import all_text, find_all, known_state


def test_the_25_most_needed_resources_are_covered_and_all_are_real_tracked_resources(game_env):
    m = game_env.module
    assert wf_tips.COVERED == 25 == len(wf_tips.ORDER) and wf_tips.TRACKED == 65 == len(m.RESOURCE_LOCATIONS)
    assert set(wf_tips.ORDER) <= set(m.RESOURCE_LOCATIONS)
    uses = {r: len(m.resource_usage(r)) for r in m.RESOURCE_LOCATIONS}
    covered_min = min(uses[r] for r in wf_tips.ORDER)
    # nothing left out is used by more parts than the least-used resource that is covered
    assert all(uses[r] <= covered_min for r in m.RESOURCE_LOCATIONS if r not in wf_tips.ORDER)


def test_every_tip_is_sourced_dated_and_either_a_page_sentence_or_an_honest_gap():
    for entry in wf_tips.all_tips():
        assert entry["url"] == "https://wiki.warframe.com/w/" + entry["resource"].replace(" ", "_")
        assert entry["date"] == "2026-09-27"
        assert bool(entry["text"]) != bool(entry["note"])
        if entry["text"]:
            assert entry["section"] and len(entry["text"]) < 260
    with_text = [e for e in wf_tips.all_tips() if e["text"]]
    assert len(with_text) == 16
    gaps = {e["resource"] for e in wf_tips.all_tips() if e["note"]}
    assert "Coprite Alloy" in gaps and "Pyrotic Alloy" in gaps  # refined resources, and the one unverifiable read
    assert wf_tips.tip("Ferrite") is None and wf_tips.tip_line("Ferrite") == ""


def test_specific_figures_are_the_ones_read_from_the_pages():
    assert "28.57%" in wf_tips.tip("Gyromag Systems")["text"]
    assert "50% chance to drop 5" in wf_tips.tip("Breath Of The Eidolon")["text"]
    assert "100% chance" in wf_tips.tip("Condroc Wing")["text"]
    assert "3-5 Iradite" in wf_tips.tip("Iradite")["text"]
    assert "Wiki tip (Acquisition, read 2026-09-27)" in wf_tips.tip_line("Fish Scales")


def test_resource_rows_show_the_tip_line(game_env):
    m = game_env.module
    known_state(m, parts={"Ooltha Strike": {"owned": 0}})
    rows = game_env.elements["resources-body"].children
    fish = next(r for r in rows if r.attributes["data-resource"] == "Fish Scales")
    assert "Wiki tip (Acquisition" in all_text(fish)
    tips = find_all(fish, class_name="resource-tip")
    assert len(tips) == 1
    iradite = next(r for r in rows if r.attributes["data-resource"] == "Iradite")
    assert "3-5 Iradite" in all_text(iradite)


def test_tips_tab_lists_all_with_links(game_env):
    els = game_env.elements
    assert "25 of the 65" in els["tips-summary"].textContent and "16 carry a sentence" in els["tips-summary"].textContent
    cards = els["tips-list"].children
    assert len(cards) == 25
    links = find_all(els["tips-list"], tag="a")
    assert len(links) == 25 and all(a.attributes["href"].startswith("https://wiki.warframe.com/w/") for a in links)
