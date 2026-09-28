#!/usr/bin/env python3
"""Run signal-scout's deterministic pipeline code on fixture inputs and grade the outputs.

Each case in evals/pipeline/cases/<id>/ has:
  input.json     an analysis.json, the file the skill's LLM step would write
  pages.json     url -> {"status", "text", optional "wayback", optional "archive_ph"}
                 served in place of the network, so the run is offline and repeatable
  expected.json  what the code should produce for this input

For every case this script calls the real code in skills/signal-scout/scripts:
  - finalize.validate()            schema checks and score-drift check
  - signal_scout_core.compute_score() on every prospect's dimensions
  - verify_sources.main()          verification tiers, opener grounding notes,
                                   the handoff file, and the exit code
and compares the results to expected.json. Exit code 1 on any mismatch.

What this does NOT cover: the LLM steps of the skill (finding prospects,
classifying them as Individual/Segment/Company, rating dimensions, writing
openers). input.json stands in for that output. See evals/README.md.

Usage:
    python3 evals/pipeline/run.py [-v]
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "skills" / "signal-scout" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import finalize  # noqa: E402
import verify_sources  # noqa: E402
from signal_scout_core import compute_score  # noqa: E402

PROSPECT_KINDS = finalize.PROSPECT_KINDS


def fake_network(pages: dict):
    def fetch_text(url, timeout):
        page = pages.get(url)
        if page is None:
            return None, ""
        return page.get("status", 200), page.get("text", "")

    def fetch_wayback(url, timeout):
        snap = (pages.get(url) or {}).get("wayback")
        if not snap:
            return "", "", ""
        return "https://web.archive.org/web/" + snap["date"] + "/" + url, snap["date"], snap["text"]

    def fetch_archive_ph(url, timeout):
        text = (pages.get(url) or {}).get("archive_ph")
        if not text:
            return "", ""
        return "https://archive.ph/newest/" + url, text

    return fetch_text, fetch_wayback, fetch_archive_ph


def run_verify(data: dict, pages: dict) -> tuple[int, dict, dict]:
    """Run verify_sources.main() offline. Returns (exit_code, annotated, handoff)."""
    fetch_text, fetch_wayback, fetch_archive_ph = fake_network(pages)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src, annotated, handoff = tmp_path / "in.json", tmp_path / "out.json", tmp_path / "handoff.json"
        src.write_text(json.dumps(data), encoding="utf-8")
        argv = ["verify_sources.py", str(src), "--annotate-out", str(annotated), "--handoff-out", str(handoff)]
        code = 0
        with mock.patch.object(verify_sources, "fetch_text", fetch_text), \
                mock.patch.object(verify_sources, "fetch_wayback", fetch_wayback), \
                mock.patch.object(verify_sources, "fetch_archive_ph", fetch_archive_ph), \
                mock.patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                verify_sources.main()
            except SystemExit as exc:
                code = int(exc.code or 0)
        return (
            code,
            json.loads(annotated.read_text(encoding="utf-8")),
            json.loads(handoff.read_text(encoding="utf-8")),
        )


def grade_case(case_dir: Path) -> list[str]:
    """Return a list of failure messages (empty list = case passed)."""
    data = json.loads((case_dir / "input.json").read_text(encoding="utf-8"))
    expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
    pages_file = case_dir / "pages.json"
    pages = json.loads(pages_file.read_text(encoding="utf-8")) if pages_file.exists() else {}
    failures: list[str] = []

    # 1. Validation. Each expected substring must match an error, and the error count must match.
    errors = finalize.validate(data)
    want_errors = expected.get("validate_errors", [])
    for needle in want_errors:
        if not any(needle in err for err in errors):
            failures.append(f"validate: expected an error containing {needle!r}, got {errors}")
    if len(errors) != len(want_errors):
        failures.append(f"validate: expected {len(want_errors)} error(s), got {len(errors)}: {errors}")

    # 2. Score formula, on every prospect that the case pins a score for.
    for kind, prospect_type in PROSPECT_KINDS.items():
        for item in data.get(kind) or []:
            key = f"{kind}/{item.get('name')}"
            want = (expected.get("prospects") or {}).get(key, {}).get("computed_score")
            if want is None:
                continue
            got = compute_score(prospect_type, item.get("dimensions") or {})
            if got != want:
                failures.append(f"{key}: compute_score expected {want}, got {got}")

    if "verify_exit" not in expected:
        return failures

    # 3. Verification, opener grounding, handoff filtering, exit code.
    code, annotated, handoff = run_verify(data, pages)
    if code != expected["verify_exit"]:
        failures.append(f"verify_sources: expected exit {expected['verify_exit']}, got {code}")

    kept = {f"{kind}/{i.get('name')}" for kind in PROSPECT_KINDS for i in handoff.get(kind) or []}
    for kind in PROSPECT_KINDS:
        for item in annotated.get(kind) or []:
            key = f"{kind}/{item.get('name')}"
            want = (expected.get("prospects") or {}).get(key)
            if want is None:
                failures.append(f"{key}: not listed in expected.json")
                continue
            if "tier" in want and item.get("verification_tier") != want["tier"]:
                failures.append(f"{key}: tier expected {want['tier']!r}, got {item.get('verification_tier')!r} "
                                f"({item.get('verification_note')})")
            if "note_contains" in want and want["note_contains"] not in str(item.get("verification_note", "")):
                failures.append(f"{key}: verification_note should contain {want['note_contains']!r}, "
                                f"got {item.get('verification_note')!r}")
            if "opener_flagged" in want and bool(item.get("opener_grounding_note")) != want["opener_flagged"]:
                failures.append(f"{key}: opener_flagged expected {want['opener_flagged']}, "
                                f"got {bool(item.get('opener_grounding_note'))}")
            if "in_handoff" in want and (key in kept) != want["in_handoff"]:
                failures.append(f"{key}: in_handoff expected {want['in_handoff']}, got {key in kept}")
    return failures


def main() -> int:
    verbose = "-v" in sys.argv[1:]
    case_dirs = sorted(p for p in (HERE / "cases").iterdir() if p.is_dir())
    failed = 0
    for case_dir in case_dirs:
        failures = grade_case(case_dir)
        print(f"{'PASS' if not failures else 'FAIL'}  {case_dir.name}")
        if failures:
            failed += 1
            for msg in failures:
                print(f"      - {msg}")
        elif verbose:
            print("      all checks matched expected.json")
    print(f"\n{len(case_dirs) - failed}/{len(case_dirs)} pipeline cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
