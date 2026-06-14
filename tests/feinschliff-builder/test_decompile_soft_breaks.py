"""`<a:br/>` soft line breaks must become newlines, not vanish.

A title authored as "The power<a:br/>of communication" renders on two lines
in PowerPoint; dropping the break concatenates the runs into
"The powerof communication" — wrong text AND wrong layout (one long line
instead of two short ones).
"""
from __future__ import annotations

from lxml import etree

from feinschliff_builder.decompile.pptx_svg_decompile import _text_runs

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _sp_with_break() -> etree._Element:
    return etree.fromstring(f"""
      <p:sp xmlns:p="{_P}" xmlns:a="{_A}">
        <p:txBody>
          <a:bodyPr/>
          <a:p>
            <a:r><a:rPr lang="en-US" sz="6000"/><a:t>The power</a:t></a:r>
            <a:br><a:rPr lang="en-US" sz="6000"/></a:br>
            <a:r><a:rPr lang="en-US" sz="6000"/><a:t>of communication</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    """.encode())


def test_soft_break_becomes_newline():
    runs = _text_runs(_sp_with_break(), {}, {})
    flat = "".join(r.text for r in runs)
    assert flat == "The power\nof communication"


def test_leading_break_is_not_emitted():
    sp = etree.fromstring(f"""
      <p:sp xmlns:p="{_P}" xmlns:a="{_A}">
        <p:txBody><a:bodyPr/>
          <a:p>
            <a:br/>
            <a:r><a:t>Body</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    """.encode())
    runs = _text_runs(sp, {}, {})
    flat = "".join(r.text for r in runs)
    assert flat == "Body"
