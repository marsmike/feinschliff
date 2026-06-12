#!/usr/bin/env python3
"""Annotated brand-pack documentation PDF: render + slot overlay + slot
coverage + full metadata, one page-set per layout, at the slide page size.

Per layout (page order):
  1. **render**   — the defaults showcase render, overlaid with the pack's
     fillable slots (orange = text slot `id · role`, blue = image slot,
     gray = footer/page-number, dashed = baked native chrome).
  2. **coverage** — the same slide built with EVERY slot bound to its own
     default text and ``--slot-debug-color``: bound text renders in the
     debug colour, anything still brand-coloured is NOT slot-covered.
  3. **detail**   — every frontmatter field: role/family/ideal_count/
     data_band badges, description, when_to_use / when_not_to_use, chrome
     notes, slot table (chars budgets, defaults), warnings, element_tree.

Inputs: a deck plan YAML whose slides each reference one layout (the
showcase plan), e.g. built by brand bootstrap. The script builds the two
decks itself (defaults + coverage), converts via soffice, and prints the
final document with headless Chrome at the exact slide page size.

Usage:
  uv run python scripts/render_brand_annotated.py \\
      --plan <showcase-plan.yaml> --out <annotated.pdf> \\
      [--debug-color "#E6007E"] [--workdir <dir>]

External tools: soffice, pdftoppm, Google Chrome (headless print).
"""
from __future__ import annotations

import argparse
import base64
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium", "chromium-browser",
)

EL_RE = re.compile(
    r"^(text|image|native)\s+(\S+)(?:\s+(?:role|class)=(\S+))?\s+@([\d.]+),([\d.]+)\s+([\d.]+)x([\d.]+)")
SLOT_LINE_RE = re.compile(
    r'^(text|picture)\s+(\d+),(\d+)(?:\s+(\d+)x(\d+))?\b(.*\{\{\s*(\w+)[\s|].*)$')
MW_RE = re.compile(r"maxwidth:(\d+)")
MH_RE = re.compile(r"maxheight:(\d+)")

BADGE_FIELDS = ["role", "family", "ideal_count", "data_band", "comparison",
                "family_curated", "variety_exempt", "fixed_chrome", "slide_index"]
PROSE_FIELDS = ["description", "when_to_use", "when_not_to_use",
                "chrome_subject", "chrome_note", "chrome_text"]

ORANGE = (224, 81, 43)
BLUE = (30, 100, 200)
GRAY = (120, 120, 120)
DPI = 120


def _chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit("no Chrome/Chromium found for PDF printing")


def esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def split_doc(p: Path):
    t = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    if m:
        return yaml.safe_load(m.group(1)) or {}, m.group(2)
    return {}, t


def slots_from_body(body: str) -> list[tuple]:
    out = []
    for ln in body.splitlines():
        m = SLOT_LINE_RE.match(ln.strip())
        if not m:
            continue
        kind, x, y, w, h, rest, slot = m.groups()
        x, y = int(x), int(y)
        if kind == "picture":
            if w and h:
                out.append(("image", slot, "replace", x, y, int(w), int(h)))
        else:
            mw, mh = MW_RE.search(rest), MH_RE.search(rest)
            out.append(("text", slot, None, x, y,
                        int(mw.group(1)) if mw else 400,
                        int(mh.group(1)) if mh else 60))
    return out


def default_bindings(fm: dict) -> dict:
    """content dict binding every text slot to its own default."""
    out = {}
    for name, meta in (fm.get("slots") or {}).items():
        if not isinstance(meta, dict) or meta.get("role") == "image":
            continue
        d = meta.get("default")
        if d not in (None, ""):
            out[name] = str(d)
    return out


def build_deck(plan_path: Path, out_pptx: Path, extra_args: list[str]) -> None:
    from feinschliff.cli.main import main as feinschliff_main
    rc = feinschliff_main(["deck", "build", str(plan_path), "-o", str(out_pptx),
                           "--skip-content-lint", "--allow-missing-assets",
                           "--allow-diagram-warnings", *extra_args])
    if rc not in (0, None):
        sys.exit(f"deck build failed (rc={rc}) for {plan_path}")


