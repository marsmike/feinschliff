"""Integration tests for Layer 1 emitter restraint behaviors.

Each test renders one or two DSL primitives through the emitter, opens
the resulting Presentation, and asserts that the run text / properties
match the restraint defaults.
"""
from __future__ import annotations

from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.pptx_emit import build_presentation
from feinschmiede.dsl.tokens import Tokens


def _minimal_tokens(
    *,
    locale: str = "en",
    extra: dict | None = None,
) -> Tokens:
    """A locally-minimal Tokens bundle for emitter tests.

    Uses px-suffixed font sizes + array-shape font families to match the
    on-disk schema. Extra brand fields can be passed via `extra`.
    """
    raw: dict = {
        "color": {
            "ink": "#111111",
            "accent": "#FF5722",
            "paper": "#FFFFFF",
            "fog": "#CCCCCC",
            "graphite": "#444444",
            "steel": "#666666",
            "paper-2": "#F5F5F5",
            "accent-hover": "#FF8A65",
        },
        "font-family": {
            "display": ["Inter"],
            "body": ["Inter"],
            "mono": ["Consolas"],
        },
        "font-size": {
            "slide-title": "56px", "title-l": "80px", "sub": "32px", "huge": "96px",
            "display": "160px", "display-xl": "200px", "bignum": "240px",
            "col-num": "20px", "col-title": "24px", "col-title-q": "20px",
            "col-body": "18px",
            "body": "18px", "eyebrow": "14px", "footer": "14px", "pgmeta": "14px",
            "kpi-value": "80px", "kpi-unit": "32px", "kpi-key": "14px",
            "kpi-delta": "14px",
            "agenda-num": "16px", "agenda-t": "24px", "agenda-d": "18px",
            "quote": "56px", "quote-attr": "14px",
            "btn": "22px", "chip": "14px",
            "act-title": "40px", "act-kicker": "14px", "tracker": "14px",
            "h-idx": "14px", "h-hd": "24px", "h-li": "18px", "lede": "32px",
        },
        "font-weight": {"light": 300, "regular": 400, "medium": 500,
                        "semibold": 600, "bold": 700, "black": 900},
        "locale": locale,
    }
    if extra:
        raw.update(extra)
    return Tokens.from_dict(raw, brand_name="test")


def _emit_one_slide(dsl_source: str, tokens: Tokens | None = None):
    tokens = tokens or _minimal_tokens()
    nodes, _ = parse_lines(dsl_source)
    return build_presentation(nodes, tokens)


# ---------------------------------------------------------------------------
# Task 3 — normalize_text wiring
# ---------------------------------------------------------------------------

def test_normalize_smart_quotes_in_emitted_text():
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "He said \\"hi\\" to me."'
    )
    prs = _emit_one_slide(dsl, _minimal_tokens(locale="en"))
    txt = prs.slides[0].shapes[0].text_frame.text
    assert "“hi”" in txt
    assert '"hi"' not in txt


def test_normalize_em_dash_in_emitted_text():
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "before--after"'
    )
    prs = _emit_one_slide(dsl)
    txt = prs.slides[0].shapes[0].text_frame.text
    assert "before—after" in txt


def test_normalize_locale_de_quotes():
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "Er sagte \\"hallo\\" zu mir."'
    )
    prs = _emit_one_slide(dsl, _minimal_tokens(locale="de"))
    txt = prs.slides[0].shapes[0].text_frame.text
    assert "„hallo“" in txt


# ---------------------------------------------------------------------------
# Task 4 — tabular-numeral font switch on numeric runs
# ---------------------------------------------------------------------------

def test_tnum_font_switch_when_token_set_and_content_numeric():
    """Numeric runs should switch to tokens.tnum_font when configured."""
    tokens = _minimal_tokens(extra={"typography": {"tnum_font": "Inter Tabular"}})
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:kpi-value "42.7"'
    )
    prs = _emit_one_slide(dsl, tokens)
    run = prs.slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
    assert run.font.name == "Inter Tabular"


