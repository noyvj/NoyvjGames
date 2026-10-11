"""GH-28 / H-7: shareable run codes, a ghost line on the Past chains graph and a side-by-side comparison card."""

import base64
import json
import zlib
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
INDEX = (HERE / "index.html").read_text(encoding="utf-8")


def run_some_cycles(env, cycles=4, funds=2000.0):
    chain = env.chain
    chain.funds = funds
    for i in range(cycles):
        env.invest_circularity("recycle")
        if i % 2:
            env.invest_circularity("reuse")
        env.advance_cycle()


def make_code(module, data):
    raw = json.dumps(data, separators=(",", ":")).encode("ascii")
    payload = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii").rstrip("=")
    return f"{module.GHOST_PREFIX}-{payload}.{module._ghost_check(payload)}"


GOOD = {"v": 1, "g": "clothing", "n": 3, "x": 90, "s": 412, "k": 0, "f": [10, 30, 50],
        "b": [[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0]]}


def test_a_code_needs_a_run_to_share(game_env):
    code, error = game_env.module.build_run_code()
    assert code == "" and "at least one cycle" in error


def test_a_code_round_trips_the_run(game_env):
    module, chain = game_env.module, game_env.chain
    run_some_cycles(game_env)
    code, error = module.build_run_code()
    assert error == "" and code.startswith("LOOPRUN1-") and "." in code
    ghost, problem = module.decode_run_code(code)
    assert problem == ""
    assert ghost["category"] == "electronics" and ghost["cycles"] == 4
    assert ghost["extracted"] == round(chain.total_extracted) and ghost["score"] == round(chain.score())
    assert ghost["fractions"] == [round(f * 100) / 100 for f in chain.circular_fraction_log]
    assert ghost["buys"] == chain.buy_log and ghost["closed"] is None


def test_the_code_holds_nothing_a_player_typed(game_env):
    module = game_env.module
    run_some_cycles(game_env, 2)
    note = game_env.elements["cycle-note-input"]
    note.value = "my secret note"
    game_env.advance_cycle()
    code, _ = module.build_run_code()
    payload = code.split("-", 1)[1].split(".")[0]
    raw = zlib.decompress(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).decode()
    assert "secret" not in raw and set(json.loads(raw)) == {"v", "g", "n", "x", "s", "k", "f", "b"}


