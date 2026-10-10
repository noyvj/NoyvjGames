"""Stranded -- the whole story graph, merged from the story_* tables, plus the lookups the rest of the engine needs."""

import story_1
import story_2
import story_3
import story_4

START = "d1a"
DAYS = 12

SCENES = {}
ORDER = []
for _module in (story_1, story_2, story_3, story_4):
    for _scene in _module.SCENES:
        if _scene["id"] in SCENES:
            raise ValueError("duplicate scene " + _scene["id"])
        SCENES[_scene["id"]] = _scene
        ORDER.append(_scene["id"])

ENDINGS = [(s["end"], s["id"], s["title"]) for s in (SCENES[i] for i in ORDER) if s["end"]]
ENDING_IDS = [e[0] for e in ENDINGS]

# What a locked choice says. Flags that mean "you saw a place or heard a thing"; shown in words, never as a bare code.
FLAG_NEED = {
    "bit": "Needs Bit awake (wake it on day 3)",
    "core": "Needs the core room seen (day 7)",
    "names": "Needs the wall of names seen (day 7)",
    "confess": "Needs the amber light talked about (day 4)",
    "pavel": "Needs Pavel's message opened (day 6)",
}
FLAG_NOT = {}

# CHOICES: (scene id, choice number) for every reply in the story. EDGES: (scene id, choice number, target scene) for every place a
# reply can lead (a reply with a conditional route has one edge per target). The branch map and "paths walked" count edges.
CHOICES = [(sid, i) for sid in ORDER for i in range(len(SCENES[sid]["choices"]))]
EDGES = []
for _sid, _i in CHOICES:
    for _cond, _target in SCENES[_sid]["choices"][_i]["to"]:
        if (_sid, _i, _target) not in EDGES:
            EDGES.append((_sid, _i, _target))
