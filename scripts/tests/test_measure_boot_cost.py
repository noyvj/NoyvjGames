"""scripts/measure-boot-cost.py (TODO LZ-1): the static boot-cost measurement. A made-up game tree
checks how files are found, counted and grouped (and that a pack already deferred by modules.json
leaves the boot figures); the real repository checks the script copes with every game and that its
JSON and table output keep their shape."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "measure-boot-cost.py"
spec = importlib.util.spec_from_file_location("measure_boot_cost", SCRIPT)
mb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mb)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A tiny repo: shared/ with a script, a style and a module; games/demo with an engine list in app.js."""
    write(tmp_path / "shared" / "tool.js", "x" * 1000)
    write(tmp_path / "shared" / "tool.css", "y" * 500)
    write(tmp_path / "shared" / "seed.py", "z = 1\n" * 100)
    game = tmp_path / "games" / "demo"
    write(game / "index.html", '<!doctype html><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="../../shared/tool.css">'
                               '<script src="../../shared/tool.js"></script><script src="app.js"></script>'
                               '<script>inline code here</script><style>b{}</style>')
    write(game / "style.css", "s" * 200)
    write(game / "app.js", '''
      // "commented.py" is only named in a comment
      var ENGINE_MODULES = ["rooms_a.py", "rooms_b.py", "engine.py"];
      for (const f of ["seed.py"]) { fetch("../../shared/" + f); }
      fetch("levels.json"); fetch("achievements.json"); fetch("packed.py");
      fetch("content/" + name);
    ''')
    write(game / "game.py", "X = 1\n\ndef setup():\n    return 1\n\n\nclass Big:\n    pass\n")
    write(game / "rooms_a.py", "a = 1\n" * 2000)
    write(game / "rooms_b.py", "b = 1\n" * 2500)
    write(game / "engine.py", "e = 1\n" * 700)
    write(game / "commented.py", "c = 1\n" * 3000)
    write(game / "packed.py", "p = 1\n" * 4000)
    write(game / "levels.json", json.dumps({"levels": ["q" * 100] * 80}))
    write(game / "achievements.json", "{}")
    write(game / "content" / "one.json", json.dumps({"k": "v" * 7000}))
    write(game / "content" / "two.json", json.dumps({"k": "v" * 7000}))
    write(game / "tests" / "test_x.py", "def test(): pass\n")
    monkeypatch.setattr(mb, "ROOT", tmp_path)
    monkeypatch.setattr(mb, "GAMES", tmp_path / "games")
    monkeypatch.setattr(mb, "SHARED", tmp_path / "shared")
    return game


def test_files_named_in_scripts_are_found_and_counted(tree):
    r = mb.measure_game("demo")
    names = {m["name"] for m in r["python_module_list"]}
    assert {"rooms_a.py", "rooms_b.py", "engine.py", "packed.py"} <= names
    assert "commented.py" not in names                      # named only in a comment
    assert "game.py" not in names and r["game_py_lines"] == 8
    assert r["python_modules"] == 4
    assert r["shared_python_bytes"] == len("z = 1\n" * 100)  # "seed.py" found in shared/ through the game's list
    assert {j["name"] for j in r["json_list"]} == {"levels.json", "achievements.json", "one.json", "two.json"}  # content/ folder named as a prefix
    assert r["shared_script_bytes"] == 1000 and r["shared_style_bytes"] == 500
    assert r["own_style_bytes"] == 200
    assert r["inline_script_bytes"] == len("inline code here") and r["inline_style_bytes"] == len("b{}")
    assert r["total_bytes"] > sum(m["bytes"] for m in r["python_module_list"])
    assert 0 < r["wire_bytes_est"] < r["total_bytes"]       # the highly repetitive test files compress well


def test_candidates_group_families_and_skip_core_files(tree):
    r = mb.measure_game("demo")
    by_label = {c["candidate"]: c for c in r["candidates"]}
    assert "rooms_* (2 files)" in by_label
    assert by_label["rooms_* (2 files)"]["bytes"] == len("a = 1\n" * 2000) + len("b = 1\n" * 2500)
    assert by_label["rooms_* (2 files)"]["files"] == ["rooms_a.py", "rooms_b.py"]
    assert "content/ (2 files)" in by_label and by_label["content/ (2 files)"]["kind"] == "json"
    assert "achievements.json" not in by_label and "game.py" not in by_label
    assert [c["bytes"] for c in r["candidates"]] == sorted((c["bytes"] for c in r["candidates"]), reverse=True)
    assert r["candidate_bytes"] == sum(c["bytes"] for c in r["candidates"])


