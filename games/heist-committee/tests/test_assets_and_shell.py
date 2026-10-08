import re
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
ROOT = GAME.parent.parent
HTML = (GAME / "index.html").read_text(encoding="utf-8")


def ids_in(text):
    return set(re.findall(r'(?<![\w-])id="([^"]+)"', text))


def test_every_local_asset_the_page_names_exists():
    for ref in re.findall(r'(?:src|href)="([^"#?]+)"', HTML):
        if ref.startswith(("http", "data:", "mailto:")):
            continue
        assert (GAME / ref).resolve().exists(), ref


def test_every_id_the_scripts_look_up_exists_in_the_page():
    page_ids = ids_in(HTML)
    for name in ("app.js", "plan.js", "settings.js"):
        src = (GAME / name).read_text(encoding="utf-8")
        wanted = set(re.findall(r'\$\("([\w-]+)"\)', src)) | set(re.findall(r'getElementById\("([\w-]+)"\)', src))
        missing = sorted(wanted - page_ids)
        # ids the scripts create themselves are listed here
        missing = [m for m in missing if m not in ()]
        assert not missing, f"{name} looks up ids missing from index.html: {missing}"


def test_page_ids_are_unique():
    ids = re.findall(r'(?<![\w-])id="([^"]+)"', HTML)
    assert len(ids) == len(set(ids))


def test_engine_modules_app_js_loads_all_exist():
    src = (GAME / "app.js").read_text(encoding="utf-8")
    modules = re.search(r"ENGINE_MODULES = \[(.*?)\]", src, re.S).group(1)
    for name in re.findall(r'"([\w.]+\.py)"', modules):
        assert (GAME / name).exists(), name
    content = re.search(r"CONTENT_FILES = \[(.*?)\]", src, re.S).group(1)
    for name in re.findall(r'"(\w+)"', content):
        assert (GAME / "content" / (name + ".json")).exists() or name == "writeups", name


def test_game_py_imports_only_modules_the_page_loads():
    src = (GAME / "app.js").read_text(encoding="utf-8")
    loaded = set(re.findall(r'"([\w]+)\.py"', re.search(r"ENGINE_MODULES = \[(.*?)\]", src, re.S).group(1)))
    game = (GAME / "game.py").read_text(encoding="utf-8")
    local = {p.stem for p in GAME.glob("*.py")}
    for line in game.splitlines():
        m = re.match(r"(?:import|from)\s+(\w+)", line)
        if m and m.group(1) in local:
            assert m.group(1) in loaded, f"game.py imports {m.group(1)} but app.js does not load it"
    for name in loaded:
        for line in (GAME / (name + ".py")).read_text(encoding="utf-8").splitlines():
            m = re.match(r"(?:import|from)\s+(\w+)", line)
            if m and m.group(1) in local:
                assert m.group(1) in loaded, f"{name}.py imports {m.group(1)} but app.js does not load it"


def test_the_page_has_the_standard_shared_includes_in_lexis_order():
    wanted = ["theme.js", "lite-mode.js", "error-boundary.js", "perf-mark.js", "debug-overlay.js", "info-footer.js",
              "site-settings.js", "settings.js"]
    positions = [HTML.index(name) for name in wanted]
    assert positions == sorted(positions)
    for name in ("a11y.css", "touch-targets.css", "lite-mode.css", "save-widget.js", "tutorial.js", "hub-auth.js", "confirm-dialog.js"):
        assert name in HTML


def test_game_id_is_consistent_on_every_include():
    assert set(re.findall(r'data-game-id="([^"]+)"', HTML)) == {"heist-committee"}


def test_favicon_exists_and_is_code_drawn():
    svg = (GAME / "icons" / "favicon-heist-committee.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "<image" not in svg


def test_a_hidden_attribute_always_wins():
    css = (GAME / "style.css").read_text(encoding="utf-8")
    assert "[hidden] { display: none !important; }" in css
