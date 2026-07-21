#!/usr/bin/env python3
"""Verify signal-scout prospect sources before generating the report.

For each prospect in analysis.json, checks that source_url resolves and that
the cited `evidence` actually appears on the fetched page. This catches dead
links, wrong URLs, evidence paraphrased from a search snippet rather than the
page itself, and — the case that matters most — claims that are simply not in
the source at all, which self-graded `evidence_quality` scores never catch
because the model grading the evidence is the model that invented it.

It is a containment check, not proof of authenticity: it can tell you a claim
is absent from a page, and it can tell you a claim is quoted from one. It
cannot tell you the page is honest, or that a correctly-quoted line means what
the prospect record says it means.

Every prospect is stamped with `verified_at` (today's date) regardless of
tier, so a report generated later can show how stale its verification is —
that's a display concern, handled by generate_report.py, not this script.
Every individual's outreach `opener` is also checked against its own
`evidence` (not the live page) and flagged with `opener_grounding_note` if it
references specifics the evidence doesn't support — a softer, separate signal
from verification_tier that doesn't fail the run or drop the prospect.

Usage:
    python3 verify_sources.py analysis.json [--timeout 10]
        [--annotate-out OUT.json] [--handoff-out HANDOFF.json]

Exit code is non-zero if any source is unreachable (dead link, invalid URL) or
any claim is missing from its live page. Paraphrase is reported, not failed —
rewording a real signal is legitimate; inventing one is not.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from signal_scout_core import (
    TIER_BROKEN,
    TIER_DISQUALIFYING,
    TIER_LABELS,
    TIER_SNIPPET_ONLY,
    TIER_UNSUPPORTED,
    opener_grounding_note,
    tier_for_evidence,
)


def is_reddit(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host == "reddit.com" or host.endswith(".reddit.com")


# Meta keys whose content is worth harvesting on JS-rendered pages — an SPA
# shell often carries the page's real substance only here and in JSON-LD.
_META_KEYS = frozenset({
    "description", "og:description", "og:title", "twitter:description", "twitter:title",
})


def _ldjson_strings(raw: str) -> str:
    """Extract the human-readable string values from a JSON-LD block. On parse
    failure return the raw text — partial signal beats none."""
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            found.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(parsed)
    return " ".join(found)


class _TextExtractor(HTMLParser):
    """Visible text, plus meta descriptions and JSON-LD string values —
    the latter two are what a JS-rendered page still exposes to a plain fetch,
    and are often enough to verify a claim that would otherwise be Unverified."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False
        self._in_ldjson = False

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "script":
            attr_map = dict(attrs)
            self._in_ldjson = (attr_map.get("type") or "").strip().lower() == "application/ld+json"
            self._skip = not self._in_ldjson
        elif tag == "style":
            self._skip = True
        elif tag == "meta":
            attr_map = dict(attrs)
            key = (attr_map.get("name") or attr_map.get("property") or "").strip().lower()
            content = attr_map.get("content")
            if key in _META_KEYS and content:
                self._chunks.append(f" {content} ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False
            self._in_ldjson = False

    def handle_data(self, data: str) -> None:
        if self._in_ldjson:
            self._chunks.append(f" {_ldjson_strings(data)} ")
        elif not self._skip:
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


WAYBACK_API = "https://archive.org/wayback/available?url="


def fetch_wayback(url: str, timeout: int) -> tuple[str, str, str]:
    """Try the Wayback Machine for a page we couldn't read live.

    Returns (snapshot_url, snapshot_date, page_text) or ("", "", "") if no
    usable archived copy exists. A claim verified against an archived copy is
    still a claim verified against the page as it was published — strictly
    better than giving up as Broken/Unverified, and honestly disclosed in the
    verification note."""
    try:
        request = urllib.request.Request(
            WAYBACK_API + urllib.parse.quote(url, safe=""),
            headers={"User-Agent": "Mozilla/5.0 (signal-scout verifier)"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            info = json.load(response)
        closest = (info.get("archived_snapshots") or {}).get("closest") or {}
        snapshot_url = closest.get("url") if closest.get("available") else ""
        snapshot_date = str(closest.get("timestamp", ""))[:8]
    except Exception:
        return "", "", ""
    if not snapshot_url:
        return "", "", ""
    status, text = fetch_text(snapshot_url, timeout)
    if status is not None and status < 400 and text:
        return snapshot_url, snapshot_date, text
    return "", "", ""


def check_source(url: str, evidence: str, timeout: int) -> tuple[str, str, float, float]:
    """Fetch a source (live first, Wayback fallback) and tier its evidence.

    The Wayback fallback fires when the live page is unreachable, bot-walled
    (Reddit 403, any 429), or yields too little text to check (JS-rendered) —
    each a fetch problem, not a fabrication signal, and each recoverable when
    an archived copy of the page exists."""
    status, page_text = fetch_text(url, timeout)

    live_failed = status is None or status >= 400
    too_thin = not live_failed and len(page_text.strip()) < 200
    if live_failed or too_thin:
        snapshot_url, snapshot_date, archive_text = fetch_wayback(url, timeout)
        if archive_text:
            tier, note, quoted, topical = tier_for_evidence(evidence, archive_text)
            suffix = f" — checked against Wayback archive ({snapshot_date or 'undated'}), live page {'unreachable' if live_failed else 'yielded no text'}"
            return tier, (note + suffix).strip(" —") if not note else note + suffix, quoted, topical

    if status == 429:
        # 429 always means "you're being throttled," on any domain — it is never
        # evidence the link is dead. Conflating it with TIER_BROKEN would fail a
        # real, live source over a rate limit (this happened during dogfooding:
        # heavy HN fetching in one run rate-limited a later run's IP).
        return (TIER_SNIPPET_ONLY,
                "Source rate-limited the fetch (HTTP 429) and no archived copy found; evidence is snippet-sourced only",
                0.0, 0.0)
    if status == 403 and is_reddit(url):
        # Reddit blocks automated fetches (403) even for real, live threads —
        # this is a platform anti-bot wall, not evidence the link is dead. Don't
        # fail the run over it; the agent should trust the discovery-search
        # snippet that surfaced this URL and note the gap in `limits` instead.
        return (TIER_SNIPPET_ONLY,
                "Reddit blocks automated fetch and no archived copy found; evidence is snippet-sourced only",
                0.0, 0.0)
    if live_failed:
        return TIER_BROKEN, f"Source unreachable (status {status}) and no archived copy found", 0.0, 0.0
    return tier_for_evidence(evidence, page_text)


def iter_prospects(data: dict[str, Any]):
    for kind in ("individuals", "segments", "companies"):
        for item in data.get(kind) or []:
            if isinstance(item, dict):
                yield kind, item


def battlecard_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    ctx = data.get("competitive_context")
    if not isinstance(ctx, dict):
        return []
    return [e for e in (ctx.get("battlecard") or []) if isinstance(e, dict)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument(
        "--annotate-out",
        type=Path,
        help="Write the input JSON back out with a verification_tier/verification_note "
        "added to every prospect (including broken ones), for generate_report.py to "
        "render as a badge. Does not drop anything — this is for visibility, not filtering.",
    )
    parser.add_argument(
        "--handoff-out",
        type=Path,
        help="Write a filtered copy of the input JSON — same schema, broken-source and "
        "not-on-page prospects dropped — ready to hand to signal-outreach (or any other "
        "consumer) without carrying dead links or unsupported claims forward.",
    )
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    results: list[tuple[str, str, str, str, float, float]] = []
    counts: dict[str, int] = {}

    def record(kind: str, name: str, url: str, tier: str, note: str, quoted: float, topical: float, item: dict[str, Any]) -> None:
        item["verification_tier"] = tier
        item["verification_note"] = note
        item["verified_at"] = date.today().isoformat()
        counts[tier] = counts.get(tier, 0) + 1
        results.append((kind, name, url, tier, quoted, topical))

    ungrounded_openers = 0
    for kind, item in iter_prospects(data):
        name = str(item.get("name", "(unnamed)"))
        url = str(item.get("source_url", "")).strip()
        if kind == "individuals":
            note = opener_grounding_note(str(item.get("opener", "")), str(item.get("evidence", "")))
            if note:
                item["opener_grounding_note"] = note
                ungrounded_openers += 1
        if not url.startswith(("http://", "https://")):
            record(kind, name, url, TIER_BROKEN, "Invalid source_url", 0.0, 0.0, item)
            continue
        tier, note, quoted, topical = check_source(url, str(item.get("evidence", "")), args.timeout)
        record(kind, name, url, tier, note, quoted, topical, item)

    # Battlecard entries are factual claims about competitors and go through the
    # same verification — but they fail individually (dropped from the report and
    # handoff), never the run: a bad competitor claim shouldn't block a shipped
    # shortlist of good prospects the way a fabricated prospect must.
    battlecard = battlecard_entries(data)
    battlecard_disqualified = 0
    if battlecard:
        mentions = [
            str(item.get("competitor_mentioned", "")).strip().lower()
            for _, item in iter_prospects(data)
            if str(item.get("competitor_mentioned", "")).strip()
        ]
        for entry in battlecard:
            name = str(entry.get("competitor", "(unnamed competitor)"))
            url = str(entry.get("source_url", "")).strip()
            if not url.startswith(("http://", "https://")):
                tier, note, quoted, topical = TIER_BROKEN, "Invalid source_url", 0.0, 0.0
            else:
                tier, note, quoted, topical = check_source(url, str(entry.get("evidence", "")), args.timeout)
            entry["verification_tier"] = tier
            entry["verification_note"] = note
            entry["verified_at"] = date.today().isoformat()
            if tier in TIER_DISQUALIFYING:
                battlecard_disqualified += 1
            results.append(("battlecard", name, url, tier, quoted, topical))
            # Cross-examination: does any prospect in this run independently
            # mention this competitor? Zero corroboration doesn't fail the entry,
            # but it must be visible — a single-source competitor claim shipped
            # as consensus is exactly the kind of thing a client will repeat.
            comp = name.strip().lower()
            entry["corroboration_count"] = sum(1 for m in mentions if comp and (comp in m or m in comp))
            if entry["corroboration_count"] == 0:
                entry["corroboration_note"] = (
                    "No prospect in this run independently mentions this competitor — single-source claim"
                )

    print(f"{'TYPE':<11} {'NAME':<26} {'TIER':<14} {'QUOTED':>6} {'TOPICAL':>7}  URL")
    for kind, name, url, tier, quoted, topical in results:
        label = TIER_LABELS.get(tier, tier)
        print(f"{kind:<11} {name[:26]:<26} {label:<14} {quoted:>6.2f} {topical:>7.2f}  {url}")

    total = len(results)
    summary = ", ".join(f"{n} {TIER_LABELS.get(t, t).lower()}" for t, n in sorted(counts.items())) or "none"
    print(f"\n{total} sources checked — prospects: {summary}.")
    if battlecard:
        single_source = sum(1 for e in battlecard if e.get("corroboration_count", 0) == 0)
        print(f"Battlecard: {len(battlecard)} entr(ies) checked, {battlecard_disqualified} disqualified "
              f"(dropped from report/handoff, run not failed), {single_source} single-source (no corroborating prospect).")

    unsupported = counts.get(TIER_UNSUPPORTED, 0)
    broken = counts.get(TIER_BROKEN, 0)
    if unsupported:
        print(
            f"\n{unsupported} claim(s) are NOT ON THE PAGE they cite. The source loaded and was "
            "readable, and the evidence isn't in it — treat as fabricated until proven otherwise. "
            "Drop the prospect or replace the evidence with text that is actually on the page."
        )
    if broken:
        print(f"\n{broken} source(s) are unreachable or invalid. Drop the prospect or find a working source.")
    if counts.get(TIER_SNIPPET_ONLY):
        print("\nSnippet-only entries: keep only if the evidence came from a real discovery-search "
              "snippet, and disclose the unverified status in `limits`.")
    if ungrounded_openers:
        print(
            f"\n{ungrounded_openers} opener(s) reference specifics not found in their own checked "
            "evidence — tighten them to what the evidence actually supports before sending."
        )

    if args.annotate_out:
        args.annotate_out.parent.mkdir(parents=True, exist_ok=True)
        args.annotate_out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\nAnnotated JSON written: {args.annotate_out.resolve()}")

    if args.handoff_out:
        handoff = json.loads(json.dumps(data))
        dropped = 0
        ctx = handoff.get("competitive_context")
        if isinstance(ctx, dict) and ctx.get("battlecard"):
            kept_entries = [
                e for e in ctx["battlecard"]
                if not (isinstance(e, dict) and e.get("verification_tier") in TIER_DISQUALIFYING)
            ]
            dropped += len(ctx["battlecard"]) - len(kept_entries)
            if kept_entries:
                ctx["battlecard"] = kept_entries
            else:
                ctx.pop("battlecard", None)
        for kind in ("individuals", "segments", "companies"):
            kept = [
                item for item in (handoff.get(kind) or [])
                if isinstance(item, dict) and item.get("verification_tier") not in TIER_DISQUALIFYING
            ]
            dropped += len(handoff.get(kind) or []) - len(kept)
            if kept:
                handoff[kind] = kept
            else:
                handoff.pop(kind, None)
        args.handoff_out.parent.mkdir(parents=True, exist_ok=True)
        args.handoff_out.write_text(json.dumps(handoff, indent=2), encoding="utf-8")
        print(f"Handoff JSON written: {args.handoff_out.resolve()} "
              f"({dropped} broken-source / not-on-page prospect(s) dropped)")

    if broken or unsupported:
        sys.exit(1)


if __name__ == "__main__":
    main()
