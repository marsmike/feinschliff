"""slotify_native_text + cleanup passes — the per-slide decompile loop."""
from __future__ import annotations

import base64
import re

from feinschliff_builder.decompile.cleanup import (
    cleanup_dsl,
    dedupe_native_pics,
    dedupe_text_lines,
    drop_helper_captions,
    drop_prompt_copies,
    unslotified_text_report,
)
from feinschliff_builder.decompile.slotify import slotify_native_text


def _b64(xml: str) -> str:
    return base64.b64encode(xml.encode()).decode("ascii")


_TABLE_XML = (
    '<p:graphicFrame xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    "<a:tbl><a:tr>"
    "<a:tc><a:txBody><a:p><a:r><a:t>Headline</a:t></a:r></a:p></a:txBody></a:tc>"
    "<a:tc><a:txBody><a:p><a:r><a:t>Placeholder Subheadline</a:t></a:r></a:p></a:txBody></a:tc>"
    "<a:tc><a:txBody><a:p><a:r><a:t>  </a:t></a:r></a:p></a:txBody></a:tc>"
    "</a:tr></a:tbl></p:graphicFrame>"
)

_CHART_XML = (
    '<p:graphicFrame xmlns:p="x" xmlns:c="y"><c:chart r:id="rId2" xmlns:r="z"/>'
    "<a:t xmlns:a='w'>Category 1</a:t></p:graphicFrame>"
)


def test_native_table_text_runs_become_slots():
    dsl = f'canvas 1920x1080\nnative table1 b64:"{_b64(_TABLE_XML)}"\n'
    new_dsl, slots, logs = slotify_native_text(dsl, None)
    assert [s["name"] for s in slots] == ["text_1", "text_2"]
    assert slots[0]["default"] == "Headline"
    xml = base64.b64decode(
        new_dsl.split('b64:"')[1].split('"')[0]).decode()
    assert '{{ text_1 | default("Headline") }}' in xml
    # whitespace-only run untouched
    assert "<a:t>  </a:t>" in xml


def test_native_slot_numbering_continues_after_existing():
    dsl = ('text 76,76 maxwidth:100 maxheight:40 '
           '"{{ text_3 | default(\\"T\\") }}"\n'
           f'native table1 b64:"{_b64(_TABLE_XML)}"\n')
    _new, slots, _logs = slotify_native_text(dsl, None)
    assert [s["name"] for s in slots] == ["text_4", "text_5"]


def test_native_slotify_idempotent():
    dsl = f'native table1 b64:"{_b64(_TABLE_XML)}"\n'
    once, slots1, _ = slotify_native_text(dsl, None)
    twice, slots2, _ = slotify_native_text(once, None)
    assert slots1 and not slots2
    assert once == twice


def test_charts_are_skipped():
    dsl = f'native graphic1 b64:"{_b64(_CHART_XML)}"\n'
    new_dsl, slots, _ = slotify_native_text(dsl, None)
    assert not slots and new_dsl == dsl


def test_sidecar_payload_rewritten_on_disk(tmp_path):
    assets = tmp_path / "assets"
    (assets / "native").mkdir(parents=True)
    (assets / "native" / "t.xml").write_text(_TABLE_XML, encoding="utf-8")
    dsl = 'native table1 xml_file:"native/t.xml"\n'
    new_dsl, slots, _ = slotify_native_text(dsl, assets)
    assert new_dsl == dsl  # the DSL line keeps its sidecar reference
    assert len(slots) == 2
    assert '{{ text_1 | default("Headline") }}' in (
        assets / "native" / "t.xml").read_text(encoding="utf-8")


# --- cleanup passes ---------------------------------------------------------

def test_dedupe_text_lines():
    dsl = ('text 76,76 maxwidth:80 maxheight:31 "15"\n'
           'text 76,76 maxwidth:80 maxheight:31 "15"\n')
    out, n = dedupe_text_lines(dsl)
    assert n == 1 and out.count('"15"') == 1


def test_prompt_copies_drop_earlier_keep_later():
    dsl = ('text 76,76 style:body maxwidth:1834 maxheight:122 "Title A"\n'
           'text 76,76 style:body color:black maxwidth:1834 maxheight:122 "Title B"\n')
    out, n = drop_prompt_copies(dsl)
    assert n == 1 and "Title B" in out and "Title A" not in out


def test_partial_overlap_survives():
    # KPI tile: 28pt value box and 16pt caption overlap ~0.5 — keep both.
    dsl = ('text 546,675 maxwidth:457 maxheight:152 "94%"\n'
           'text 653,705 maxwidth:350 maxheight:122 "detection rate"\n')
    out, n = drop_prompt_copies(dsl)
    assert n == 0 and "94%" in out


