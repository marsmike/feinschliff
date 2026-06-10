"""General eval support for DSL templates (.slide.dsl layouts).

The grader scores `.slide.dsl` artifacts like it already scores diagram
artifacts; checks read the brand's OWN tokens, so they stay general (no
per-brand constants). `title-on-grid` codifies the decompiler drift root
cause: a layout's title must sit on the brand's `slide.padding-x` margin.
"""
import json

from feinschmiede.brand_discovery import find_brand
from feinschliff_builder.eval.checks import CheckContext, run_check
from feinschliff_builder.eval.grader import grade

_BRAND = find_brand("feinschliff").root  # padding-x = 100


def _synthetic_brand(tmp_path, *, footer_date="2099-01", footer_section="DEMO"):
    """A minimal standalone brand pack with footer template-default tokens."""
    d = tmp_path / "brands" / "acme"
    d.mkdir(parents=True)
    d.joinpath("tokens.json").write_text(json.dumps({
        "color": {"$type": "color", "accent": {"$value": "#FF0000"},
                  "ink": {"$value": "#111111"}, "paper": {"$value": "#FFFFFF"}},
        "font-family": {"$type": "fontFamily", "body": {"$value": ["Arial"]},
                        "display": {"$value": ["Arial"]}, "mono": {"$value": ["Courier"]}},
        "font-size": {"$type": "dimension", "slide-title": {"$value": "40px"},
                      "body": {"$value": "20px"}},
        "slide": {"$type": "dimension", "width": {"$value": "1920px"},
                  "height": {"$value": "1080px"}, "padding-x": {"$value": "90px"}},
        "brand": {"footer-date": {"$type": "string", "$value": footer_date},
                  "footer-section": {"$type": "string", "$value": footer_section}},
    }))
    return d


def _ctx():
    return CheckContext(brand_dir=_BRAND)


def _layout(tmp_path, title_x):
    p = tmp_path / "t.slide.dsl"
    p.write_text(
        "canvas 1920x1080\n"
        "theme feinschliff\n"
        "rect 0,0 1920x1080 fill:paper\n"
        f'text {title_x},90 style:body size:20pt maxwidth:800 maxheight:111 "Title"\n'
    )
    return p


def test_title_on_grid_passes_when_title_at_padding_x(tmp_path):
    assert run_check("title-on-grid", _layout(tmp_path, 100), _ctx()) is True


def test_title_on_grid_fails_when_title_drifts_left(tmp_path):
    assert run_check("title-on-grid", _layout(tmp_path, 52), _ctx()) is False


def test_title_on_grid_passes_when_no_top_title(tmp_path):
    # A cover/divider with only a bottom title has no top title to misplace.
    p = tmp_path / "cover.slide.dsl"
    p.write_text(
        "canvas 1920x1080\ntheme feinschliff\nrect 0,0 1920x1080 fill:cover-dark\n"
        'text 100,782 style:title-l size:60pt maxwidth:1200 maxheight:133 "Thanks"\n'
    )
    assert run_check("title-on-grid", p, _ctx()) is True


def test_footer_overridable_fails_on_hardcoded_template_literal(tmp_path):
    brand = _synthetic_brand(tmp_path, footer_date="2099-01", footer_section="DEMO")
    lay = tmp_path / "leak.slide.dsl"
    lay.write_text(
        'canvas 1920x1080\ntheme acme\n'
        'footer page:"3" date:"2099-01" section:"DEMO" right:"X"\n'
    )
    assert run_check("footer-overridable", lay, CheckContext(brand_dir=brand)) is False


def test_footer_overridable_passes_when_value_is_a_slot_default(tmp_path):
    brand = _synthetic_brand(tmp_path, footer_date="2099-01", footer_section="DEMO")
    lay = tmp_path / "ok.slide.dsl"
    lay.write_text(
        'canvas 1920x1080\ntheme acme\n'
        'footer page:"{{ footer_page | default(\\"3\\") }}" '
        'date:"{{ footer_date | default(\\"2099-01\\") }}" '
        'section:"{{ footer_section | default(\\"DEMO\\") }}" right:"X"\n'
    )
    assert run_check("footer-overridable", lay, CheckContext(brand_dir=brand)) is True


def test_footer_overridable_vacuous_pass_when_brand_has_no_footer_tokens(tmp_path):
    lay = tmp_path / "ok.slide.dsl"
    lay.write_text('canvas 1920x1080\ntheme feinschliff\ntext 100,90 style:body "T"\n')
    # feinschliff defines no brand.footer-date/section -> nothing to leak
    assert run_check("footer-overridable", lay, CheckContext(brand_dir=_BRAND)) is True


def test_grader_scores_a_slide_dsl_suite(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "ok").with_suffix(".slide.dsl").write_text(
        "canvas 1920x1080\ntheme feinschliff\n"
        'text 100,90 style:body size:20pt maxwidth:800 maxheight:111 "T"\n'
    )
    evals = tmp_path / "evals.json"
    evals.write_text(json.dumps({
        "skill": "slide-dsl",
        "tests": [{"name": "ok", "checks": ["title-on-grid"]}],
    }))
    report = grade(evals, results, _BRAND)
    assert report["score"] == 1.0
    assert report["tests"][0]["exists"] is True