def test_tnum_skipped_when_content_not_numeric():
    tokens = _minimal_tokens(extra={"typography": {"tnum_font": "Inter Tabular"}})
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "Hello"'
    )
    prs = _emit_one_slide(dsl, tokens)
    run = prs.slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
    # Body weight 400 → "Inter" (no suffix), NOT "Inter Tabular".
    assert run.font.name == "Inter"


def test_tnum_skipped_when_no_tnum_font_set():
    """No tnum_font token → numeric content uses the default face unchanged."""
    tokens = _minimal_tokens()  # no tnum_font
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:kpi-value "42.7"'
    )
    prs = _emit_one_slide(dsl, tokens)
    run = prs.slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
    # kpi-value style: display weight=light → "Inter Light".
    assert run.font.name == "Inter Light"


# ---------------------------------------------------------------------------
# Task 5 — display tracking curve as brand-level fallback
# ---------------------------------------------------------------------------

def _spc_for(prs) -> int | None:
    """Pull the spc attribute off the first run's rPr, or None if absent."""
    run = prs.slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
    rpr = run._r.get_or_add_rPr()
    s = rpr.get("spc")
    return int(s) if s is not None else None


def test_display_tracking_curve_applies_when_style_has_no_letter_spacing():
    """style:huge has no letter_spacing in STYLE_BUNDLES. With a curve set,
    a huge run (96px = 48pt) should pick up tracking via the curve."""
    tokens = _minimal_tokens(extra={
        "typography": {
            "display_tracking_curve": {"32": -0.005, "56": -0.015, "96": -0.025}
        }
    })
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:huge "Big"'
    )
    prs = _emit_one_slide(dsl, tokens)
    spc = _spc_for(prs)
    assert spc is not None, "tracking curve should set spc for huge size"
    # 48pt picks key=32 → -0.005. spc = -0.005 * 48 * 100 = -24.
    assert -50 < spc < 0


def test_display_tracking_curve_no_change_when_style_already_has_letter_spacing():
    """style:title declares letter_spacing -0.015. Curve must not override
    an explicit per-style letter_spacing (the bundle wins)."""
    tokens = _minimal_tokens(extra={
        "typography": {
            "display_tracking_curve": {"32": -0.005, "56": -0.001, "96": -0.001}
        }
    })
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:title "Title"'
    )
    prs = _emit_one_slide(dsl, tokens)
    spc = _spc_for(prs)
    # style:title letter_spacing -0.015 at 28pt → spc = -0.015 * 28 * 100 = -42.
    assert spc == -42


def test_display_tracking_curve_skipped_below_threshold():
    """Body text (18px = 9pt) is below the curve's lowest key (32) → no spc."""
    tokens = _minimal_tokens(extra={
        "typography": {
            "display_tracking_curve": {"32": -0.005, "56": -0.015}
        }
    })
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "body"'
    )
    prs = _emit_one_slide(dsl, tokens)
    assert _spc_for(prs) is None


# ---------------------------------------------------------------------------
# Task 6 — hanging punctuation
# ---------------------------------------------------------------------------

def test_hanging_punctuation_shifts_textbox_left():
    """Runs starting with a bullet should have their textbox shifted left
    by the glyph's approximate side-bearing so the bullet hangs into the
    margin."""
    dsl_with_bullet = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "• First item"'
    )
    dsl_plain = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "First item"'
    )
    prs_bullet = _emit_one_slide(dsl_with_bullet)
    prs_plain = _emit_one_slide(dsl_plain)
    left_bullet = prs_bullet.slides[0].shapes[0].left
    left_plain = prs_plain.slides[0].shapes[0].left
    assert left_bullet < left_plain, (
        f"bullet textbox should hang into margin: left={left_bullet}, plain={left_plain}"
    )


def test_hanging_punctuation_no_offset_when_no_hang_glyph():
    """A plain word run should not be offset — x=100 design-px maps to
    635000 EMU."""
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "Word"'
    )
    prs = _emit_one_slide(dsl)
    shape = prs.slides[0].shapes[0]
    assert shape.left == 635000


def test_hanging_punctuation_em_dash_at_start():
    """An em-dash leading the run also hangs."""
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "— attribution"'
    )
    prs = _emit_one_slide(dsl)
    assert prs.slides[0].shapes[0].left < 635000


