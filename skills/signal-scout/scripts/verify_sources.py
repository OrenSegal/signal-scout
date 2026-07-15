#!/usr/bin/env python3
"""Verify signal-scout prospect sources before generating the report.

For each prospect in analysis.json, checks that source_url resolves and that
the cited `evidence` text plausibly appears on the fetched page. This is a
heuristic fuzzy-match, not a proof of authenticity — it catches dead links,
wrong URLs, and evidence that was paraphrased from a search snippet rather
than the actual page, which self-graded `evidence_quality` scores can't catch.

Usage:
    python3 verify_sources.py analysis.json [--timeout 10] [--match-threshold 0.15]

Exit code is non-zero only if a source is unreachable (dead link, invalid
URL). Low evidence-text overlap is reported but does not fail the run, since
paraphrasing and page redesigns both produce low ratios legitimately.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._chunks)).strip()


def fetch_text(url: str, timeout: int) -> tuple[int | None, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (signal-scout verifier)"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(2_000_000).decode(charset, errors="ignore")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception:
        return None, ""
    parser = _TextExtractor()
    parser.feed(raw)
    return status, parser.text()


def best_match_ratio(evidence: str, page_text: str) -> float:
    if not evidence or not page_text:
        return 0.0
    words = re.findall(r"[A-Za-z0-9']{4,}", evidence)[:40]
    if not words:
        return 0.0
    snippet = " ".join(words).lower()
    return difflib.SequenceMatcher(None, snippet, page_text.lower()).quick_ratio()


def iter_prospects(data: dict[str, Any]):
    for kind in ("individuals", "segments", "companies"):
        for item in data.get(kind) or []:
            if isinstance(item, dict):
                yield kind, item


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument(
        "--match-threshold",
        type=float,
        default=0.15,
        help="Minimum fuzzy overlap between cited evidence and page text (0-1)",
    )
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    results: list[tuple[str, str, str, str, float]] = []
    broken = 0
    weak = 0

    for kind, item in iter_prospects(data):
        name = str(item.get("name", "(unnamed)"))
        url = str(item.get("source_url", "")).strip()
        if not url.startswith(("http://", "https://")):
            results.append((kind, name, url, "INVALID_URL", 0.0))
            broken += 1
            continue
        status, page_text = fetch_text(url, args.timeout)
        if status is None or status >= 400:
            results.append((kind, name, url, f"UNREACHABLE ({status})", 0.0))
            broken += 1
            continue
        ratio = best_match_ratio(str(item.get("evidence", "")), page_text)
        flag = "OK" if ratio >= args.match_threshold else "LOW_MATCH"
        if flag == "LOW_MATCH":
            weak += 1
        results.append((kind, name, url, flag, round(ratio, 2)))

    print(f"{'TYPE':<10} {'NAME':<28} {'STATUS':<16} {'MATCH':<6} URL")
    for kind, name, url, flag, ratio in results:
        print(f"{kind:<10} {name[:28]:<28} {flag:<16} {ratio:<6} {url}")

    total = len(results)
    print(f"\n{total} sources checked — {broken} unreachable, {weak} low-evidence-match.")
    if broken or weak:
        print("Review flagged prospects before generating the report: drop, re-verify against the live page, or note the gap in `limits`.")
    if broken:
        sys.exit(1)


if __name__ == "__main__":
    main()