def test_only_the_first_sixty_cycles_travel(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 1e6
    for _ in range(70):
        game_env.advance_cycle()
    code, _ = module.build_run_code()
    ghost, _ = module.decode_run_code(code)
    assert ghost["cycles"] == 70 and len(ghost["fractions"]) == 60 and len(ghost["buys"]) == 60


def test_a_run_without_a_purchase_record_still_shares_its_curve(game_env):
    module, chain = game_env.module, game_env.chain
    run_some_cycles(game_env, 3)
    chain.buy_log = []  # e.g. a save from before the log existed
    code, _ = module.build_run_code()
    ghost, _ = module.decode_run_code(code)
    assert ghost["buys"] == [] and len(ghost["fractions"]) == 3


@pytest.mark.parametrize("text,fragment", [
    ("", "Paste a run code"),
    ("   ", "Paste a run code"),
    (None, "Paste a run code"),
    ("hello", "does not look like"),
    ("LOOPRUN2-abc.12345678", "does not look like"),
    ("LOOPRUN1-" + "A" * 6100 + ".12345678", "too long"),
])
def test_bad_input_gets_a_plain_message(game_env, text, fragment):
    ghost, error = game_env.module.decode_run_code(text)
    assert ghost is None and fragment in error


def test_a_typing_mistake_is_caught(game_env):
    module = game_env.module
    code = make_code(module, GOOD)
    flipped = code[:12] + ("A" if code[12] != "A" else "B") + code[13:]
    ghost, error = module.decode_run_code(flipped)
    assert ghost is None and "typing mistake" in error


def test_whitespace_and_line_breaks_are_forgiven(game_env):
    module = game_env.module
    code = make_code(module, GOOD)
    spaced = "  " + code[:20] + "\n" + code[20:] + " \n"
    ghost, error = module.decode_run_code(spaced)
    assert error == "" and ghost["category"] == "clothing"


@pytest.mark.parametrize("change", [
    {"v": 2}, {"g": "spaceships"}, {"n": 0}, {"n": True}, {"n": 2_000_000}, {"x": -1}, {"x": 1.5},
    {"s": "9"}, {"k": -3}, {"f": [10, 30]}, {"f": [10, 30, 101]}, {"f": [10, 30, "x"]}, {"f": "abc"},
    {"b": [[1, 0, 0, 0, 0, 0]]}, {"b": [[1, 0, 0], [0, 0, 0], [0, 0, 0]]}, {"b": "no"},
    {"b": [[1, 0, 0, 0, 0, 9999]] * 3},
])
def test_a_well_checked_code_with_bad_contents_is_refused(game_env, change):
    module = game_env.module
    ghost, error = module.decode_run_code(make_code(module, {**GOOD, **change}))
    assert ghost is None and error


def test_a_code_that_is_not_a_json_object_is_refused(game_env):
    module = game_env.module
    for payload_obj in ([1, 2, 3], "text", 5):
        raw = json.dumps(payload_obj).encode()
        payload = base64.urlsafe_b64encode(zlib.compress(raw)).decode().rstrip("=")
        code = f"{module.GHOST_PREFIX}-{payload}.{module._ghost_check(payload)}"
        ghost, error = module.decode_run_code(code)
        assert ghost is None and error


def test_garbage_that_passes_the_check_is_refused(game_env):
    module = game_env.module
    payload = "AAAAAAAA"
    code = f"{module.GHOST_PREFIX}-{payload}.{module._ghost_check(payload)}"
    ghost, error = module.decode_run_code(code)
    assert ghost is None and "could not be read" in error


def test_a_zip_bomb_is_not_unpacked(game_env):
    module = game_env.module
    raw = b"0" * 3_000_000
    payload = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode().rstrip("=")
    assert len(payload) < module.GHOST_MAX_INPUT
    code = f"{module.GHOST_PREFIX}-{payload}.{module._ghost_check(payload)}"
    ghost, error = module.decode_run_code(code)
    assert ghost is None and "could not be read" in error


def test_loading_a_ghost_draws_it_dotted_and_labelled(game_env):
    module = game_env.module
    run_some_cycles(game_env, 2)
    assert "ghost" not in game_env.elements["past-chains-chart"].innerHTML
    assert module.load_ghost(make_code(module, GOOD)) is True
    module.render()
    svg = game_env.elements["past-chains-chart"].innerHTML
    assert "past-line--ghost" in svg and ">ghost<" in svg and 'stroke-dasharray="1 3"' in svg
    assert module.past_chains_svg().count("<polyline") == 2  # you and the ghost


def test_the_comparison_card_lines_the_runs_up(game_env):
    module, chain = game_env.module, game_env.chain
    run_some_cycles(game_env, 3)
    module.load_ghost(make_code(module, GOOD))
    module.render()
    table = game_env.elements["ghost-table"].innerHTML
    for expected in ("Goods", "Clothing", "Electronics", "Cycles run", "Units extracted", "412", "not yet", "never"):
        assert expected in table
    assert game_env.elements["ghost-compare"].hidden is False
    sparks = game_env.elements["ghost-sparks"].innerText
    assert sparks.startswith("You ") and "Ghost" in sparks


def test_the_gap_sentence_compares_the_same_cycle(game_env):
    module, chain = game_env.module, game_env.chain
    assert module.ghost_gap_text() == ""
    module.load_ghost(make_code(module, GOOD))
    assert "Run a cycle" in module.ghost_gap_text()
    run_some_cycles(game_env, 3)
    text = module.ghost_gap_text()
    mine = round(chain.circular_fraction_log[2] * 100)
    assert f"On cycle 3 the ghost was 50% circular and you were {mine}%" in text
    chain.circular_fraction_log[2] = 0.7
    assert "you are 20 points ahead" in module.ghost_gap_text()
    chain.circular_fraction_log[2] = 0.5
    assert "you are level" in module.ghost_gap_text()
    chain.circular_fraction_log[2] = 0.3
    assert "you are 20 points behind" in module.ghost_gap_text()


def test_the_ghosts_purchases_are_listed_cycle_by_cycle(game_env):
    module = game_env.module
    module.load_ghost(make_code(module, GOOD))
    lines = module.ghost_buy_lines()
    assert lines == ["Cycle 1: Repair x1", "Cycle 2: Reuse x1", "Cycle 3: Recycling x1"]
    module.load_ghost(make_code(module, {**GOOD, "b": []}))
    module.render()
    assert "does not carry its purchases" in game_env.elements["ghost-buys"].innerHTML


def test_removing_the_ghost_clears_everything(game_env):
    module = game_env.module
    module.load_ghost(make_code(module, GOOD))
    game_env.elements["ghost-clear-button"].dispatch("click", None)
    assert module.ghost is None
    assert game_env.elements["ghost-compare"].hidden is True and game_env.elements["ghost-clear-button"].hidden is True
    assert game_env.elements["ghost-message"].innerText == "Ghost removed."


def test_the_buttons_copy_and_load(game_env):
    module = game_env.module
    run_some_cycles(game_env, 2)
    game_env.elements["ghost-copy-button"].dispatch("click", None)
    code = game_env.elements["ghost-code-output"].value
    assert code.startswith("LOOPRUN1-")
    assert "Select the code" in game_env.elements["ghost-message"].innerText  # no clipboard under pytest
    game_env.elements["ghost-code-input"].value = code
    game_env.elements["ghost-load-button"].dispatch("click", None)
    assert module.ghost is not None and "Ghost loaded" in game_env.elements["ghost-message"].innerText
    game_env.elements["ghost-code-input"].value = "nonsense"
    game_env.elements["ghost-load-button"].dispatch("click", None)
    assert module.ghost is not None  # a bad paste leaves the loaded ghost alone
    assert game_env.elements["ghost-message"].attributes["role"] == "alert"


def test_copying_with_no_run_says_why(game_env):
    game_env.elements["ghost-copy-button"].dispatch("click", None)
    assert game_env.elements["ghost-code-output"].value == ""
    assert "at least one cycle" in game_env.elements["ghost-message"].innerText


def test_a_ghost_is_not_part_of_a_save_and_changes_no_rule(game_env):
    module, chain = game_env.module, game_env.chain
    run_some_cycles(game_env, 2)
    before = module.get_state()
    module.load_ghost(make_code(module, GOOD))
    module.render()
    assert module.get_state() == before
    assert not any("ghost" in key for key in before)


def test_the_ghost_is_remembered_in_the_browser(game_env, monkeypatch):
    module = game_env.module
    store = {}

    class Storage:
        def getItem(self, key):
            return store.get(key)

        def setItem(self, key, value):
            store[key] = value

        def removeItem(self, key):
            store.pop(key, None)

    class Window:
        localStorage = Storage()

    monkeypatch.setattr(module, "_window", lambda: Window())
    code = make_code(module, GOOD)
    module.load_ghost(code)
    assert store[module.GHOST_STORAGE_KEY] == code
    module.ghost = None
    module.restore_ghost()
    assert module.ghost["category"] == "clothing"
    store[module.GHOST_STORAGE_KEY] = "junk"
    module.ghost = None
    module.restore_ghost()
    assert module.ghost is None and module.GHOST_STORAGE_KEY not in store
    module.load_ghost(code)
    module.clear_ghost()
    assert module.GHOST_STORAGE_KEY not in store


def test_the_page_has_the_run_code_panel():
    for needed in ('id="ghost-panel"', 'id="ghost-code-input"', 'id="ghost-copy-button"', 'id="ghost-compare"',
                   'maxlength="6000"'):
        assert needed in INDEX
