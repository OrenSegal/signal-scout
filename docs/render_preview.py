#!/usr/bin/env python3
"""Render docs/preview.svg (the README preview) from examples/finder-report.json.

Run from the repo root: python3 docs/render_preview.py
"""

import json
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
TIER = {"verified": "Verified", "low_match": "Paraphrased", "snippet_only": "Snippet-only"}


def main() -> None:
    data = json.loads((ROOT / "examples/finder-report.json").read_text())
    rows = [("Segment", p) for p in data.get("segments", [])] + [("Company", p) for p in data.get("companies", [])]
    rows.sort(key=lambda r: r[1]["score"], reverse=True)
    width, y = 760, 48
    out = []

    def text(x, y, s, size=14, weight="normal", fill="#111"):
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}">{escape(s)}</text>')

    text(24, y, f"{data['title']} · signal-scout report · {data['generated_at']}", 22, "bold")
    y += 26
    text(24, y, "No-people mode · every cited source re-fetched and checked by finalize.py", 13, fill="#555")
    y += 30
    for line in textwrap.wrap(data["verdict"], 92):
        text(24, y, line, 14, fill="#222")
        y += 20
    y += 14
    for kind, p in rows:
        out.append(f'<rect x="24" y="{y - 18}" width="{width - 48}" height="28" rx="4" fill="#f4f4f2"/>')
        text(34, y, f"{p['score']}", 14, "bold")
        text(70, y, kind, 12, fill="#555")
        name = p["name"] if len(p["name"]) <= 68 else p["name"][:67] + "…"
        text(140, y, name, 13)
        badge = f"{TIER.get(p.get('verification_tier'), p.get('verification_tier', ''))} {p.get('verified_at', '')}"
        out.append(f'<text x="{width - 34}" y="{y}" font-size="12" text-anchor="end" fill="#1a7f37">{escape(badge)}</text>')
        y += 34
    height = y + 4
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">'
           f'<rect width="100%" height="100%" fill="#fff" stroke="#ddd"/>' + "".join(out) + "</svg>\n")
    (ROOT / "docs/preview.svg").write_text(svg)


if __name__ == "__main__":
    main()
