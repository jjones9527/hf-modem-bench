#!/usr/bin/env python3
"""Render a report in docs/ (Markdown) to a self-contained PDF for email.
    python3 scripts/md_to_pdf.py docs/wgn-report.md docs/wgn-report.pdf [--charts logs/archive/reports/interim-wgn]
Charts referenced as charts/<dir>/<name>.png are embedded inline, as the SVG of the same name
from --charts when it exists (vector, sharp at any zoom), else as the PNG. Links to other files
in the repository become GitHub links, so they work from an email. Printed with headless
Chrome (US Letter); needs the `markdown` package."""
import argparse, base64, re, subprocess, sys, tempfile
from pathlib import Path

import markdown

REPO = "https://github.com/jjones9527/hf-modem-bench"
BRANCH = "phase1-scaffold"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: Letter; margin: 16mm 14mm 16mm 14mm; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 10pt; line-height: 1.42;
       color: #1d2733; background: #fff; }
h1 { font-size: 21pt; margin: 0 0 4pt; color: #0f2a44; }
h1 + p strong { font-size: 11.5pt; color: #3a4d63; }
h2 { font-size: 14.5pt; color: #0f2a44; border-bottom: 1.5px solid #c9d4e0; padding-bottom: 3pt;
     margin-top: 20pt; break-after: avoid; }
h3 { font-size: 11.5pt; color: #1f4c78; margin-top: 14pt; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
a { color: #1f5fa8; text-decoration: none; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.6pt; background: #f1f4f8; padding: 0 2px; border-radius: 2px; }
table { border-collapse: collapse; margin: 6pt 0 10pt; width: 100%; font-size: 8.8pt; break-inside: auto; }
th { background: #e8eef5; color: #0f2a44; text-align: left; font-weight: 600; }
th, td { border: 0.6pt solid #c3ceda; padding: 2.6pt 4.5pt; vertical-align: top; }
tr { break-inside: avoid; }
tbody tr:nth-child(even) td { background: #f8fafc; }
table.wide { font-size: 7.6pt; }
table.wide th, table.wide td { padding: 2pt 3pt; }
td.num, th.num { text-align: right; white-space: nowrap; }
figure { margin: 8pt 0 12pt; break-inside: avoid; text-align: center; }
figure img { width: 100%; max-width: 172mm; }
figcaption { font-size: 8.6pt; color: #4a5a6c; margin-top: 2pt; }
.cover-note { font-size: 8.6pt; color: #4a5a6c; border-top: 0.6pt solid #c9d4e0; margin-top: 18pt; padding-top: 5pt; }
ul { padding-left: 16pt; }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--charts", default="logs/archive/reports/interim-wgn")
    a = ap.parse_args()
    src = Path(a.src)
    text = src.read_text()

    # links to repository files -> GitHub
    def link(m):
        label, target = m.group(1), m.group(2)
        if re.match(r"^(https?:|#|mailto:)", target):
            return m.group(0)
        p = (src.parent / target).resolve().relative_to(Path.cwd().resolve())
        kind = "tree" if target.endswith("/") or (Path.cwd() / p).is_dir() else "blob"
        return f"[{label}]({REPO}/{kind}/{BRANCH}/{p.as_posix()})"
    text = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", link, text)

    html = markdown.markdown(text, extensions=["tables", "sane_lists", "toc"])

    # charts: inline, SVG preferred; alt text becomes the caption
    def img(m):
        alt, path = m.group(1), m.group(2)
        name = Path(path).stem
        svg = Path(a.charts) / f"{name}.svg"
        if svg.exists():
            data, mime = svg.read_bytes(), "image/svg+xml"
        else:
            data, mime = (src.parent / path).read_bytes(), "image/png"
        uri = f"data:{mime};base64,{base64.b64encode(data).decode()}"
        return f'<figure><img src="{uri}" alt="{alt}"><figcaption>{alt}</figcaption></figure>'
    html = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>', img, html)

    # wide tables (8+ columns) get a smaller font; numeric cells right-aligned
    def table(m):
        t = m.group(0)
        cols = t.split("</tr>", 1)[0].count("<th")
        if cols < 8:
            return t
        t = t.replace("<table>", '<table class="wide">', 1)
        return re.sub(r"<td>([−\-\d.,/ ]+(?: of \d+)?)</td>", r'<td class="num">\1</td>', t)
    html = re.sub(r"<table>.*?</table>", table, html, flags=re.S)

    title = re.search(r"<h1[^>]*>(.*?)</h1>", html).group(1)
    footer = (f'<p class="cover-note">From the hf-modem-bench project: {REPO}. This PDF is generated from '
              f'<a href="{REPO}/blob/{BRANCH}/{src.as_posix()}">{src.as_posix()}</a>; the Markdown there is the current version.</p>')
    doc = f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{CSS}</style></head><body>{html}{footer}</body></html>"
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "report.html"
        h.write_text(doc)
        out = Path(a.out).resolve()
        r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={out}", h.as_uri()], capture_output=True, text=True, timeout=180)
        if not out.exists():
            sys.exit(f"Chrome did not write the PDF:\n{r.stderr[-2000:]}")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
