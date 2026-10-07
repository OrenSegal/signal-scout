#!/usr/bin/env python3
"""No-people mode: prove no person data leaks into filtered output.

Every leak test is a pair. The fixture is first checked to CONTAIN every
planted person string (negative control), then the filtered output is checked
to contain NONE of them. Covers people_filter directly, finalize.py end to end
(JSON, handoff, HTML, CSV), verification-before-redaction ordering, and the
MCP server's _finish_run with stubbed anthropic/mcp modules. No network.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import finalize
import verify_sources
from people_filter import (
    NAME_PLACEHOLDER,
    drop_people,
    is_personal_url,
    redact_people,
    strip_people,
)
from signal_scout_core import TIER_VERIFIED

SCRIPTS = Path(__file__).resolve().parent
MCP_SERVER = SCRIPTS.parents[2] / "mcp-server"
REAL_RUN = subprocess.run

THREAD_URL = "https://www.reddit.com/r/devops/comments/abc123/flaky_ci_again/"
ISSUE_URL = "https://github.com/acme/ci-runner/issues/42"
COMPANY_URL = "https://acme.com/partners"

# Every string here identifies a person and must never reach filtered output.
PLANTED = (
    "Jane Doe",
    "janedoe",
    "devguy42",
    "linkedin.com/in/",
    "jane.doe@gmail.com",
    "x.com/janedoe",
    "x.com/someone",
    "bobbuilder",
)

SEGMENT_EVIDENCE = (
    "Flaky CI again, third time this week. @janedoe said the same thing and u/devguy42 "
    "had to rerun every pipeline by hand."
)


def individual() -> dict:
    dims = {"pain_strength": 4, "product_fit": 4, "timing": 4, "reachability": 3, "evidence_quality": 3}
    return {
        "name": "Jane Doe (@janedoe)", "stage": "High intent", "score": 74,
        "pain_signal": "CI keeps failing", "evidence": "my CI is broken again",
        "why_fit": "w", "why_now": "n", "source_title": "post",
        "source_url": "https://x.com/janedoe/status/123", "source_type": "Social post",
        "signal_date": "2026-09-01", "suggested_channel": "Reply on X",
        "opener": "Hi Jane, saw your CI post", "caution": "c", "dimensions": dims,
    }


def segment(name: str, url: str, evidence: str) -> dict:
    return {
        "name": name, "stage": "Problem aware", "score": 75,
        "pain_signal": "flaky CI", "evidence": evidence,
        "why_fit": "Same pain Jane Doe described", "why_now": "n",
        "source_title": "thread", "source_url": url, "source_type": "Forum",
        "signal_date": "2026-09-02", "content_angle": "Write about flaky CI",
        "proof_points": ["@bobbuilder's benchmark, quoted by Sam Lee", "see https://www.linkedin.com/in/janedoe"],
        "caution": "c",
        "dimensions": {"pain_strength": 4, "product_fit": 4, "timing": 3, "evidence_quality": 4},
    }


def company() -> dict:
    return {
        "name": "Acme", "domain": "acme.com", "role": "Integration/distribution partner",
        "stage": "Trigger present", "score": 70, "pain_signal": "p",
        "evidence": "Acme launched a partner program", "why_fit": "w", "why_now": "n",
        "source_title": "Partners", "source_url": COMPANY_URL, "source_type": "Company page",
        "signal_date": "2026-09-03", "execution_path": "Self-serve program",
        "contact_path": "partners@acme.com or ask jane.doe@gmail.com",
        "bd_angle": "b", "what_to_propose": "w", "caution": "c",
        "dimensions": {"strategic_fit": 4, "timing": 3, "execution_ease": 3, "evidence_quality": 4},
    }


def fixture() -> dict:
    return {
        "title": "CI Tool", "product": "P", "product_url": "https://ci.example",
        "target_customer": "devops leads", "search_scope": "s", "generated_at": "2026-10-06",
        "verdict": "Strong signal from Jane Doe and others",
        "search_queries_used": ["flaky ci", "from:janedoe ci"],
        "sources_consulted": [THREAD_URL, "https://www.linkedin.com/in/janedoe", "https://x.com/janedoe"],
        "individuals": [individual()],
        "segments": [
            segment("Teams with flaky CI", THREAD_URL, SEGMENT_EVIDENCE),
            segment("Runner users", "https://x.com/someone/status/9", "runner pain"),
        ],
        "companies": [company()],
        "patterns": [{"title": "Flaky CI", "count": 2, "insight": "Jane Doe and @janedoe-style posts"}],
        "outreach_plan": {"angle": "a", "first_step": "Reply to Jane Doe", "personalization_notes": "DM @janedoe"},
        "executive_summary": {"overview": "o", "key_findings": ["Jane Doe is the hottest lead"]},
        "competitive_context": {"battlecard": [
            {"competitor": "OldCI", "claim": "slow", "evidence": "per @janedoe it is slow",
             "source_url": ISSUE_URL, "counter_angle": "fast"},
            {"competitor": "OtherCI", "claim": "c", "evidence": "e",
             "source_url": "https://www.linkedin.com/in/bob", "counter_angle": "x"},
        ]},
        "limits": ["Classified Jane Doe as Individual, not Company"],
    }


def assert_no_leak(test: unittest.TestCase, text: str, where: str) -> None:
    lowered = text.lower()
    for needle in PLANTED:
        test.assertNotIn(needle.lower(), lowered, f"{needle!r} leaked into {where}")


class NegativeControl(unittest.TestCase):
    def test_fixture_contains_every_planted_string(self):
        raw = json.dumps(fixture()).lower()
        for needle in PLANTED:
            self.assertIn(needle.lower(), raw, f"fixture is missing {needle!r}; the leak tests would prove nothing")


class PersonalUrlTests(unittest.TestCase):
    def test_classification(self):
        personal = [
            "https://www.linkedin.com/in/janedoe", "https://x.com/janedoe/status/1", "https://twitter.com/janedoe",
            "https://www.reddit.com/user/devguy42", "https://reddit.com/u/devguy42",
            "https://news.ycombinator.com/user?id=pg", "https://github.com/janedoe",
            "https://bsky.app/profile/jane.bsky.social", "https://medium.com/@jane/post",
            "https://mastodon.social/@jane",
        ]
        public = [
            THREAD_URL, ISSUE_URL, COMPANY_URL, "https://github.com/acme/repo",
            "https://www.linkedin.com/company/acme", "https://news.ycombinator.com/item?id=1",
            "https://x.com/search?q=ci",
        ]
        for url in personal:
            self.assertTrue(is_personal_url(url), url)
        for url in public:
            self.assertFalse(is_personal_url(url), url)


class StripPeopleTests(unittest.TestCase):
    def test_no_person_data_leaks(self):
        out, stats = strip_people(fixture())
        assert_no_leak(self, json.dumps(out), "strip_people output")
        self.assertNotIn("individuals", out)
        self.assertIs(out["people"], False)
        self.assertEqual(stats["individuals_removed"], 1)
        # Segment on x.com/someone and battlecard on a LinkedIn profile are dropped whole.
        self.assertEqual(stats["dropped_for_personal_source"], 2)

    def test_keeps_non_person_content(self):
        out, _ = strip_people(fixture())
        self.assertEqual([s["name"] for s in out["segments"]], ["Teams with flaky CI"])
        self.assertEqual(out["segments"][0]["source_url"], THREAD_URL)
        self.assertIn(THREAD_URL, out["sources_consulted"])
        self.assertEqual(len(out["sources_consulted"]), 1)
        self.assertIn("partners@acme.com", out["companies"][0]["contact_path"])
        self.assertEqual(out["companies"][0]["domain"], "acme.com")
        self.assertEqual(out["competitive_context"]["battlecard"][0]["source_url"], ISSUE_URL)
        self.assertIn(NAME_PLACEHOLDER, out["segments"][0]["evidence"])
        self.assertTrue(any(str(x).startswith("No-people mode:") for x in out["limits"]))

    def test_idempotent_keeps_original_note(self):
        once, _ = strip_people(fixture())
        twice, stats = strip_people(once)
        self.assertEqual(once, twice)
        self.assertEqual(stats["redactions"], 0)

    def test_input_not_mutated(self):
        data = fixture()
        strip_people(data)
        self.assertEqual(data, fixture())


class VerifyThenRedactOrdering(unittest.TestCase):
    """A segment quote containing a handle must still verify: drop first,
    verify the unredacted quote, redact afterwards."""

    def test_handle_in_quote_verifies_then_is_redacted(self):
        public, stats = drop_people(fixture())
        filler = " Unrelated discussion about build caches, runners, and deploy queues." * 12
        pages = {
            THREAD_URL: "Some header." + filler + " " + SEGMENT_EVIDENCE + filler,
            COMPANY_URL: "Acme launched a partner program for integrations." + filler,
            ISSUE_URL: "per @janedoe it is slow, and other users agree." + filler,
        }

        def fetch_text(url, timeout):
            return (200, pages[url]) if url in pages else (None, "")

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "analysis.json"
            handoff = Path(tmp) / "handoff.json"
            src.write_text(json.dumps(public), encoding="utf-8")
            argv = ["verify_sources.py", str(src), "--annotate-out", str(src), "--handoff-out", str(handoff)]
            with mock.patch.object(verify_sources, "fetch_text", fetch_text), \
                    mock.patch.object(verify_sources, "fetch_wayback", lambda u, t: ("", "", "")), \
                    mock.patch.object(verify_sources, "fetch_archive_ph", lambda u, t: ("", "")), \
                    mock.patch.object(sys, "argv", argv), \
                    contextlib.redirect_stdout(io.StringIO()):
                try:
                    verify_sources.main()
                except SystemExit as exc:
                    self.assertIn(exc.code, (0, None))
            annotated = json.loads(src.read_text(encoding="utf-8"))
            self.assertEqual(annotated["segments"][0]["verification_tier"], TIER_VERIFIED)

            final = finalize.finish_people_filter(src, annotated, stats, handoff)
            self.assertEqual(final["segments"][0]["verification_tier"], TIER_VERIFIED)
            assert_no_leak(self, src.read_text(encoding="utf-8"), "annotated JSON")
            assert_no_leak(self, handoff.read_text(encoding="utf-8"), "handoff.json")


class FinalizeEndToEnd(unittest.TestCase):
    def run_finalize(self, tmp: Path, *flags: str, data: dict | None = None) -> tuple[Path, str]:
        src = tmp / "analysis-2026-10-06.json"
        src.write_text(json.dumps(data or fixture()), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "finalize.py"), str(src), "--skip-verify", *flags],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return src, result.stdout

    def test_no_people_flag_outputs_are_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src, stdout = self.run_finalize(tmp_path, "--no-people")
            public = tmp_path / "public"
            outputs = {
                "public JSON": public / src.name,
                "HTML report": public / "signal-scout-report.html",
                "CSV": public / "prospects.csv",
            }
            for where, path in outputs.items():
                self.assertTrue(path.exists(), where)
                assert_no_leak(self, path.read_text(encoding="utf-8"), where)
            assert_no_leak(self, stdout, "finalize stdout")
            # Private draft untouched; nothing written beside it.
            self.assertEqual(json.loads(src.read_text(encoding="utf-8")), fixture())
            self.assertFalse((tmp_path / "prospects.csv").exists())
            with (public / "prospects.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual({r["type"] for r in rows}, {"segment", "company"})
            self.assertEqual([r["domain"] for r in rows if r["type"] == "company"], ["acme.com"])

    def test_people_false_in_json_enables_filter(self):
        data = fixture()
        data["people"] = False
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src, _ = self.run_finalize(tmp_path, data=data)
            assert_no_leak(self, (tmp_path / "public" / "signal-scout-report.html").read_text(encoding="utf-8"), "HTML")

    def test_default_mode_keeps_individuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self.run_finalize(tmp_path)
            self.assertIn("Jane Doe", (tmp_path / "signal-scout-report.html").read_text(encoding="utf-8"))
            self.assertFalse((tmp_path / "public").exists())

    def test_only_people_fails_clearly(self):
        data = fixture()
        for key in ("segments", "companies"):
            data.pop(key)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "analysis.json"
            src.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "finalize.py"), str(src), "--no-people", "--validate-only"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("no Segments or Companies left", result.stdout)


class GenerateReportDirect(unittest.TestCase):
    def test_people_false_never_renders_a_person(self):
        data = fixture()
        data["people"] = False
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "in.json", Path(tmp) / "out.html"
            src.write_text(json.dumps(data), encoding="utf-8")
            subprocess.run([sys.executable, str(SCRIPTS / "generate_report.py"), str(src), str(out), "--no-history"],
                           check=True, capture_output=True)
            assert_no_leak(self, out.read_text(encoding="utf-8"), "generate_report HTML")


def load_server():
    """Import mcp-server/server.py with anthropic and mcp stubbed (CI installs neither)."""
    stubs = {}
    if "anthropic" not in sys.modules:
        anthropic = types.ModuleType("anthropic")
        anthropic.Anthropic = object
        stubs["anthropic"] = anthropic
    fastmcp = types.ModuleType("mcp.server.fastmcp")

    class FastMCP:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self):
            return lambda fn: fn

        def run(self, **kwargs):
            pass

    fastmcp.FastMCP = FastMCP
    stubs.update({
        "mcp": types.ModuleType("mcp"),
        "mcp.server": types.ModuleType("mcp.server"),
        "mcp.server.fastmcp": fastmcp,
    })
    sys.path.insert(0, str(MCP_SERVER))
    try:
        with mock.patch.dict(sys.modules, stubs):
            sys.modules.pop("server", None)
            import server  # noqa: PLC0415
            return server
    finally:
        sys.path.remove(str(MCP_SERVER))


class McpServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def fake_run(self, cmd, **kwargs):
        """verify_sources is replaced (no network): it annotates and writes a
        handoff from the unredacted text, and prints names, as the real one does.
        generate_report runs for real."""
        if cmd[1].endswith("verify_sources.py"):
            src = Path(cmd[2])
            data = json.loads(src.read_text(encoding="utf-8"))
            for kind in ("individuals", "segments", "companies"):
                for item in data.get(kind) or []:
                    item["verification_tier"] = TIER_VERIFIED
            Path(cmd[cmd.index("--annotate-out") + 1]).write_text(json.dumps(data), encoding="utf-8")
            Path(cmd[cmd.index("--handoff-out") + 1]).write_text(json.dumps(data), encoding="utf-8")
            names = [i["name"] for k in ("individuals", "segments") for i in data.get(k) or []]
            stdout = "Verified: " + ", ".join(names) + " | evidence: " + data["segments"][0]["evidence"]
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
        return REAL_RUN(cmd, **kwargs)

    def finish(self, tmp: str, people: bool) -> tuple[dict, str]:
        with mock.patch.object(self.server, "OUTPUT_DIR", Path(tmp)), \
                mock.patch.object(self.server.subprocess, "run", self.fake_run), \
                mock.patch.object(self.server, "record_call", lambda **kw: 0.0):
            result = self.server._finish_run(
                fixture(), None, product_url="https://ci.example", depth="standard", focus="all", people=people,
            )
        written = "".join(p.read_text(encoding="utf-8") for p in Path(tmp).rglob("*") if p.is_file())
        return result, written

    def test_default_is_no_people(self):
        import inspect
        for tool in (self.server.classify_and_score, self.server.find_first_customers):
            self.assertIs(inspect.signature(tool).parameters["people"].default, False)

    def test_no_people_leaks_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, written = self.finish(tmp, people=False)
        self.assertEqual(result["individuals"], 0)
        self.assertIs(result["people"], False)
        assert_no_leak(self, json.dumps(result), "tool result")
        assert_no_leak(self, written, "files the server wrote")

    def test_people_true_keeps_individuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, written = self.finish(tmp, people=True)
        self.assertEqual(result["individuals"], 1)
        self.assertIn("Jane Doe", written)

    def test_focus_individuals_requires_people(self):
        with self.assertRaises(ValueError):
            self.server._validate_depth_focus("standard", "individuals", people=False)

    def test_prompt_tells_model_to_skip_people(self):
        captured = {}

        def fake_complete(system, prompt, tools):
            captured["prompt"] = prompt
            return {}, None

        with mock.patch.object(self.server, "_complete", fake_complete):
            self.server._run_classification("u", "", [{"source_url": "s", "evidence": "e"}], "quick", "all")
        self.assertIn(self.server.NO_PEOPLE_INSTRUCTION, captured["prompt"])


class RedactPeopleUnit(unittest.TestCase):
    def test_known_limit_bare_name_never_recorded_as_individual(self):
        """Documented boundary (COMPLIANCE.md): pattern matching, not NER. A bare
        name that was never an Individual and has no handle or URL stays."""
        out, _ = strip_people(fixture())
        self.assertIn("Sam Lee", json.dumps(out))

    def test_non_personal_urls_untouched(self):
        text = f"See {THREAD_URL} and {ISSUE_URL}, also https://www.linkedin.com/in/janedoe."
        out, n = redact_people(text, [])
        self.assertIn(THREAD_URL, out)
        self.assertIn(ISSUE_URL, out)
        self.assertNotIn("linkedin.com/in", out)
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
