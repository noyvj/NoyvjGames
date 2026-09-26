"""The tracker loads the shared theme switch and ships a real light palette."""

import pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
HTML = (HERE / "index.html").read_text()
CSS = (HERE / "style.css").read_text()


def test_page_loads_the_shared_theme_script_with_a_floating_toggle():
    assert '<script src="../shared/theme.js" data-floating-toggle></script>' in HTML
    assert (HERE.parent / "shared" / "theme.js").exists()


def test_shared_light_widget_styles_are_linked():
    assert 'href="../shared/theme-light-games.css"' in HTML


def test_theme_script_loads_before_the_page_body_so_there_is_no_flash():
    assert HTML.index("theme.js") < HTML.index("<body>")


def test_light_palette_covers_the_main_surfaces():
    for selector in ('html[data-theme="light"] body', 'html[data-theme="light"] section',
                     'html[data-theme="light"] button.secondary', 'html[data-theme="light"] input[type="number"]',
                     'html[data-theme="light"] th,'):
        assert selector in CSS, selector


def test_light_body_text_is_dark_on_a_light_background():
    rule = CSS[CSS.index('html[data-theme="light"] body'):].split("}")[0]
    assert "background: #f1f3f8" in rule and "color: #1b2033" in rule


def test_the_dark_theme_rules_are_untouched():
    assert "background: #111318" in CSS and "color: #e8eaf0" in CSS


def test_every_light_rule_is_scoped_to_the_light_theme():
    after = CSS[CSS.index("/* Light theme"):]
    for block in after.split("}"):
        selectors = block.split("{")[0].strip()
        if not selectors or selectors.startswith("/*"):
            continue
        assert 'data-theme="light"' in selectors or selectors.startswith("#theme-toggle-floating"), selectors[:60]