def test_helper_captions_dropped():
    dsl = ('text 1007,0 maxwidth:281 maxheight:27 "Add Picture"\n'
           'text 76,208 maxwidth:900 maxheight:780 "Add Text\\nSecond level"\n'
           'text 76,76 maxwidth:900 maxheight:100 "Real title"\n')
    out, n = drop_helper_captions(dsl)
    assert n == 2 and "Real title" in out and "Add Picture" not in out


def _pic_xml(x: int, y: int, cx: int = 2000000, cy: int = 2000000) -> str:
    return (
        '<p:pic xmlns:p="x" xmlns:a="y"><p:spPr xmlns:p="x"><a:xfrm>'
        f'<a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/>'
        "</a:xfrm></p:spPr></p:pic>"
    )


def test_stacked_native_pics_deduped():
    dsl = (f'native pic1 b64:"{_b64(_pic_xml(100000, 100000))}"\n'
           f'native pic2 b64:"{_b64(_pic_xml(101000, 99000))}"\n'   # ~same rect
           f'native pic3 b64:"{_b64(_pic_xml(5000000, 100000))}"\n')  # elsewhere
    out, n = dedupe_native_pics(dsl)
    assert n == 1
    assert "pic2" in out and "pic3" in out and "pic1" not in out


def test_unslotified_report_and_cleanup_roundtrip():
    dsl = (f'native table1 b64:"{_b64(_TABLE_XML)}"\n'
           'text 76,76 maxwidth:100 maxheight:40 "Literal"\n')
    report = unslotified_text_report(dsl, None)
    assert any("Literal" in r for r in report)
    assert any("Headline" in r for r in report)
    new_dsl, _slots, _ = slotify_native_text(dsl, None)
    report2 = unslotified_text_report(new_dsl, None)
    assert not any("Headline" in r for r in report2)
    cleaned, stats = cleanup_dsl(new_dsl)
    assert isinstance(stats, dict)


def test_native_text_double_blanked_when_text_line_matches():
    from feinschliff_builder.decompile.cleanup import strip_native_text_doubles
    sp = ('<p:sp xmlns:p="x" xmlns:a="y"><p:spPr><a:xfrm>'
          '<a:off x="445500" y="3073950"/><a:ext cx="1679062" cy="571500"/>'
          '</a:xfrm></p:spPr><p:txBody><a:p><a:r><a:t>Step 1</a:t></a:r>'
          "</a:p></p:txBody></p:sp>")
    dsl = (f'native shape1 b64:"{_b64(sp)}"\n'
           'text 78,538 style:body maxwidth:294 maxheight:100 '
           '"{{ text_8 | default(\\"Step 1\\") }}"\n')
    out, n = strip_native_text_doubles(dsl, None, width_emu=10969625)
    assert n == 1
    xml = base64.b64decode(out.split('b64:"')[1].split('"')[0]).decode()
    assert "<a:t></a:t>" in xml and "Step 1" not in xml
    # the regular text slot stays
    assert 'default(\\"Step 1\\")' in out


def test_native_text_without_matching_text_line_kept():
    from feinschliff_builder.decompile.cleanup import strip_native_text_doubles
    sp = ('<p:sp xmlns:p="x" xmlns:a="y"><p:txBody><a:p><a:r>'
          "<a:t>Unique label</a:t></a:r></a:p></p:txBody></p:sp>")
    dsl = (f'native shape1 b64:"{_b64(sp)}"\n'
           'text 78,538 maxwidth:294 maxheight:100 "Other"\n')
    out, n = strip_native_text_doubles(dsl, None)
    assert n == 0 and out == dsl


def test_native_pic_rects_filters_marks():
    from feinschliff_builder.decompile.cleanup import native_pic_rects
    tile = _pic_xml(445500, 1074000, 1263000, 1263000)   # ~221px tile
    logo = _pic_xml(9849600, 5760000, 684000, 207973)    # ~120x36 mark
    dsl = (f'native pic1 b64:"{_b64(tile)}"\n'
           f'native pic2 b64:"{_b64(logo)}"\n')
    rects = native_pic_rects(dsl, None, width_emu=10969625)
    assert len(rects) == 1
    r = rects[0]
    assert abs(r["x"] - 78) < 2 and abs(r["w"] - 221) < 2


def test_clip_text_at_native_pic():
    from feinschliff_builder.decompile.cleanup import native_pic_rects
    from feinschliff_builder.decompile.slotify import clip_text_to_images
    tile = _pic_xml(428000, 1074000, 1263000, 1263000)
    dsl = (f'native pic1 b64:"{_b64(tile)}"\n'
           'text 75,188 style:body maxwidth:593 maxheight:238 '
           '"{{ text_2 | default(\\"Headline\\") }}"\n')
    rects = native_pic_rects(dsl, None, width_emu=10969625)
    out, logs = clip_text_to_images(dsl, extra_images=rects)
    assert logs and "shifted right of picture" in logs[0]
    # shifted box starts right of the 221px photo with the gutter
    assert re.search(r"text 31[12](?:\.\d+)?,", out)