def to_pdf(pptx: Path, outdir: Path) -> Path:
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            ["soffice", f"-env:UserInstallation=file://{profile}", "--headless",
             "--convert-to", "pdf", str(pptx), "--outdir", str(outdir)],
            check=True, capture_output=True)
    return outdir / (pptx.stem + ".pdf")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", required=True, type=Path,
                    help="Showcase deck plan YAML (one layout per slide)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--debug-color", default="#E6007E",
                    help="Slot-coverage colour (default magenta #E6007E)")
    ap.add_argument("--workdir", type=Path,
                    help="Working dir for intermediate renders "
                         "(default: <out>.work/)")
    args = ap.parse_args()

    from PIL import Image, ImageDraw, ImageFont

    plan_path = args.plan.resolve()
    plan = yaml.safe_load(plan_path.read_text())
    plan_dir = plan_path.parent
    layouts: list[Path] = []
    for spec in plan["slides"]:
        lp = (plan_dir / spec["layout"]).resolve()
        if not lp.is_file():
            # toolkit-relative fallback — same resolution as `deck build`
            from feinschliff.layout_discovery import all_layout_dirs
            lp = next((c for d in all_layout_dirs()
                       if (c := (d.parent / spec["layout"]).resolve()).is_file()),
                      None)
            if lp is None:
                sys.exit(f"layout not found: {spec['layout']}")
        layouts.append(lp)

    work = (args.workdir or args.out.with_suffix(".work")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    pages_dir = work / "pages"
    pages_dir.mkdir(exist_ok=True)

    # --- coverage plan: every slot bound to its default --------------------
    cov_plan = {k: v for k, v in plan.items() if k != "slides"}
    cov_plan["slides"] = []
    for spec, lp in zip(plan["slides"], layouts):
        fm, _body = split_doc(lp)
        merged = default_bindings(fm)
        if spec.get("content_file"):
            cf = (plan_dir / spec["content_file"]).resolve()
            if not cf.is_file():
                from feinschliff.layout_discovery import all_layout_dirs
                cf = next((c for d in all_layout_dirs()
                           if (c := (d.parent / spec["content_file"]).resolve()).is_file()),
                          cf)
            if cf.is_file():
                merged.update(yaml.safe_load(cf.read_text()) or {})
        merged.update(spec.get("content") or {})
        cov_spec = dict(spec)
        cov_spec["layout"] = str(lp)  # plan lives in workdir — absolute path
        cov_spec["content"] = merged
        cov_spec.pop("content_file", None)
        cov_plan["slides"].append(cov_spec)
    cov_plan_path = work / "coverage-plan.yaml"
    cov_plan_path.write_text(yaml.safe_dump(cov_plan, allow_unicode=True,
                                            default_flow_style=False))

    print("building defaults deck …")
    build_deck(plan_path, work / "defaults.pptx", [])
    print("building coverage deck (slot-debug-color) …")
    build_deck(cov_plan_path, work / "coverage.pptx",
               ["--slot-debug-color", args.debug_color])
    print("converting to PDF …")
    defaults_pdf = to_pdf(work / "defaults.pptx", work)
    coverage_pdf = to_pdf(work / "coverage.pptx", work)

    # page size in points, straight from the defaults PDF
    info = subprocess.run(["pdfinfo", str(defaults_pdf)], check=True,
                          capture_output=True, text=True).stdout
    m = re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info)
    page_w_pt, page_h_pt = (float(m.group(1)), float(m.group(2))) if m else (864.0, 486.0)

    subprocess.run(["pdftoppm", "-png", "-r", str(DPI), str(defaults_pdf),
                    str(pages_dir / "def")], check=True)
    subprocess.run(["pdftoppm", "-png", "-r", str(DPI), str(coverage_pdf),
                    str(pages_dir / "cov")], check=True)

    try:
        font_s = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except OSError:
        font_s = ImageFont.load_default()

    def tag(draw, x, y, label, color):
        tw = draw.textlength(label, font=font_s) + 10
        ty = max(0, y - 19)
        draw.rectangle([x, ty, x + tw, ty + 18], fill=color)
        draw.text((x + 5, ty + 1), label, font=font_s, fill="white")

    n = len(layouts)
    digits = max(2, len(str(n)))
    scale = (DPI * (page_w_pt / 72.0)) / 1920.0

    pages_html = []
    for i, lp in enumerate(layouts, 1):
        name = lp.name[: -len(".slide.dsl")] if lp.name.endswith(".slide.dsl") else lp.stem
        fm, body = split_doc(lp)
        src_png = next(pages_dir.glob(f"def-*{i:0{digits}d}.png"), None) \
            or pages_dir / f"def-{i}.png"
        img = Image.open(src_png).convert("RGB")
        draw = ImageDraw.Draw(img)

        elements = []
        for entry in fm.get("element_tree") or []:
            m = EL_RE.match(str(entry).strip())
            if m:
                k, sid, meta, x, y, w, h = m.groups()
                elements.append((k, sid, meta, float(x), float(y), float(w), float(h)))
        if not elements:
            elements = slots_from_body(body)

        for k, sid, meta, x, y, w, h in elements:
            x, y, w, h = x * scale, y * scale, w * scale, h * scale
            if k == "text":
                role = meta or ""
                if role in ("page-number", "footer"):
                    draw.rectangle([x, y, x + w, y + h], outline=GRAY, width=1)
                    tag(draw, x, y, f"{sid} · {role}", GRAY)
                else:
                    draw.rectangle([x, y, x + w, y + h], outline=ORANGE, width=3)
                    tag(draw, x, y, f"{sid} · {role or 'text'}", ORANGE)
            elif k == "image":
                draw.rectangle([x, y, x + w, y + h], outline=BLUE, width=3)
                tag(draw, x, y, f"{sid} · image ({meta or 'replace'})", BLUE)
            else:
                for xx in range(int(x), int(x + w), 10):
                    draw.line([xx, y, min(xx + 5, x + w), y], fill=GRAY, width=1)
                    draw.line([xx, y + h, min(xx + 5, x + w), y + h], fill=GRAY, width=1)
        ann_png = pages_dir / f"ann-{i:0{digits}d}.png"
        img.save(ann_png)

        cov_png = next(pages_dir.glob(f"cov-*{i:0{digits}d}.png"), None) \
            or pages_dir / f"cov-{i}.png"

        badges = ""
        for k in BADGE_FIELDS:
            v = fm.get(k)
            if v in (None, "", False):
                continue
            badges += (f"<span class='badge{' on' if v is True else ''}'>"
                       f"{esc(k if v is True else f'{k}: {v}')}</span>")
        prose = "".join(f"<p class='prose'><b>{esc(k)}</b> {esc(fm[k])}</p>"
                        for k in PROSE_FIELDS if fm.get(k) not in (None, ""))
        slots_rows = ""
        for sid, smeta in (fm.get("slots") or {}).items():
            if not isinstance(smeta, dict):
                continue
            warn = " ⚠" if (fm.get("slot_warnings") or {}).get(sid) else ""
            slots_rows += (
                f"<tr><td><code>{esc(sid)}</code>{warn}</td><td>{esc(smeta.get('role',''))}</td>"
                f"<td class='num'>{esc(smeta.get('chars',''))}</td><td>{esc(smeta.get('class',''))}</td>"
                f"<td class='default'>{esc(str(smeta.get('default',''))[:160])}</td></tr>")
        extra = ""
        if fm.get("image_queries"):
            extra += f"<p class='prose'><b>image_queries</b> {esc(fm['image_queries'])}</p>"
        if fm.get("slot_warnings"):
            rows = "".join(
                f"<li><code>{esc(k)}</code>: "
                f"{esc('; '.join(map(str, v)) if isinstance(v, list) else v)}</li>"
                for k, v in fm["slot_warnings"].items())
            extra += f"<div class='prose'><b>slot_warnings</b><ul class='warn'>{rows}</ul></div>"
        et_html = "".join(f"<div class='et'>{esc(e)}</div>"
                          for e in (fm.get("element_tree") or [])[:28])

        pages_html.append(f"""
<div class='page render'><img src='{ann_png.as_uri()}'>
  <div class='strip'>{i:0{digits}d} · {esc(name)} — slots: orange = text · blue = image · gray = footer/page · dashes = baked chrome</div>
</div>
<div class='page render'><img src='{Path(cov_png).as_uri()}'>
  <div class='strip'>{i:0{digits}d} · {esc(name)} — slot coverage: {esc(args.debug_color)} text = slot-bound · brand-coloured text = NOT bindable</div>
</div>
<div class='page detail'>
  <div class='head'><span class='idx'>{i:0{digits}d}</span><h2>{esc(name)}</h2>{badges}</div>
  <div class='cols'>
    <div class='col'>{prose}{extra}
      {'<h3>element_tree</h3><div class="etwrap">' + et_html + '</div>' if et_html else ''}
    </div>
    <div class='col'>
      <h3>slots <span class='sub'>(bind at deck creation; chars = budget)</span></h3>
      <table><tr><th>slot</th><th>role</th><th>chars</th><th>class</th><th>default</th></tr>{slots_rows}</table>
    </div>
  </div>
</div>""")

    doc = f"""<!doctype html><html><head><meta charset='utf-8'><style>
  @page {{ size: {page_w_pt}pt {page_h_pt}pt; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family:'Noto Sans','Helvetica Neue',Arial,sans-serif; color:#262626; margin:0; }}
  .page {{ width:{page_w_pt}pt; height:{page_h_pt}pt; overflow:hidden; page-break-after:always; position:relative; }}
  .render img {{ width:100%; height:100%; object-fit:contain; display:block; }}
  .strip {{ position:absolute; left:0; right:0; bottom:0; background:#262626ee; color:#fff;
            font-size:8.5pt; padding:3pt 10pt; }}
  .detail {{ padding:16pt 22pt; border-top:5pt solid #FF6840; }}
  .head {{ display:flex; align-items:center; gap:6pt; flex-wrap:wrap; margin-bottom:6pt; }}
  .idx {{ color:#FF6840; font-weight:bold; font-size:13pt; }}
  h2 {{ font-size:14pt; margin:0 8pt 0 0; }}
  h3 {{ font-size:9pt; margin:7pt 0 3pt; color:#E0512B; }}
  h3 .sub {{ color:#999; font-weight:normal; font-size:7.5pt; }}
  .badge {{ background:#f5f5f5; border-radius:8pt; padding:1.5pt 7pt; font-size:7.5pt; color:#555; }}
  .badge.on {{ background:#262626; color:#fff; }}
  .cols {{ display:flex; gap:18pt; height:calc(100% - 30pt); }}
  .col {{ flex:1; min-width:0; overflow:hidden; }}
  .prose {{ font-size:8.5pt; margin:3pt 0; line-height:1.45; }}
  .prose b {{ color:#E0512B; font-size:7pt; text-transform:uppercase; letter-spacing:.4pt; margin-right:4pt; }}
  table {{ border-collapse:collapse; width:100%; font-size:7.5pt; }}
  th, td {{ border:1px solid #eee; padding:2pt 5pt; text-align:left; vertical-align:top; }}
  th {{ background:#fafafa; color:#666; }}
  td.num {{ text-align:right; }} td.default {{ color:#888; }}
  code {{ font-family:Menlo,monospace; font-size:6.5pt; }}
  .etwrap {{ max-height:2.1in; overflow:hidden; }}
  .et {{ font-family:Menlo,monospace; font-size:6pt; color:#555; padding:0.5pt 0;
         border-bottom:1px dotted #eee; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  ul.warn {{ font-size:7pt; color:#a55; margin:1pt 0 4pt 12pt; padding:0; }}
</style></head><body>{''.join(pages_html)}</body></html>"""

    html_path = work / "annotated.html"
    html_path.write_text(doc, encoding="utf-8")
    subprocess.run([_chrome(), "--headless", "--disable-gpu",
                    "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={args.out}", html_path.as_uri()],
                   check=True, capture_output=True)
    print(f"wrote {args.out} ({3 * n} pages: render + coverage + detail per layout)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
