#!/usr/bin/env python3
"""Diff two signal-scout analysis.json snapshots for watch mode.

Watch mode re-runs the search phase for a product on a schedule and should
only surface what changed — re-showing the same 10 prospects every week
trains the user to ignore the report. This script identifies prospects
present in the current snapshot but absent from the previous one, and
patterns whose count grew, so the agent can report deltas only.

Prospects are matched by (type, name, source_url) — same person/segment
citing a new source counts as new evidence, not a duplicate.

Usage:
    python3 diff_reports.py previous.json current.json [--json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SINGULAR = {"individuals": "individual", "segments": "segment", "companies": "company"}


def prospect_key(kind: str, item: dict[str, Any]) -> tuple[str, str, str]:
    return (kind, str(item.get("name", "")).strip().lower(), str(item.get("source_url", "")).strip())


def load_prospects(data: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for kind in ("individuals", "segments", "companies"):
        for item in data.get(kind) or []:
            if isinstance(item, dict):
                out[prospect_key(kind, item)] = item
    return out


def load_patterns(data: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for pattern in data.get("patterns") or []:
        if isinstance(pattern, dict):
            title = str(pattern.get("title", "")).strip()
            if title:
                out[title] = int(pattern.get("count") or 0)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a text summary")
    args = parser.parse_args()

    previous = json.loads(args.previous.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))

    prev_prospects = load_prospects(previous)
    curr_prospects = load_prospects(current)

    new_keys = set(curr_prospects) - set(prev_prospects)
    dropped_keys = set(prev_prospects) - set(curr_prospects)
    new_prospects = [curr_prospects[k] | {"_type": k[0]} for k in new_keys]
    dropped_prospects = [prev_prospects[k] | {"_type": k[0]} for k in dropped_keys]

    prev_patterns = load_patterns(previous)
    curr_patterns = load_patterns(current)
    grown_patterns = [
        {"title": title, "previous_count": prev_patterns.get(title, 0), "current_count": count}
        for title, count in curr_patterns.items()
        if count > prev_patterns.get(title, 0)
    ]

    if args.json:
        print(json.dumps({
            "new_prospects": new_prospects,
            "dropped_prospects": dropped_prospects,
            "grown_patterns": grown_patterns,
        }, indent=2))
        return

    if not new_prospects and not dropped_prospects and not grown_patterns:
        print("No changes since the previous snapshot.")
        return

    if new_prospects:
        print(f"NEW ({len(new_prospects)}):")
        for item in sorted(new_prospects, key=lambda x: -int(x.get("score") or 0)):
            label = SINGULAR.get(item["_type"], item["_type"])
            print(f"  [{label}] {item.get('name', '(unnamed)')} — {item.get('score', '?')}/100 — {item.get('pain_signal', '')[:80]}")
        print()

    if dropped_prospects:
        print(f"NO LONGER SURFACED ({len(dropped_prospects)}) — evidence may be stale or superseded:")
        for item in dropped_prospects:
            label = SINGULAR.get(item["_type"], item["_type"])
            print(f"  [{label}] {item.get('name', '(unnamed)')}")
        print()

    if grown_patterns:
        print("PATTERNS GROWING:")
        for pattern in grown_patterns:
            print(f"  {pattern['title']}: {pattern['previous_count']} → {pattern['current_count']}")


if __name__ == "__main__":
    main()
