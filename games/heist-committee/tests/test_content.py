import json

import content


def test_content_validates(C):
    assert content.validate(C) == []


def test_every_json_file_parses():
    folder = content._find_dir()
    import os
    for name in content.FILES:
        if name in content.OPTIONAL_FILES and not os.path.exists(f"{folder}/{name}.json"):
            continue
        with open(f"{folder}/{name}.json", encoding="utf-8") as fh:
            json.load(fh)


def test_ids_are_stable_snake_case(C):
    import re
    for table in (C.actions, C.traits, C.crew, C.gear, C.complications, C.targets):
        for key in table:
            assert re.fullmatch(r"[a-z][a-z0-9_]*", key), key


def test_five_roles_five_skills(C):
    assert len(C.roles) == 5 and len(C.skills) == 5
    for role in C.roles.values():
        assert role["skill"] in C.skills
        assert role["shape"] and role["icon"]


def test_every_crew_member_has_a_voice_and_a_visible_role(C):
    for crew in C.crew.values():
        assert crew["voice"] and crew["name"] and crew["short"]
        assert crew["fee"] > 0
        assert max(crew["skills"].values()) >= 2


def test_every_tag_has_label_and_icon(C):
    for tag, data in C.tags.items():
        assert data["label"] and data["icon"], tag


def test_validation_catches_a_broken_complication(C):
    import copy
    bad = copy.deepcopy(C.raw)
    bad["complications"]["complications"][0]["requires"] = ["no_such_tag"]
    broken = content.Content(bad)
    assert any("no_such_tag" in p for p in content.validate(broken))


def test_validation_catches_an_auto_complication_without_requirements(C):
    import copy
    bad = copy.deepcopy(C.raw)
    for comp in bad["complications"]["complications"]:
        if comp["trigger"] == "auto":
            comp["requires"] = []
            break
    assert any("auto complication" in p for p in content.validate(content.Content(bad)))


def test_validation_catches_an_unanswerable_complication(C):
    import copy
    bad = copy.deepcopy(C.raw)
    comp = next(c for c in bad["complications"]["complications"] if c["id"] == "dusty_display")
    comp["kinds"] = ["weird"]
    comp["skill_counter"] = None
    assert any("no reachable counter" in p for p in content.validate(content.Content(bad)))