def test_a_pack_already_in_modules_json_leaves_the_boot_figures(tree):
    before = mb.measure_game("demo")
    write(tree / "modules.json", json.dumps({"version": 1, "packs": [
        {"id": "packed", "label": "Packed", "kind": "python", "url": "packed.py", "bytes": 24000},
        {"id": "ghost", "label": "Ghost", "kind": "json", "url": "missing.json"}]}))
    after = mb.measure_game("demo")
    assert "packed.py" in {m["name"] for m in before["python_module_list"]}
    assert "packed.py" not in {m["name"] for m in after["python_module_list"]}
    assert after["deferred_pack_bytes"] == len("p = 1\n" * 4000)
    assert [d["id"] for d in after["deferred_packs"]] == ["packed"]            # a pack whose file is missing is not counted
    assert after["python_module_bytes"] == before["python_module_bytes"] - len("p = 1\n" * 4000)


def test_unreferenced_python_files_are_listed_but_not_counted(tree):
    r = mb.measure_game("demo")
    assert r["unreferenced_py"] == ["commented.py"]


def test_game_py_anatomy_finds_the_big_blocks(tmp_path):
    src = tmp_path / "game.py"
    src.write_text("DATA = " + repr(["x" * 50] * 100) + "\n\ndef render_a():\n    return 1\n\ndef render_b():\n    return 2\n\nclass Big:\n    def f(self):\n        return 'ok'\n", encoding="utf-8")
    an = mb.anatomy(src)
    assert an["top_blocks"][0]["name"] == "DATA" and an["top_blocks"][0]["kind"] == "data"
    assert an["data_constant_bytes"] > 5000 and an["top_level_blocks"] == 4
    assert any(g["prefix"] == "render" and g["blocks"] == 2 for g in an["top_prefix_groups"])
    assert mb.anatomy(tmp_path / "missing.py") == {}
    (tmp_path / "bad.py").write_text("def (:\n", encoding="utf-8")
    assert mb.anatomy(tmp_path / "bad.py") == {}


def test_family_names():
    assert mb.family_of("rooms_loops.py") == "rooms" and mb.family_of("cases_3.py") == "cases"
    assert mb.family_of("engine.py") == "engine" and mb.family_of("story_json.py") == "story"


# ---------------------------------------------------------------------------------- the real repository

def run_script(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT, timeout=60)


def test_every_real_game_can_be_measured():
    rows = [mb.measure_game(s) for s in mb.game_slugs()]
    assert len(rows) >= 20
    for r in rows:
        assert r["index_html_bytes"] > 0 and r["total_bytes"] >= r["index_html_bytes"] + r["game_py_bytes"], r["slug"]
        assert r["wire_bytes_est"] < r["total_bytes"], r["slug"]


def test_known_shapes_of_a_few_real_games():
    continuum = mb.measure_game("continuum")
    assert any("three" in u for u in continuum["cdn_scripts"])                      # Three.js is a CDN script, never counted as a Python module
    assert continuum["python_modules"] >= 40 and any(m["name"] == "sim.py" for m in continuum["python_module_list"])
    canopy = mb.measure_game("canopy")
    assert canopy["game_py_lines"] > 5000 and canopy["python_modules"] == 0
    assert canopy["game_py_anatomy"]["top_blocks"]
    champ = mb.measure_game("champ-de-mots")
    assert any(j["name"] == "fren_combined_catalog.json" for j in champ["json_list"])
    heist = mb.measure_game("heist-committee")
    assert {j["name"] for j in heist["json_list"]} >= {"complications.json", "targets.json"}   # content/ folder


def test_json_output_is_machine_readable_and_sorted_heaviest_first():
    out = run_script("--json", "continuum", "canopy", "lexis")
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert data["version"] == 1
    sizes = [g["total_bytes"] for g in data["games"]]
    assert sizes == sorted(sizes, reverse=True) and {g["slug"] for g in data["games"]} == {"continuum", "canopy", "lexis"}


def test_table_output_and_detail_flag():
    out = run_script("tide")
    assert out.returncode == 0 and out.stdout.splitlines()[0].startswith("game") and "tide" in out.stdout
    detail = run_script("--detail", "tide")
    assert "biggest prefix groups" in detail.stdout and "SettlementState" in detail.stdout


def test_unknown_game_is_an_error():
    out = run_script("no-such-game")
    assert out.returncode == 2 and "unknown game" in out.stderr


def test_the_script_only_reads_the_repository():
    text = SCRIPT.read_text(encoding="utf-8")
    for forbidden in ("write_text", "write_bytes", "open(", "subprocess", "urllib", "requests", "socket"):
        assert forbidden not in text.split('"""', 2)[2], forbidden