# ---------------------------------------------------------------------------
# Task 8 — 3-channel hierarchy stepping (indent:1, indent:2, ...)
# ---------------------------------------------------------------------------

def test_hierarchy_stepping_level_1_drops_size_and_steps_color():
    """style:title indent:1 — size ×0.85, color steps ink→graphite."""
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:title indent:1 "Sub-title"'
    )
    prs = _emit_one_slide(dsl)
    run = prs.slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
    # title: 56 design-px = 28pt; × 0.85 = 23.8 → round to 0.5 → 24.0pt.
    assert 23.0 <= run.font.size.pt <= 25.0
    # title color was ink (#111111); steps once to graphite (#444444).
    assert str(run.font.color.rgb).lower() == "444444"


def test_hierarchy_stepping_level_0_unchanged():
    """No indent (or indent:0) preserves the original style."""
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:title "Title"'
    )
    prs = _emit_one_slide(dsl)
    run = prs.slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
    assert run.font.size.pt == 28
    assert str(run.font.color.rgb).lower() == "111111"


def test_hierarchy_stepping_level_2_walks_color_to_fog():
    """Two indent levels walk the color from ink through graphite to fog."""
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:title indent:2 "deep sub"'
    )
    prs = _emit_one_slide(dsl)
    run = prs.slides[0].shapes[0].text_frame.paragraphs[0].runs[0]
    # 28pt × 0.85 × 0.85 ≈ 20.23 → round 0.5 → 20.0pt.
    assert 19.0 <= run.font.size.pt <= 21.0
    # ink → graphite → fog (#CCCCCC).
    assert str(run.font.color.rgb).lower() == "cccccc"


# ---------------------------------------------------------------------------
# Task 9 — picture treatment (desat / duotone)
# ---------------------------------------------------------------------------

def test_picture_desat_token_desaturates_blob(tmp_path):
    """When picture_treatment is desat(0.4), the emitted picture pixel data
    is desaturated 40% — pure-red (255,0,0) shifts toward gray."""
    import io
    from PIL import Image

    img = Image.new("RGB", (200, 200), color=(255, 0, 0))
    img_path = tmp_path / "red.png"
    img.save(img_path)

    tokens = _minimal_tokens(extra={"picture_treatment": "desat(0.4)"})
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        f'picture 100,100 200x200 path:{img_path}'
    )
    prs = _emit_one_slide(dsl, tokens)
    pic = prs.slides[0].shapes[0]
    blob = pic.image.blob
    img_out = Image.open(io.BytesIO(blob)).convert("RGB")
    r, g, b = img_out.getpixel((100, 100))
    assert g > 0 or b > 0, (
        f"expected desaturated pixel, got pure ({r}, {g}, {b})"
    )


def test_picture_desat_preserves_alpha_on_rgba_source(tmp_path):
    """Regression: desat() must not flatten an RGBA source onto opaque black.

    Before the fix, _apply_picture_treatment converted RGBA→RGB unconditionally,
    so transparent pixels became opaque black — the FEINSCHLIFF gem chip
    rendered as a featureless dark square across every slide.
    """
    import io
    from PIL import Image

    # Diamond on transparent background: center red opaque, corners transparent.
    img = Image.new("RGBA", (200, 200), color=(0, 0, 0, 0))
    for x in range(60, 140):
        for y in range(60, 140):
            img.putpixel((x, y), (255, 0, 0, 255))
    img_path = tmp_path / "diamond.png"
    img.save(img_path)

    tokens = _minimal_tokens(extra={"picture_treatment": "desat(0.4)"})
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        f'picture 100,100 200x200 path:{img_path}'
    )
    prs = _emit_one_slide(dsl, tokens)
    pic = prs.slides[0].shapes[0]
    img_out = Image.open(io.BytesIO(pic.image.blob))
    assert img_out.mode == "RGBA", (
        f"alpha channel dropped: mode={img_out.mode} — chip renders as black square"
    )
    # Corner pixel was transparent in source; must stay transparent after desat.
    rgba = img_out.convert("RGBA")
    _, _, _, a = rgba.getpixel((5, 5))
    assert a == 0, f"transparent corner became opaque (alpha={a})"


