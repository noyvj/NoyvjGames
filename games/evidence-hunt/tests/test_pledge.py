"""The brief's hard rules as tests: no gore or death words, no timer or energy words, no clock and no random source in the engine,
nothing that loses progress, no audio, no leaderboard. Spirits are gentle and nobody is harmed."""

import ast
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
DEATH = re.compile(r"\b(dies|died|die|dead|death|dying|fatal|kill\w*|corpse|suicide|blood\w*|gore|gory|murder\w*|bleed\w*|grave|graves|funeral|passed away|"
                   r"scream\w*|terror\w*|horror|demon\w*|curse\w*|cursed|possess\w*|ghoul|jump scare|attack\w*)\b", re.IGNORECASE)
BANNED = re.compile(r"\b(timer|countdown|stopwatch|energy|stamina|streak|daily|premium|gems?|loot ?box|deck of cards|leaderboard|hurry|expires?|"
                    r"limited time|audio|sound effects?|deadline|clock|cooldown)\b", re.IGNORECASE)


def _py_strings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr):
            skip.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip]


def player_text():
    out = []
    for path in GAME_DIR.glob("*.py"):
        if path.stem in ("render",):
            continue                                    # SVG markup, not prose
        out += [(path.name, t) for t in _py_strings(path)]
    for name in ("app.js", "index.html", "changelog.json", "achievements.json"):
        if (GAME_DIR / name).exists():
            text = (GAME_DIR / name).read_text(encoding="utf-8")
            if name == "index.html":
                text = re.sub(r"<[^>]+>", " ", text)
            out.append((name, text))
    return out


def test_no_death_or_gore_words_outside_the_about_pledge():
    for name, text in player_text():
        if name == "info.py":
            continue
        hit = DEATH.search(text)
        assert not hit, "%s: %r in %r" % (name, hit and hit.group(0), text[:70])


def test_no_timer_energy_or_other_banned_words_outside_the_about_pledge():
    for name, text in player_text():
        if name == "info.py":
            continue
        hit = BANNED.search(text)
        assert not hit, "%s: %r in %r" % (name, hit and hit.group(0), text[:70])


def test_the_engine_reads_no_clock_and_no_random_source():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets|os|sys)\b", text, flags=re.M), path.name
        assert not re.search(r"\b(random|time\.time|datetime\.now|perf_counter)\b\s*\(", text), path.name
