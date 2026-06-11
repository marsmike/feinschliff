"""Opt-in brand-font embedding (ECMA-376 embeddedFontLst + fntdata parts).

PowerPoint/LibreOffice load /ppt/fonts/fontN.fntdata (plain TTF/OTF bytes;
obfuscation is optional per spec) when presentation.xml declares
embedTrueTypeFonts="1" plus a <p:embeddedFontLst> mapping typeface -> r:id.
Only .ttf/.otf files embed; .ttc collections (and anything else fontconfig
hands back, e.g. .woff2) are skipped with a warning. Font files resolve via
feinschmiede.text.measure.find_font_file — an unresolvable family is skipped
(the deck still builds, fonts just aren't embedded).

python-pptx (1.0.x) needs no special registration: a plain
``Part(partname, content_type, package, blob=...)`` related from the
presentation part is save-reachable, and the saved ``[Content_Types].xml``
gets a ``<Default Extension="fntdata" ContentType="application/x-fontdata"/>``
entry derived from the part's content type (verified empirically).
"""
from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree
from pptx.opc.package import Part

from feinschmiede.text.measure import find_font_file

_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_RT_FONT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
_CT_FNTDATA = "application/x-fontdata"

# CT_Presentation child order (ECMA-376 §19.2.1.26): embeddedFontLst comes
# after sldSz/notesSz/smartTags and before custShowLst/photoAlbum/custDataLst/
# kinsoku/defaultTextStyle/modifyVerifier/extLst.
_AFTER_TAGS = [f"{{{_NS_P}}}{t}" for t in (
    "custShowLst", "photoAlbum", "custDataLst", "kinsoku",
    "defaultTextStyle", "modifyVerifier", "extLst",
)]

_EMBEDDABLE_SUFFIXES = {".ttf", ".otf"}


def _q(tag: str) -> str:
    return f"{{{_NS_P}}}{tag}"


def _embeddable(path: Path | None, family: str, face: str) -> Path | None:
    """Return `path` when it's an embeddable single-font file, else None.

    .ttc collections (and any other suffix) are skipped with a WARN —
    fntdata parts must contain a single TTF/OTF font program.
    """
    if path is None:
        return None
    if path.suffix.lower() not in _EMBEDDABLE_SUFFIXES:
        print(
            f"feinschliff: WARN: font '{family}' ({face}) resolves to "
            f"{path.name} — only .ttf/.otf can be embedded; skipping.",
            file=sys.stderr,
        )
        return None
    return path


def embed_brand_fonts(prs, tokens) -> list[str]:
    """Embed regular+bold faces for the brand display/body families.

    Returns the list of typefaces actually embedded (may be empty).
    Idempotent: a second call must not duplicate parts or list entries —
    if presentation.xml already carries a <p:embeddedFontLst> we return []
    immediately (no merging; the first call owns the list).
    """
    pres_el = prs.element
    if pres_el.find(_q("embeddedFontLst")) is not None:
        return []

    # Brand families: display + body, first (primary) name each, deduped.
    families: list[str] = []
    for role in ("display", "body"):
        try:
            fam = tokens.font_family(role)[0]
        except (KeyError, IndexError):
            continue
        if fam not in families:
            families.append(fam)

    # Resolve font files up front — only touch the package/XML when at
    # least one family actually embeds.
    entries: list[tuple[str, Path, Path | None]] = []
    for fam in families:
        regular = _embeddable(find_font_file(fam), fam, "regular")
        if regular is None:
            print(
                f"feinschliff: WARN: font '{fam}' not resolvable to a "
                f".ttf/.otf file — not embedding.",
                file=sys.stderr,
            )
            continue
        bold = _embeddable(find_font_file(fam, bold=True), fam, "bold")
        # No distinct bold face (fontconfig fell back to the regular file):
        # don't write a <p:bold> entry pointing at the same data.
        if bold is not None and bold.resolve() == regular.resolve():
            bold = None
        entries.append((fam, regular, bold))
    if not entries:
        return []

    # Materialise each distinct font file as ONE /ppt/fonts/fontN.fntdata
    # part related from the presentation part (dedupe across families).
    pkg = prs.part.package
    rid_by_file: dict[str, str] = {}

    def _rid_for(path: Path) -> str:
        key = str(path.resolve())
        if key not in rid_by_file:
            partname = pkg.next_partname("/ppt/fonts/font%d.fntdata")
            part = Part(partname, _CT_FNTDATA, pkg, blob=path.read_bytes())
            rid_by_file[key] = prs.part.relate_to(part, _RT_FONT)
        return rid_by_file[key]

    lst = etree.SubElement(pres_el, _q("embeddedFontLst"))
    # Reposition per CT_Presentation child order: before the first present
    # anchor that must follow embeddedFontLst (else leave appended).
    anchor = next((c for c in pres_el if c.tag in _AFTER_TAGS), None)
    if anchor is not None:
        anchor.addprevious(lst)

    embedded: list[str] = []
    for fam, regular, bold in entries:
        ef = etree.SubElement(lst, _q("embeddedFont"))
        etree.SubElement(ef, _q("font")).set("typeface", fam)
        etree.SubElement(ef, _q("regular")).set(f"{{{_NS_R}}}id", _rid_for(regular))
        if bold is not None:
            etree.SubElement(ef, _q("bold")).set(f"{{{_NS_R}}}id", _rid_for(bold))
        embedded.append(fam)

    pres_el.set("embedTrueTypeFonts", "1")
    return embedded