def test_picture_treatment_none_passes_through(tmp_path):
    """Default picture_treatment 'none' must leave the image pixel-identical."""
    import io
    from PIL import Image

    img = Image.new("RGB", (200, 200), color=(255, 0, 0))
    img_path = tmp_path / "red.png"
    img.save(img_path)

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        f'picture 100,100 200x200 path:{img_path}'
    )
    prs = _emit_one_slide(dsl, _minimal_tokens())
    pic = prs.slides[0].shapes[0]
    img_out = Image.open(io.BytesIO(pic.image.blob)).convert("RGB")
    assert img_out.getpixel((100, 100)) == (255, 0, 0)


# ---------------------------------------------------------------------------
# Task 10 — sanitize_chrome (post-build XML pass)
# ---------------------------------------------------------------------------

_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def test_sanitize_chrome_removes_effect_lst():
    from lxml import etree
    from feinschliff.dsl.pptx_emit import sanitize_chrome

    xml = b"""<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:cSld><p:spTree>
        <p:sp>
          <p:spPr>
            <a:effectLst>
              <a:outerShdw blurRad="50800" dist="38100" dir="2700000"/>
            </a:effectLst>
          </p:spPr>
        </p:sp>
      </p:spTree></p:cSld>
    </p:sld>"""
    root = etree.fromstring(xml)
    sanitize_chrome(root)
    assert root.find(".//a:effectLst", _NS) is None


def test_sanitize_chrome_preserves_effect_when_allow():
    from lxml import etree
    from feinschliff.dsl.pptx_emit import sanitize_chrome
    # The marker uses the namespaced attribute the emitter writes
    # when a primitive opts in via effect:allow.
    xml = b"""<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                    xmlns:fs="urn:feinschliff:emit">
      <p:cSld><p:spTree>
        <p:sp fs:effect-allow="1">
          <p:spPr>
            <a:effectLst>
              <a:outerShdw blurRad="50800"/>
            </a:effectLst>
          </p:spPr>
        </p:sp>
      </p:spTree></p:cSld>
    </p:sld>"""
    root = etree.fromstring(xml)
    sanitize_chrome(root)
    assert root.find(".//a:effectLst", _NS) is not None


def test_effect_allow_marker_is_namespaced():
    """The opt-in marker must be XML-namespaced — bare attributes on
    <p:sp> are schema-invalid OOXML that strict validators flag."""
    from lxml import etree

    _FS_NS = "urn:feinschliff:emit"
    dsl = (
        "canvas 1920x1080\n"
        "theme test\n"
        "rect 100,100 400x200 "
        "gradient:angle=90deg;0.00=accent;1.00=paper"
    )
    prs = _emit_one_slide(dsl)
    slide_xml = prs.slides[0]._element
    raw = etree.tostring(slide_xml)

    # The bare (non-namespaced) attribute must NOT appear.
    assert b' effect-allow=' not in raw, (
        "bare 'effect-allow' attribute found — must use namespaced form"
    )
    # The namespaced marker MUST appear in Clark-notation form.
    sp_elements = slide_xml.iter(f"{{{_NS['p']}}}sp")
    found_ns_attr = any(
        sp.get(f"{{{_FS_NS}}}effect-allow") == "1"
        for sp in sp_elements
    )
    assert found_ns_attr, (
        "{urn:feinschliff:emit}effect-allow='1' not found on any <p:sp>"
    )


def test_sanitize_chrome_legacy_bare_attr_honored():
    """Old decks with bare effect-allow='1' must still survive sanitize_chrome
    with their effectLst intact (backward-compat read path)."""
    from lxml import etree
    from feinschliff.dsl.pptx_emit import sanitize_chrome

    xml = b"""<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:cSld><p:spTree>
        <p:sp effect-allow="1">
          <p:spPr>
            <a:effectLst>
              <a:outerShdw blurRad="50800"/>
            </a:effectLst>
          </p:spPr>
        </p:sp>
      </p:spTree></p:cSld>
    </p:sld>"""
    root = etree.fromstring(xml)
    sanitize_chrome(root)
    assert root.find(".//a:effectLst", _NS) is not None, (
        "legacy bare effect-allow='1' must preserve effectLst (backward compat)"
    )


