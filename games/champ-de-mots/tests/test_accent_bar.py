"""L-20: the on-screen accent bar beside every typed-answer box."""

import re
from pathlib import Path

HTML = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def _keys(env, bar_id):
    return env.elements[bar_id].children


def _press(env, bar_id, char):
    for key in _keys(env, bar_id):
        if key.innerText == char:
            key.dispatch("click", None)
            return key
    raise AssertionError(f"no {char!r} key in {bar_id}")


def test_every_typed_box_has_a_bar_in_the_markup():
    boxes = re.findall(r'<input id="([a-z-]+-answer-input)"', HTML)
    assert len(boxes) >= 6
    for box in boxes:
        stem = box[: -len("-answer-input")]
        assert f'id="accent-bar-{stem}"' in HTML, box


def test_each_bar_is_wired_to_a_real_input(game_env):
    module = game_env.module
    for bar_id, input_id in module.ACCENT_BARS.items():
        assert bar_id in game_env.elements and input_id in game_env.elements
        assert len(_keys(game_env, bar_id)) == len(module.ACCENT_CHARS)


def test_keys_carry_names_and_stay_out_of_the_tab_order(game_env):
    module = game_env.module
    for key in _keys(game_env, "accent-bar-practice"):
        assert key.getAttribute("tabindex") == "-1"
        assert key.getAttribute("aria-label").startswith(key.innerText + ",")
        assert key.type == "button"
    chars = [c for c, _n in module.ACCENT_CHARS]
    for needed in "éèêëàâîïôùûüçœ":
        assert needed in chars


def test_a_key_appends_when_there_is_no_caret_info(game_env):
    box = game_env.elements["practice-answer-input"]
    box.value = "cafe"
    _press(game_env, "accent-bar-practice", "é")
    assert box.value == "cafeé"


def test_a_key_inserts_at_the_caret_and_replaces_a_selection(game_env):
    module = game_env.module
    box = game_env.elements["review-answer-input"]
    box.value = "ecole"
    box.selectionStart = box.selectionEnd = 0
    _press(game_env, "accent-bar-review", "é")
    assert box.value == "éecole"
    assert box.selectionStart == 1 and box.focused is True
    box.value = "ecole"
    box.selectionStart, box.selectionEnd = 0, 1
    assert module.insert_accent("review-answer-input", "ê") == "êcole"


def test_junk_caret_values_never_lose_the_letter(game_env):
    module = game_env.module
    box = game_env.elements["practice-answer-input"]
    box.value = "abc"
    for start, end in ((None, None), (True, False), ("2", "3"), (2, 1), (99, 100)):
        box.value = "abc"
        box.selectionStart, box.selectionEnd = start, end
        result = module.insert_accent("practice-answer-input", "ç")
        assert result.count("ç") == 1 and result.replace("ç", "") == "abc"
    box.value = "abc"
    box.selectionStart, box.selectionEnd = -5, 99  # clamped to the whole text, so it is replaced
    assert module.insert_accent("practice-answer-input", "ç") == "ç"


def test_mousedown_is_cancelled_so_the_box_keeps_focus(game_env):
    key = _keys(game_env, "accent-bar-practice")[0]

    class Evt:
        prevented = False

        def preventDefault(self):
            self.prevented = True

    evt = Evt()
    key.dispatch("mousedown", evt)
    assert evt.prevented is True


def test_a_bar_shows_only_while_its_box_shows(game_env):
    module = game_env.module
    plot = next(p for p in game_env.state.plots if "fr_to_en_typed" in module.variants_for(p))
    module.open_practice(plot.plot_id, variant="fr_to_en_typed")
    assert game_env.elements["practice-answer-input"].hidden is False
    assert game_env.elements["accent-bar-practice"].hidden is False
    choice_plot = next(p for p in game_env.state.plots if "fr_to_en_choice" in module.variants_for(p))
    module.open_practice(choice_plot.plot_id, variant="fr_to_en_choice")
    assert game_env.elements["practice-answer-input"].hidden is True
    assert game_env.elements["accent-bar-practice"].hidden is True


def test_the_bar_dims_when_the_accent_check_is_off(game_env):
    module = game_env.module
    module.render()
    assert "accent-bar--optional" not in game_env.elements["accent-bar-practice"].className
    game_env.elements["accent-toggle-checkbox"].dispatch("click", None)
    assert module.ACCENT_SENSITIVE is False
    bar = game_env.elements["accent-bar-practice"]
    assert "accent-bar--optional" in bar.className
    assert "optional" in bar.title
    game_env.elements["accent-toggle-checkbox"].dispatch("click", None)
    assert "accent-bar--optional" not in game_env.elements["accent-bar-practice"].className


def test_typing_with_the_bar_gets_an_accent_checked_answer_marked_right(game_env):
    module = game_env.module
    plot = next(
        p for p in game_env.state.plots
        if "en_to_fr_typed" in module.variants_for(p) and p.topic_type == "vocab"
    )
    for _ in range(40):
        question = module.open_practice(plot.plot_id, variant="en_to_fr_typed")
        answer = question["answer"]
        if any(ch in answer for ch in "éèêàçôûîï") and "/" not in answer:
            break
    else:
        return  # no accented answer rolled for this plot: nothing to prove here
    plain = answer
    for char, base in zip("éèêëàâîïôùûüç", "eeeeaaiiouuuc"):
        plain = plain.replace(char, base)
    box = game_env.elements["practice-answer-input"]
    box.value = ""
    for ch in answer:
        if ch in "éèêëàâîïôùûüç":
            _press(game_env, "accent-bar-practice", ch)
        else:
            box.value = box.value + ch
    assert box.value == answer
    assert module.submit_answer(box.value) is True
