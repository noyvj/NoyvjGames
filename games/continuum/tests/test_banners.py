"""K-20: cosmetic banners and skyline flourishes."""

import re

import archive
import banners
import dynasty
import monuments


def test_every_catalog_entry_has_a_label_a_unique_id_and_a_drawing():
    ids = [b["id"] for b in banners.BANNERS]
    assert len(ids) == len(set(ids)) and ids[0] == "plain"
    for banner in banners.BANNERS:
        svg = banners.banner_svg(banner["id"], 60)
        assert svg.startswith("<svg") and banner["label"] in svg and "<script" not in svg
        assert "class=" not in svg  # inline attributes only: it must draw onto a canvas as a stand-alone image
    flourish_ids = [f["id"] for f in banners.FLOURISHES]
    assert flourish_ids[0] == "none" and len(flourish_ids) == len(set(flourish_ids))
    assert banners.flourish_svg("none") == "" and banners.flourish_svg("nope") == ""
    for flourish in banners.FLOURISHES[1:]:
        assert banners.flourish_svg(flourish["id"], 300).startswith("<svg")


def test_emblems_are_distinct_shapes_so_nothing_is_colour_alone():
    bodies = {b["id"]: re.sub(r'aria-label="[^"]*"', "", banners.banner_svg(b["id"])) for b in banners.BANNERS}
    assert len(set(bodies.values())) == len(bodies)


def test_every_unlock_rule_refers_to_something_real():
    import json
    from pathlib import Path
    catalog = {a["id"] for a in json.loads((Path(__file__).resolve().parent.parent / "achievements.json").read_text())["achievements"]}
    for item in list(banners.BANNERS) + list(banners.FLOURISHES):
        if "achievement" in item:
            assert item["achievement"] in catalog
        if "rank" in item:
            assert 0 <= item["rank"] < len(dynasty.RANKS)
    assert set(banners.ACHIEVEMENT_KINDS_USED if hasattr(banners, "ACHIEVEMENT_KINDS_USED") else []) <= set(monuments.ACHIEVEMENT_KIND)


def test_unlocking_by_achievement_and_by_rank():
    assert banners.unlocked_banners([], 0) == ["plain"]
    got = banners.unlocked_banners(["reached_agrarian"], 0)
    assert got == ["plain", "sheaf"]
    assert "chevron" in banners.unlocked_banners([], 1) and "bars" not in banners.unlocked_banners([], 1)
    assert set(banners.unlocked_banners([a["achievement"] for a in banners.BANNERS if "achievement" in a], 5)) == set(banners.BANNER_IDS)
    assert banners.unlocked_flourishes([], 0) == ["none"]
    assert "pennants" in banners.unlocked_flourishes([], 1) and "aurora" in banners.unlocked_flourishes([], 3)


def test_choosing_needs_an_unlock_and_junk_falls_back():
    ui = {}
    assert banners.choose(ui, "sheaf", None, [], 0) == (False, "That banner is not unlocked yet.")
    assert banners.choose(ui, "nope", None, [], 0)[0] is False
    assert banners.choose(ui, "sheaf", None, ["reached_agrarian"], 0) == (True, "")
    assert banners.get(ui) == {"banner": "sheaf", "flourish": "none"}
    assert banners.choose(ui, None, "pennants", ["reached_agrarian"], 0)[0] is False
    assert banners.choose(ui, None, "pennants", ["reached_agrarian"], 1)[0] is True
    assert banners.get(ui) == {"banner": "sheaf", "flourish": "pennants"}
    # no longer unlocked (e.g. a hand-edited save): the display falls back to the defaults
    assert banners.effective(ui, [], 0) == {"banner": "plain", "flourish": "none"}
    for raw in (None, 5, {"banner": 3, "flourish": []}, {"banner": "zzz"}):
        assert banners.clean(raw) == banners.DEFAULT_CHOICE
    banners.put(ui, banners.DEFAULT_CHOICE)
    assert banners.KEY not in ui


def test_the_card_payload_carries_labels_and_drawings_only():
    payload = banners.card_payload({"banner": "crown", "flourish": "aurora"})
    assert payload["banner_label"] == "Elder's Crown" and payload["banner_svg"].startswith("<svg")
    assert payload["flourish_label"] == "Aurora arcs" and payload["flourish_svg"].startswith("<svg")
    plain = banners.card_payload(None)
    assert plain["banner_svg"] == "" and plain["flourish_svg"] == ""


def test_archive_records_keep_only_known_cosmetics():
    base = {"saved_on": "2026-10-09", "era": "tribal", "seasons": 3, "peak_population": 6, "achievements": 0}
    record = archive.clean_record(dict(base, banner="crown", flourish="aurora"))
    assert record["banner"] == "crown" and record["flourish"] == "aurora"
    record = archive.clean_record(dict(base, banner="<img onerror=x>", flourish=7))
    assert "banner" not in record and "flourish" not in record
    assert "banner" not in archive.clean_record(dict(base, banner="plain"))
    info = archive.clean_record(dict(base, dynasty={"rank": 2, "perks": ["steady_hands", "zzz", 3, "steady_hands"]}))["dynasty"]
    assert info == {"rank": 2, "perks": ["steady_hands"]}
    assert "dynasty" not in archive.clean_record(dict(base, dynasty={"rank": 0, "perks": []}))
    assert "dynasty" not in archive.clean_record(dict(base, dynasty="junk"))


def test_the_game_shows_unlocks_and_picks_a_banner(game_env):
    module = game_env.module
    el = game_env.elements
    el["dynasty-toggle-button"].dispatch("click", None)
    locked = el["banner-sheaf-button"]
    assert locked.disabled is True and "reached_agrarian" not in locked.title and "Earn the achievement" in locked.title
    unlocked = el["banner-plain-button"]
    assert unlocked.disabled is False
    module.campaign.ui[dynasty.KEY] = {"earned": 6, "owned": []}
    module.render()
    el["banner-chevron-button"].dispatch("click", None)
    el["flourish-pennants-button"].dispatch("click", None)
    assert banners.get(module.campaign.ui) == {"banner": "chevron", "flourish": "pennants"}
    assert module.current_record()["banner"] == "chevron"
    payload_banner = banners.card_payload(banners.get(module.campaign.ui))
    assert payload_banner["banner_label"] == "Steward's Chevron"


def test_the_shareable_card_and_the_gallery_carry_the_chosen_cosmetics(game_env):
    import json

    from .test_archive import _find, _install_window, _open

    sent = []
    storage = _install_window(download=sent.append)
    module = game_env.module
    module.campaign.ui[dynasty.KEY] = {"earned": 6, "owned": []}
    banners.choose(module.campaign.ui, "chevron", "pennants", [], 1)
    game_env.advance_season(2)
    _open(game_env)
    _find(game_env, "archive-card-current-button").dispatch("click", None)
    payload = json.loads(sent[-1])
    assert payload["banner_label"] == "Steward's Chevron" and payload["banner_svg"].startswith("<svg")
    assert payload["flourish_label"] == "Pennants" and payload["flourish_svg"].startswith("<svg")
    _find(game_env, "archive-add-button").dispatch("click", None)
    saved = json.loads(storage.data["continuum-archive-v1"])
    assert saved[0]["banner"] == "chevron" and saved[0]["flourish"] == "pennants"
    assert saved[0]["dynasty"]["rank"] == 1
    _find(game_env, "archive-card-0-button").dispatch("click", None)
    again = json.loads(sent[-1])
    assert again["banner_label"] == "Steward's Chevron"
    assert any("Dynasty Steward" in line for line in json.loads(sent[-1])["lines"])
