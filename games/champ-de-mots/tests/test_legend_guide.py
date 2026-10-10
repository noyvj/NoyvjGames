"""LM-2: the "What the colours and icons mean" guide. The list is read from the tables the farm draws from,
samples use the farm's own CSS classes, and these tests walk the other way: everything the game can render
(plot classes, stage and kind tables, row parts, status readouts, question tags) has an entry."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
PC_HTML = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
CSS = "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in ("style.css", "visual-styles.css", "minigames.css"))
SOURCE = (GAME_DIR / "game.py").read_text(encoding="utf-8")
CONFIG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))

# Parts of a week row that are controls or layout, not indicators.
ROW_NOT_INDICATORS = {"row", "row-head", "row-plots", "row-proficiency-button secondary", "row-bonus-button secondary"}
# Status-area paragraphs that are not readouts of the farm's state.
READOUT_NOT_INDICATORS = {"pace-display"}


def _covered_classes(module):
    covered = set()
    for item in module.legend_indicators():
        covered.update(item["classes"])
    return covered


def _read_back(env):
    env.module.on_toggle_legend()
    return env.elements["legend-panel"]


def test_every_entry_is_complete_and_ids_are_unique(game_env):
    items = game_env.module.legend_indicators()
    assert len(items) >= 40
    assert len({item["id"] for item in items}) == len(items)
    groups = {key for key, _title in game_env.module.LEGEND_GROUPS}
    for item in items:
        assert item["group"] in groups
        assert item["name"].strip() and item["meaning"].strip()
        assert item["sample"] in {"plot", "row", "meter", "tag", "text"}
        if item["sample"] == "plot":
            assert item["icon"] and item["classes"][0] == "plot"
    for key in groups:
        assert any(item["group"] == key for item in items), key


def test_every_growth_stage_is_listed_from_the_stage_tables(game_env):
    module = game_env.module
    items = {item["id"]: item for item in module.legend_indicators()}
    for stage in module.STAGE_ORDER:
        entry = items[f"stage-{stage}"]
        assert entry["icon"] == module.STAGE_ICON[stage]
        assert f"plot--{stage}" in entry["classes"]
        assert entry["name"] == module.STAGE_LABEL[stage].split(" — ")[0]


def test_every_kind_of_plot_is_listed(game_env):
    module = game_env.module
    kinds = {plot.topic_type for plot in game_env.state.plots}
    assert kinds <= set(module.FARM_TYPE_ORDER)
    covered = _covered_classes(module)
    for kind in kinds:
        assert f"plot--type-{kind}" in covered
    names = {item["name"] for item in module.legend_indicators()}
    for kind in module.FARM_TYPE_ORDER:
        assert module.FARM_FILTERS[kind] in names


def test_every_class_a_plot_can_be_given_has_an_entry(game_env):
    module, state = game_env.module, game_env.state
    covered = _covered_classes(module)
    seen = set()
    sample = state.plots[0]
    for plot in [sample] + [state.row_plots(seq)[0] for seq in (1, 5, 12, 20)]:
        for stage in module.STAGE_ORDER:
            for weeds in (False, True):
                for due in (False, True):
                    plot.stage, plot.in_weeds = stage, weeds
                    plot.next_due = state.current_day - 1 if due else state.current_day + 9
                    plot.last_reviewed = None if stage == module.STAGE_SEED else 0
                    plot.fail_run = module.LEECH_THRESHOLD
                    seen.update(module._plot_classes(plot).split())
    module.golden_plot.update({"plot_id": sample.plot_id, "claimed": False})
    sample.stage, sample.in_weeds = module.STAGE_SEED, False
    seen.update(module._plot_classes(sample).split())
    module.minigames.amis_for_plot = lambda plot: {"means": ["x"]}
    seen.update(module._plot_classes(sample).split())
    # a locked week, as the farm gives it before earlier weeks have sprouted
    locked = state.row_plots(13)[0]
    state.is_row_unlocked = lambda sequence: False
    seen.update(module._plot_classes(locked).split())
    for expected in ("plot--golden", "plot--leech", "plot--amis", "plot--locked", "plot--weeds", "plot--due", "plot--wilting"):
        assert expected in seen, expected
    assert seen - {"plot"} <= covered, seen - covered


def test_every_plot_rule_in_the_stylesheets_has_an_entry(game_env):
    covered = _covered_classes(game_env.module)
    in_css = {f"plot--{name}" for name in re.findall(r"\.plot--([a-z][a-z-]*)", CSS)}
    assert in_css, "no .plot-- rules found"
    # a rule that only restyles an existing mark when combined with another is still that mark
    assert in_css <= covered, in_css - covered


def test_every_part_of_a_week_row_has_an_entry_or_is_a_control(game_env):
    covered = _covered_classes(game_env.module)
    body = SOURCE[SOURCE.index("def build_farm():"):SOURCE.index("def render_legend():")]
    made = set(re.findall(r'\.className = "([^"]+)"', body))
    assert {"row-progress", "row-due", "row-lock", "row-perfect-badge", "row-label", "row-chapter"} <= made
    for name in made - ROW_NOT_INDICATORS:
        parts = set(name.split())
        assert parts & covered, name
    assert "row--locked" in covered


def test_every_readout_in_the_status_area_has_an_entry(game_env):
    block = HTML[HTML.index('id="status"'):HTML.index('id="water-options-panel"')]
    ids = set(re.findall(r'id="([a-z-]+-display)"', block))
    assert {"day-display", "due-display", "combo-display", "coins-display", "stage-summary-display"} <= ids
    elements = set()
    for item in game_env.module.legend_indicators():
        elements.update(item["elements"])
    assert ids - READOUT_NOT_INDICATORS <= elements, ids - READOUT_NOT_INDICATORS - elements
    assert "automated-meter" in elements


def test_every_question_tag_text_has_an_entry(game_env):
    module = game_env.module
    names = {item["name"] for item in module.legend_indicators() if item["sample"] == "tag"}
    for _kind, text, _tip in module.GROWTH_INFO.values():
        assert text in names
    kinds = {item["growth"] for item in module.legend_indicators() if item["sample"] == "tag"}
    assert "none" in kinds and "apply" in kinds


def test_the_words_come_from_the_games_own_tables(game_env):
    module = game_env.module
    items = {item["id"]: item for item in module.legend_indicators()}
    assert module.WILTING_LEGEND.partition(" — ")[2].split(",")[0].lower() in items["mark-wilting"]["meaning"].lower()
    assert module.WEEDS_LEGEND.partition(" — ")[2].split(",")[0].lower() in items["mark-weeds"]["meaning"].lower()
    assert str(module.GOLDEN_POINTS) in items["mark-golden"]["meaning"]
    assert str(module.LEECH_THRESHOLD) in items["mark-leech"]["meaning"]
    assert items["row-due"]["text"] == module.ROW_DUE_NOTE.format(count=5)
    assert items["row-lock"]["text"].startswith(module.LOCK_NOTE.split("{")[0].strip())
    assert items["row-chapter"]["text"] == game_env.state.rows[0].chapter_label


def test_the_panel_opens_and_closes_from_both_buttons(game_env):
    elements = game_env.elements
    assert elements["legend-panel"].hidden is False or elements["legend-panel"].hidden is True
    game_env.module.render()
    assert elements["legend-panel"].hidden is True
    elements["legend-toggle-button"].dispatch("click", None)
    assert elements["legend-panel"].hidden is False
    assert elements["legend-toggle-button"].innerText.startswith("Hide")
    elements["farm-legend-button"].dispatch("click", None)
    assert elements["legend-panel"].hidden is True
    elements["farm-legend-button"].dispatch("click", None)
    assert elements["legend-panel"].hidden is False


def test_opening_draws_one_sample_per_entry_with_the_farms_own_classes(game_env):
    module = game_env.module
    panel = _read_back(game_env)
    items = module.legend_indicators()
    for item in items:
        row = game_env.elements[f"legend-item-{item['id']}"]
        assert row.parent if hasattr(row, "parent") else True
        classes = {c for el in row.descendants() for c in el.className.split()}
        if item["sample"] in ("plot", "row", "meter", "tag"):
            assert set(item["classes"]) <= classes | {"row--locked"}, item["id"]
    plots = [e for e in panel.descendants() if "plot" in e.className.split()]
    assert len(plots) == sum(1 for item in items if item["sample"] == "plot")
    assert [e.innerText for e in panel.descendants() if e.className == "legend-name"] == [item["name"] for item in items]
    # the drawn sample is decoration: the words next to it carry the meaning
    for el in panel.descendants():
        if el.className == "legend-sample":
            assert el.getAttribute("aria-hidden") == "true"


def test_the_guide_changes_no_plot_and_no_save(game_env):
    module = game_env.module
    before = module.get_state()
    module.on_toggle_legend()
    module.render()
    module.on_toggle_legend()
    assert module.get_state() == before


def test_markup_and_desktop_config_wire_the_guide(game_env):
    for page in (HTML, PC_HTML):
        for element_id in ("legend-panel", "legend-toggle-button", "farm-legend-button", "semester-summary"):
            assert f'id="{element_id}"' in page, element_id
    assert ["legend-panel", "legend-toggle-button", "What the colours and icons mean"] in CONFIG["windows"]
    help_group = next(g for g in CONFIG["toolbar"]["menu"] if g["heading"] == "Help")
    assert "legend-toggle-button" in help_group["ids"]
    assert "#semester-summary" in CONFIG["zones"]["stage"]
    assert 'toggle: "legend-toggle-button", panel: "legend-panel"' in HTML
    assert "Colours and icons" in HTML and "Colours and icons" in (GAME_DIR / "pc.js").read_text(encoding="utf-8")


def test_the_new_css_has_no_motion():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    block = css[css.index("LM-2: the colours-and-icons guide"):]
    assert "transition" not in block and "animation" not in block
