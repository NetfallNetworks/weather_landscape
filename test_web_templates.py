"""
Template integrity tests for the web worker (pixel-zine redesign).

Runtime-independent: the web worker imports the workerd/pyodide runtime
(`from js import ...`), so it can't be imported in plain CPython. These tests
instead exercise the two things that actually break in production without it:

  1. The string.Template substitution path for the rendered templates
     (forecasts.html, admin.html) -- any LONE '$' that isn't a real placeholder
     raises at render time. This is the bug class from PR #27 (admin JS regex).
  2. Structural invariants every redesigned page must keep: the glyph-sprite
     sentinel, the shared stylesheet + font links, sprite-only glyph use, and
     -- for the landing page -- no inline <style> (design system is external).

Run standalone:  python test_web_templates.py
Or via pytest:   pytest test_web_templates.py
"""

import os
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "workers", "web", "src", "assets")
TEMPLATES = os.path.join(ASSETS, "templates")

# Rendered templates -> the exact context render_template() supplies in web.py.
RENDERED = {
    "forecasts.html": {"zip_links": "<div>x</div>", "zip_count": 1},
    "admin.html": {"zip_table_rows": "<tr><td>x</td></tr>"},
}
# Static templates served via load_template() (no substitution).
STATIC = ["landing.html", "guide.html", "styleguide.html"]
ALL_TEMPLATES = list(RENDERED.keys()) + STATIC

FONTS_HREF = "fonts.googleapis.com/css2?family=Press+Start+2P"
SPRITE = os.path.join(ASSETS, "glyphs.svg")
GLYPH_IDS = [
    "glyph-brand", "glyph-house", "glyph-hill",
    "glyph-tree", "glyph-cloud", "glyph-sun", "glyph-flower",
]


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_rendered_templates_substitute_without_error():
    """forecasts/admin must render via string.Template with no stray '$'."""
    for name, ctx in RENDERED.items():
        text = _read(os.path.join(TEMPLATES, name))
        # Raises ValueError on a lone '$' / KeyError on an unknown placeholder.
        Template(text).substitute(**ctx)


def test_rendered_templates_have_their_placeholders():
    for name, ctx in RENDERED.items():
        text = _read(os.path.join(TEMPLATES, name))
        for key in ctx:
            assert "$" + key in text, f"{name} lost placeholder ${key}"


def test_every_page_has_glyph_sentinel_first_in_body():
    for name in ALL_TEMPLATES:
        text = _read(os.path.join(TEMPLATES, name))
        assert "<!--GLYPHS-->" in text, f"{name} missing <!--GLYPHS--> sentinel"
        body_idx = text.index("<body")
        body_open_end = text.index(">", body_idx)
        between = text[body_open_end + 1:text.index("<!--GLYPHS-->")]
        assert between.strip() == "", f"{name}: <!--GLYPHS--> not first in <body>"


def test_every_page_links_fonts_and_stylesheet():
    for name in ALL_TEMPLATES:
        text = _read(os.path.join(TEMPLATES, name))
        assert FONTS_HREF in text, f"{name} missing pixel-font link"
        assert "/assets/styles.css" in text, f"{name} missing shared stylesheet"


def test_glyphs_are_referenced_only_via_sprite():
    """Templates use <use href="#glyph-..."> and never paste raw <rect> data."""
    for name in ALL_TEMPLATES:
        text = _read(os.path.join(TEMPLATES, name))
        if 'class="pglyph"' in text or "brand-mark" in text:
            assert 'href="#glyph-' in text, f"{name} should reference glyph sprite"
        assert "<rect" not in text, f"{name} should not inline <rect> glyph data"


def test_landing_has_no_inline_style_block():
    text = _read(os.path.join(TEMPLATES, "landing.html"))
    assert "<style" not in text, "landing.html must use external styles.css only"


def test_sprite_defines_all_symbols_and_has_no_dollar():
    text = _read(SPRITE)
    for gid in GLYPH_IDS:
        assert f'id="{gid}"' in text, f"glyphs.svg missing {gid}"
    assert "$" not in text, "sprite must contain no '$' (injected before substitution)"
    assert "<rect" in text, "sprite should contain rect data"


def test_admin_preserves_doubled_dollar_regex():
    """The location-code regex must keep '$$' so it survives substitution -> '$'."""
    text = _read(os.path.join(TEMPLATES, "admin.html"))
    assert "$$/" in text, "admin.html lost the doubled '$$' in its validation regex"
    rendered = Template(text).substitute(zip_table_rows="x")
    assert "})$/" in rendered, "rendered admin regex should collapse '$$' to a single '$'"


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:
            failures += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)
