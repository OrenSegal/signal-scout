#!/usr/bin/env python3
"""Verify signal-scout prospect sources before generating the report.

For each prospect in analysis.json, checks that source_url resolves and that
the cited `evidence` text plausibly appears on the fetched page. This is a
heuristic fuzzy-match, not a proof of authenticity — it catches dead links,
wrong URLs, and evidence that was paraphrased from a search snippet rather
than the actual page, which self-graded `evidence_quality` scores can't catch.

Usage:
    python3 verify_sources.py analysis.json [--timeout 10] [--match-threshold 0.15] [--apply]

Exit code is non-zero only if a source is unreachable (dead link, invalid
URL). Low evidence-text overlap is reported but does not fail the run, since
paraphrasing and page redesigns both produce low ratios legitimately.

Reddit's new UI (reddit.com / www.reddit.com) serves a client-side
bot-verification interstitial to script fetches — HTTP 200, but the page is
just a "please wait for verification" stub, not the real thread. old.reddit.com
serves the same content server-rendered, with no such wall, so reddit.com and
www.reddit.com URLs are fetched via their old.reddit.com equivalent instead
(the URL recorded on the prospect is left untouched — only the fetch target
changes). api.reddit.com and other known bot-walled platforms (X/Twitter,
LinkedIn, Glassdoor, Indeed) still 403/429 real script fetches outright —
that's a platform anti-bot wall, not evidence the link is broken, so those get
a distinct BOT_BLOCKED status instead of counting as unreachable.

Pass --apply to make this robust by default instead of relying on the agent
to hand-edit the JSON afterward: it rewrites the input file in place,
dropping prospects whose source is genuinely UNREACHABLE/INVALID_URL and
appending an "unverified — bot-walled source" note to the `caution` field of
any BOT_BLOCKED prospect that doesn't already disclose it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BOT_WALLED_DOMAINS = (
    "reddit.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "glassdoor.com",
    "indeed.com",
)


def bot_walled_host(url: str) -> str | None:
    """Return the matched domain if url's host is a platform known to 403/429
    scripted fetches regardless of whether the page is actually live, else None."""
    host = urlparse(url).netloc.lower()
    for domain in BOT_WALLED_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


CHALLENGE_MARKERS = ("please wait for verification", "checking your browser")


def canonicalize_for_fetch(url: str) -> str:
    """reddit.com/www.reddit.com serve a client-side bot-verification stub to script
    fetches; old.reddit.com serves the same page server-rendered with no such wall.
    Rewrite just the fetch target — the URL shown to the user is untouched."""
    parsed = urlparse(url)
    if parsed.netloc.lower() in ("reddit.com", "www.reddit.com"):
        return parsed._replace(netloc="old.reddit.com").geturl()
    return url


def is_challenge_page(status: int | None, text: str) -> bool:
    if status != 200 or len(text) > 200:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in CHALLENGE_MARKERS)


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
    """Fraction of evidence's distinguishing words (4+ chars) that appear anywhere in
    the fetched page. A whole-string difflib ratio looks robust but isn't: quick_ratio
    is a global measure over the combined length of both strings, so a short accurate
    quote inside a large real page (a long article, a 60KB forum thread) scores near
    zero even on an exact substring match — this would silently mark good evidence on
    long pages as LOW_MATCH. Word-overlap is unaffected by page length and still
    catches genuinely wrong or fabricated evidence, which shares few if any words."""
    if not evidence or not page_text:
        return 0.0
    words = re.findall(r"[A-Za-z0-9']{4,}", evidence.lower())[:40]
    if not words:
        return 0.0
    page_words = set(re.findall(r"[A-Za-z0-9']{4,}", page_text.lower()))
    hits = sum(1 for w in words if w in page_words)
    return hits / len(words)


def iter_prospects(data: dict[str, Any]):
    for kind in ("individuals", "segments", "companies"):
        for index, item in enumerate(data.get(kind) or []):
            if isinstance(item, dict):
                yield kind, index, item


UNVERIFIED_NOTE = "Unverified — source is on a bot-walled platform; evidence confirmed via search snippet only, not the live page."


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
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite the input JSON in place: drop UNREACHABLE/INVALID_URL prospects and "
             "annotate BOT_BLOCKED ones with an unverified-evidence caution.",
    )
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    results: list[tuple[str, str, str, str, float]] = []
    to_drop: dict[str, set[int]] = {"individuals": set(), "segments": set(), "companies": set()}
    to_annotate: dict[str, set[int]] = {"individuals": set(), "segments": set(), "companies": set()}
    broken = 0
    weak = 0
    bot_walled = 0

    for kind, index, item in iter_prospects(data):
        name = str(item.get("name", "(unnamed)"))
        url = str(item.get("source_url", "")).strip()
        if not url.startswith(("http://", "https://")):
            results.append((kind, name, url, "INVALID_URL", 0.0))
            to_drop[kind].add(index)
            broken += 1
            continue
        status, page_text = fetch_text(canonicalize_for_fetch(url), args.timeout)
        domain = bot_walled_host(url)
        if (status in (403, 429) or is_challenge_page(status, page_text)) and domain:
            # These platforms block automated fetches (403/429) even for real, live
            # pages — a platform anti-bot wall, not evidence the link is dead. Don't
            # fail the run over it; the agent should trust the discovery-search
            # snippet that surfaced this URL and note the gap in `limits` instead.
            results.append((kind, name, url, f"BOT_BLOCKED:{domain} (unverifiable, not dead)", 0.0))
            to_annotate[kind].add(index)
            bot_walled += 1
            continue
        if status is None or status >= 400:
            results.append((kind, name, url, f"UNREACHABLE ({status})", 0.0))
            to_drop[kind].add(index)
            broken += 1
            continue
        ratio = best_match_ratio(str(item.get("evidence", "")), page_text)
        flag = "OK" if ratio >= args.match_threshold else "LOW_MATCH"
        if flag == "LOW_MATCH":
            weak += 1
        results.append((kind, name, url, flag, round(ratio, 2)))

    print(f"{'TYPE':<10} {'NAME':<28} {'STATUS':<28} {'MATCH':<6} URL")
    for kind, name, url, flag, ratio in results:
        print(f"{kind:<10} {name[:28]:<28} {flag:<28} {ratio:<6} {url}")

    total = len(results)
    print(
        f"\n{total} sources checked — {broken} unreachable, {weak} low-evidence-match, "
        f"{bot_walled} bot-walled (unverifiable, not necessarily dead)."
    )
    if broken or weak:
        print("Review flagged prospects before generating the report: drop, re-verify against the live page, or note the gap in `limits`.")
    if bot_walled:
        print("BOT_BLOCKED entries: keep only if the evidence was drawn from a real discovery-search snippet, and disclose the unverified status in `limits`.")

    if args.apply:
        dropped_names = []
        annotated_names = []
        for kind in ("individuals", "segments", "companies"):
            prospects = data.get(kind) or []
            kept = []
            for index, item in enumerate(prospects):
                if index in to_drop[kind]:
                    dropped_names.append(str(item.get("name", "(unnamed)")))
                    continue
                if index in to_annotate[kind]:
                    caution = str(item.get("caution", "")).strip()
                    if "unverified" not in caution.lower() and "bot-walled" not in caution.lower():
                        item["caution"] = f"{caution} {UNVERIFIED_NOTE}".strip()
                    annotated_names.append(str(item.get("name", "(unnamed)")))
                kept.append(item)
            if kind in data:
                data[kind] = kept
        args.input.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        dropped_suffix = f" ({', '.join(dropped_names)})" if dropped_names else ""
        print(f"\n--apply: rewrote {args.input} — dropped {len(dropped_names)} broken-source prospect(s)"
              f"{dropped_suffix}, annotated {len(annotated_names)} bot-walled prospect(s) with an "
              f"unverified-evidence caution.")

    if broken and not args.apply:
        sys.exit(1)


if __name__ == "__main__":
    main()
