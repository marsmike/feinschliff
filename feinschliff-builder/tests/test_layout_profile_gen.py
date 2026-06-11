"""Layout-picker frontmatter generation for decompiled brand-pack layouts.

Decompiled layouts carry no `---` frontmatter, so the /deck picker
(`feinschliff.layout_profile.build_profile_table(strict=False)`) silently
drops them. `layout_profile_gen` classifies a slotified layout from its DSL
text alone and emits a fence that `parse_profile` accepts — these tests pin
the classification heuristics, slot-role assignment, fence idempotency, and
the deck-map reduction.
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from feinschliff.dsl.parser import parse_lines, split_frontmatter
from feinschliff.layout_profile import parse_profile
from feinschliff_builder.decompile.layout_profile_gen import (
    apply_profile,
    classify_layout,
    derive_deck_map,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_COVER = (REPO_ROOT.parent / "feinschliff-extra" / "brands" / "scientific"
              / "layouts" / "cover.slide.dsl")

HEADER = "# auto-derived from PPTX+SVG hybrid — review before use\ncanvas 1920x1080\ntheme test\n\n"


def slot(n: int, default: str, *, x=152, y=260, style="title-l", pt=60,
         maxw=1600, maxh=200) -> str:
    # Mirrors real slotified output: the inner quotes are backslash-escaped
    # in the FILE, e.g.  "{{ text_1 | default(\"Annual Review\") }}"
    return (f'text {x},{y} style:{style} color:black size:{pt}pt '
            f'maxwidth:{maxw} maxheight:{maxh} '
            f'"{{{{ text_{n} | default(\\"{default}\\") }}}}"\n')


def footer_slots(start: int) -> str:
    return (
        slot(start, "Annual Review", x=1307, y=991, style="body-sm", pt=12,
             maxw=231, maxh=29)
        + slot(start + 1, "7", x=1810, y=991, style="body-sm", pt=12,
               maxw=100, maxh=29)
    )


def native(xml: str, name: str = "shape1") -> str:
    b64 = base64.b64encode(xml.encode("utf-8")).decode("ascii")
    return f'native {name} b64:"{b64}"\n'


CHART_XML = ('<p:graphicFrame xmlns:p="p"><a:graphic>'
             '<c:chart r:id="rId2"/></a:graphic></p:graphicFrame>')
TABLE_XML = ('<p:graphicFrame xmlns:p="p"><a:graphic>'
             '<a:tbl><a:tr/></a:tbl></a:graphic></p:graphicFrame>')
SMARTART_XML = ('<p:graphicFrame xmlns:p="p"><a:graphic>'
                '<dgm:relIds r:dm="rId1"/></a:graphic></p:graphicFrame>')
ILLUSTRATION_XML = '<p:sp xmlns:p="p"><p:spPr><a:custGeom/></p:spPr></p:sp>'

FULL_BLEED_PICTURE = ('picture 0,0 1920x1080 '
                      'path:"{{ image | default(\\"decompile/x/image.png\\") }}" '
                      'cover:true\n')


def classify(dsl: str, *, name="some-layout", index=5, total=13, **kw) -> dict:
    return classify_layout(dsl, layout_name=name, slide_index=index,
                           total_slides=total, **kw)


# --- role heuristics ---------------------------------------------------------

def test_slide_one_is_title_primary_cover():
    dsl = HEADER + slot(1, "Annual Review") + slot(2, "Contoso Team", y=420, pt=24)
    p = classify(dsl, name="cover", index=1)
    assert p["role"] == "title-primary"
    assert p["family"] == "framing"
    assert p["variety_exempt"] is True
    assert p["ideal_count"] == [1, 2]


def test_agenda_by_title_default():
    dsl = (HEADER + slot(1, "Agenda", pt=40)
           + slot(2, "01. Intro\\n02. Results", y=500, style="body", pt=20, maxh=400)
           + footer_slots(3))
    p = classify(dsl, name="toc", index=2)
    assert p["role"] == "agenda"
    assert p["variety_exempt"] is True


def test_agenda_by_layout_name():
    dsl = HEADER + slot(1, "Was uns erwartet", pt=40)
    assert classify(dsl, name="inhalt", index=2)["role"] == "agenda"


def test_quote_by_lone_quote_mark_default():
    dsl = (HEADER + slot(1, "“", pt=200, y=154)
           + slot(2, "Contoso was great to work with.", y=400, style="sub", pt=28)
           + footer_slots(3))
    p = classify(dsl, name="quote", index=7)
    assert p["role"] == "quote"
    assert p["family"] == "voice"
    assert p["ideal_count"] == [1, 2]


def test_closer_by_last_slide_and_by_title():
    dsl = HEADER + slot(1, "THANK YOU", pt=54, y=498) \
        + slot(2, "hello@adatum.com", y=952, style="body", pt=24)
    by_index = classify(dsl, name="end", index=13, total=13)
    assert by_index["role"] == "closer"
    assert by_index["variety_exempt"] is True
    by_title = classify(dsl, name="end", index=9, total=13)
    assert by_title["role"] == "closer"


def test_native_chart_is_data_comparison():
    dsl = HEADER + native(CHART_XML, "graphic1") + slot(1, "Growth by sector", pt=40)
    p = classify(dsl, name="growth-chart")
    assert p["role"] == "data-comparison"
    assert p["data_band"] == "chart"
    assert p["comparison"] is True
    assert p["family"] == "comparison"


def test_native_table_is_reference():
    dsl = HEADER + native(TABLE_XML, "graphic1") + slot(1, "Growth by sector", pt=40)
    p = classify(dsl, name="growth-table")
    assert p["role"] == "reference"
    assert p["data_band"] == "table"
    assert p["comparison"] is False


def test_native_smartart_is_concept_diagram():
    dsl = HEADER + native(SMARTART_XML, "graphic1") + slot(1, "Our process", pt=40)
    p = classify(dsl, name="growth-strategy")
    assert p["role"] == "concept-diagram"
    assert p["family"] == "process"
    assert p["data_band"] == "none"


def test_native_illustration_divider_is_chapter_opener():
    dsl = (HEADER + native(ILLUSTRATION_XML)
           + slot(1, "The Power of Communication", pt=36)
           + footer_slots(2))  # footer/page-number don't count as visible text
    p = classify(dsl, name="section-intro", index=4)
    assert p["role"] == "chapter-opener"
    assert p["fixed_chrome"] is True
    assert p["when_not_to_use"] == [
        "role=content-columns", "role=data-quantity", "role=data-comparison",
    ]
    assert p["ideal_count"] == [1, 2]
    assert "illustration" in p["chrome_note"]


def test_undecodable_native_defaults_to_illustration():
    dsl = (HEADER + 'native shape1 xml_file:"native/missing.xml"\n'
           + slot(1, "Divider", pt=36))
    p = classify(dsl, name="divider")  # no asset_root → cannot decode
    assert p["role"] == "chapter-opener"


def test_full_bleed_image_is_title_with_visual():
    dsl = HEADER + FULL_BLEED_PICTURE + slot(1, "Last year", pt=54)
    p = classify(dsl, name="last-year")
    assert p["role"] == "title-with-visual"
    assert p["family"] == "image-driven"
    assert "image" in p["image_queries"]


def test_numeric_short_body_slots_are_data_quantity():
    dsl = HEADER + slot(1, "Key figures", pt=40)
    for i, val in enumerate(("45%", "+30", "€2,4", "1.2"), start=2):
        dsl += slot(i, val, x=100 + 400 * i, y=600, style="body", pt=40,
                    maxw=380, maxh=200)
    p = classify(dsl, name="metrics")
    assert p["role"] == "data-quantity"
    assert p["data_band"] == "kpi"
    assert p["ideal_count"] == [4, 4]


def test_many_body_slots_fall_back_to_content_columns():
    dsl = HEADER + slot(1, "Summary", pt=40)
    for i in range(2, 5):
        dsl += slot(i, "Some longer prose paragraph here", x=100 + 500 * i,
                    y=500, style="body", pt=18, maxw=480, maxh=400)
    p = classify(dsl, name="summary")
    assert p["role"] == "content-columns"
    assert p["family"] == "organizational"
    assert p["ideal_count"] == [3, 3]


# --- slot roles ---------------------------------------------------------------

def test_slot_roles_and_char_capacity():
    dsl = (HEADER + slot(1, "Goals for Q1", pt=60, y=260)
           + slot(2, "Business priorities", y=600, style="body", pt=18,
                  maxw=800, maxh=300)
           + footer_slots(3))
    slots = classify(dsl, name="goals")["slots"]
    assert slots["text_1"]["role"] == "title"
    assert slots["text_2"]["role"] == "body"
    assert slots["text_3"]["role"] == "footer"
    assert slots["text_4"]["role"] == "page-number"
    assert all(s["chars"] > 0 for s in slots.values())
    assert slots["text_1"]["default"] == "Goals for Q1"


# --- frontmatter emission -------------------------------------------------------

def test_apply_profile_is_idempotent_and_keeps_body():
    dsl = HEADER + slot(1, "Annual Review")
    p = classify(dsl, name="cover", index=1)
    once = apply_profile(dsl, p)
    twice = apply_profile(once, p)
    assert once == twice
    assert once.startswith("---\n")
    assert once.endswith(dsl)  # body stays byte-identical after the fence


def test_generated_frontmatter_passes_parse_profile():
    dsl = (HEADER + native(CHART_XML, "graphic1") + FULL_BLEED_PICTURE
           + slot(1, "Growth", pt=40) + footer_slots(2))
    p = classify(dsl, name="growth-chart")
    fm, _body = split_frontmatter(apply_profile(dsl, p))
    assert fm is not None
    parsed = parse_profile(fm, source="growth-chart")
    assert parsed["role"] == "data-comparison"
    assert parsed["data"] == "chart"
    assert parsed["comp"] is True
    assert parsed["ideal_count"] == (1, 1)


# --- deck map -------------------------------------------------------------------

def test_derive_deck_map_assigns_roles_in_slide_order():
    profiles = {
        "thanks": {"role": "closer", "slide_index": 13},
        "cover": {"role": "title-primary", "slide_index": 1},
        "toc": {"role": "agenda", "slide_index": 2},
        "divider-a": {"role": "chapter-opener", "slide_index": 3},
        "divider-b": {"role": "chapter-opener", "slide_index": 8},
        "voice": {"role": "quote", "slide_index": 7},
        "kpis": {"role": "data-quantity", "slide_index": 4},
        "columns": {"role": "content-columns", "slide_index": 5},
    }
    assert derive_deck_map(profiles) == {
        "cover": "cover",
        "agenda": "toc",
        "section": ["divider-a", "divider-b"],
        "quote": "voice",
        "closer": "thanks",
        "content": ["kpis", "columns"],
    }


def test_derive_deck_map_omits_missing_roles():
    profiles = {
        "cover": {"role": "title-primary", "slide_index": 1},
        "body": {"role": "content-columns", "slide_index": 2},
    }
    deck_map = derive_deck_map(profiles)
    assert deck_map == {"cover": "cover", "content": ["body"]}
    assert "agenda" not in deck_map and "quote" not in deck_map


# --- integration against a real decompiled layout ---------------------------------

@pytest.mark.skipif(not REAL_COVER.is_file(),
                    reason="feinschliff-extra scientific pack not present")
def test_real_scientific_cover_roundtrip(tmp_path):
    original = REAL_COVER.read_text(encoding="utf-8")
    # A previous generator run may already have fenced the file — strip so
    # the byte-identity assertion below targets the DSL body itself.
    orig_fm, _ = split_frontmatter(original)
    if orig_fm is not None:
        lines = original.splitlines(keepends=True)
        close = [i for i, ln in enumerate(lines) if ln.strip() == "---"][1]
        original = "".join(lines[close + 1:])
    target = tmp_path / "cover.slide.dsl"
    target.write_text(original, encoding="utf-8")

    profile = classify_layout(
        original, layout_name="cover", slide_index=1, total_slides=13,
        asset_root=REAL_COVER.parent.parent / "assets")
    assert profile["role"] == "title-primary"

    fenced = apply_profile(original, profile)
    target.write_text(fenced, encoding="utf-8")
    fm, body = split_frontmatter(fenced)
    assert fm is not None
    parse_profile(fm, source=str(target))
    # split_frontmatter blanks the fence region to keep parser line numbers
    # stable — modulo that padding, the body is the original text.
    assert body.lstrip("\n").rstrip("\n") == original.rstrip("\n")
    # And the fenced file still parses at compile_slide level.
    nodes, _diag = parse_lines(body)
    assert any(n.kind == "text" for n in nodes)