def test_sanitize_chrome_legacy_bare_attr_honored_grad_fill():
    """Old decks with bare effect-allow='1' must survive sanitize_chrome
    with their gradFill intact (backward-compat read path)."""
    from lxml import etree
    from feinschliff.dsl.pptx_emit import sanitize_chrome

    xml = b"""<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:cSld><p:spTree>
        <p:sp effect-allow="1">
          <p:spPr>
            <a:gradFill>
              <a:gsLst>
                <a:gs pos="0"><a:srgbClr val="FF0000"/></a:gs>
                <a:gs pos="100000"><a:srgbClr val="0000FF"/></a:gs>
              </a:gsLst>
            </a:gradFill>
          </p:spPr>
        </p:sp>
      </p:spTree></p:cSld>
    </p:sld>"""
    root = etree.fromstring(xml)
    sanitize_chrome(root)
    assert root.find(".//a:gradFill", _NS) is not None, (
        "legacy bare effect-allow='1' must preserve gradFill (backward compat)"
    )


def test_sanitize_chrome_replaces_grad_fill_with_solid():
    from lxml import etree
    from feinschliff.dsl.pptx_emit import sanitize_chrome
    xml = b"""<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:cSld><p:spTree>
        <p:sp>
          <p:spPr>
            <a:gradFill>
              <a:gsLst>
                <a:gs pos="0"><a:srgbClr val="FF0000"/></a:gs>
                <a:gs pos="100000"><a:srgbClr val="0000FF"/></a:gs>
              </a:gsLst>
            </a:gradFill>
          </p:spPr>
        </p:sp>
      </p:spTree></p:cSld>
    </p:sld>"""
    root = etree.fromstring(xml)
    sanitize_chrome(root)
    assert root.find(".//a:gradFill", _NS) is None
    solid = root.find(".//a:solidFill", _NS)
    assert solid is not None
    rgb = solid.find("a:srgbClr", _NS)
    assert rgb is not None
    assert rgb.get("val") == "FF0000"


def test_sanitize_chrome_clamps_fat_outlines():
    """Outline width > 12700 EMU (>1pt) clamps to 6350 (0.5pt hairline)."""
    from lxml import etree
    from feinschliff.dsl.pptx_emit import sanitize_chrome
    xml = b"""<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:cSld><p:spTree>
        <p:sp>
          <p:spPr>
            <a:ln w="38100"/>
          </p:spPr>
        </p:sp>
      </p:spTree></p:cSld>
    </p:sld>"""
    root = etree.fromstring(xml)
    sanitize_chrome(root)
    ln = root.find(".//a:ln", _NS)
    assert int(ln.get("w")) == 6350


def test_sanitize_chrome_idempotent():
    from lxml import etree
    from feinschliff.dsl.pptx_emit import sanitize_chrome
    xml = b"""<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:cSld><p:spTree>
        <p:sp><p:spPr><a:ln w="20000"/><a:effectLst><a:outerShdw/></a:effectLst></p:spPr></p:sp>
      </p:spTree></p:cSld>
    </p:sld>"""
    root_once = etree.fromstring(xml)
    sanitize_chrome(root_once)
    once = etree.tostring(root_once)
    sanitize_chrome(root_once)
    twice = etree.tostring(root_once)
    assert once == twice


def test_sanitize_chrome_runs_on_build_presentation():
    """build_presentation should call sanitize_chrome so emitted decks ship
    without drop shadows / gradients / fat outlines on emitted shapes."""
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'text 100,100 style:body "Hello"'
    )
    prs = _emit_one_slide(dsl)
    # Sanitation is scoped to <p:spTree> — master/layout inheritance is
    # preserved. The emitted shape tree should be free of effectLst.
    for slide in prs.slides:
        sptree = slide._element.find(f"{{{_NS['p']}}}cSld/{{{_NS['p']}}}spTree")
        assert sptree is not None
        assert sptree.find(f".//{{{_NS['a']}}}effectLst") is None
