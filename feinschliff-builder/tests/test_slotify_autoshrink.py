"""Slotified title/body nodes get an autoshrink floor: template boxes are
sized for showcase copy, real content varies — graceful shrink to the 10pt
emit floor beats silent overflow (work item E)."""
from feinschliff_builder.decompile.slotify import add_autoshrink

DSL = (
    'canvas 1920x1080\n'
    'text 75,483 style:sub size:30pt maxwidth:1835 maxheight:81 '
    '"{{ text_1 | default(\\"Title\\") }}"\n'
    'text 75,600 style:body size:16pt maxwidth:900 maxheight:300 '
    '"{{ text_2 | default(\\"Body copy\\") }}"\n'
    'text 76,1005 style:footer size:10pt maxwidth:80 maxheight:31 '
    '"{{ text_3 | default(\\"15\\") }}"\n'
)
ROLES = {"text_1": "title", "text_2": "body", "text_3": "page-number"}


def test_title_and_body_gain_autoshrink():
    out = add_autoshrink(DSL, ROLES)
    lines = out.splitlines()
    assert "autoshrink:true" in lines[1]
    assert "autoshrink:true" in lines[2]


def test_page_number_untouched():
    out = add_autoshrink(DSL, ROLES)
    assert "autoshrink" not in out.splitlines()[3]


def test_idempotent():
    once = add_autoshrink(DSL, ROLES)
    assert add_autoshrink(once, ROLES) == once


def test_label_text_never_altered():
    out = add_autoshrink(DSL, ROLES)
    assert '"{{ text_1 | default(\\"Title\\") }}"' in out
