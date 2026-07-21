#!/usr/bin/env python3
"""Regression tests for verify_sources.py's HTTP-status handling.

Run: python3 test_verify_sources.py    (stdlib only; mocks the network)

These exist because the rate-limit special case shipped Reddit-only: the
branch that treats a throttled fetch as "unverified, not dead" checked
`is_reddit(url)` before checking the status code. Real dogfooding hit this
directly — heavy Hacker News fetching in one run got a later run's IP
rate-limited (HTTP 429), and every one of those live, real threads was
recorded as TIER_BROKEN ("unreachable or invalid") instead of TIER_SNIPPET_ONLY.

The invariant this defends: HTTP 429 means "you are being throttled," on any
domain, full stop. It is never evidence a source is dead, so it must never
be indistinguishable from a 404 or a DNS failure in the output.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verify_sources
from signal_scout_core import TIER_BROKEN, TIER_SNIPPET_ONLY, TIER_VERIFIED

DATE_RE = r"^\d{4}-\d{2}-\d{2}$"

REAL_PAGE = (
    "Navigation Home About. " * 50
    + "We've been tracking inventory in a giant Google Sheet for two years "
    "and it takes about six hours every single week to reconcile."
    + " Related discussions. " * 50
)
EVIDENCE = (
    "We've been tracking inventory in a giant Google Sheet for two years "
    "and it takes about six hours every single week to reconcile."
)


NO_ARCHIVE = ("", "", "")


def run_verify(prospects: dict, wayback: tuple[str, str, str] = NO_ARCHIVE) -> dict:
    """Write `prospects` to a temp file, run main() with --annotate-out, return the annotated JSON.

    Always mocks fetch_wayback (default: no archived copy) so failure-path tests
    never hit archive.org for real."""
    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "in.json"
        output_path = Path(tmp) / "out.json"
        input_path.write_text(json.dumps(prospects), encoding="utf-8")
        argv = ["verify_sources.py", str(input_path), "--annotate-out", str(output_path)]
        with mock.patch.object(verify_sources, "fetch_wayback", return_value=wayback):
            with mock.patch.object(sys, "argv", argv):
                try:
                    verify_sources.main()
                except SystemExit:
                    pass
        return json.loads(output_path.read_text(encoding="utf-8"))


class TestRateLimitHandling(unittest.TestCase):
    def _one_prospect(self, url: str = "https://news.ycombinator.com/item?id=1") -> dict:
        return {"individuals": [{"name": "test", "source_url": url, "evidence": EVIDENCE}]}

    def test_429_on_non_reddit_domain_is_snippet_only_not_broken(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(429, "")):
            result = run_verify(self._one_prospect("https://news.ycombinator.com/item?id=1"))
        tier = result["individuals"][0]["verification_tier"]
        self.assertEqual(tier, TIER_SNIPPET_ONLY, "a 429 must never be reported as TIER_BROKEN")

    def test_429_on_reddit_is_also_snippet_only(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(429, "")):
            result = run_verify(self._one_prospect("https://www.reddit.com/r/test/comments/1"))
        self.assertEqual(result["individuals"][0]["verification_tier"], TIER_SNIPPET_ONLY)

    def test_403_on_reddit_is_snippet_only(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(403, "")):
            result = run_verify(self._one_prospect("https://www.reddit.com/r/test/comments/1"))
        self.assertEqual(result["individuals"][0]["verification_tier"], TIER_SNIPPET_ONLY)

    def test_403_on_non_reddit_domain_is_broken(self):
        """403 elsewhere is left as a genuine failure — it may mean truly
        forbidden/gated content, not just an anti-bot wall like Reddit's."""
        with mock.patch.object(verify_sources, "fetch_text", return_value=(403, "")):
            result = run_verify(self._one_prospect("https://example.com/some-page"))
        self.assertEqual(result["individuals"][0]["verification_tier"], TIER_BROKEN)

    def test_404_is_still_broken(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(404, "")):
            result = run_verify(self._one_prospect("https://news.ycombinator.com/item?id=1"))
        self.assertEqual(result["individuals"][0]["verification_tier"], TIER_BROKEN)

    def test_200_with_matching_evidence_still_verifies(self):
        """Guard against the fix accidentally swallowing the normal success path."""
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            result = run_verify(self._one_prospect("https://news.ycombinator.com/item?id=1"))
        self.assertEqual(result["individuals"][0]["verification_tier"], TIER_VERIFIED)


class TestVerifiedAtStamp(unittest.TestCase):
    def test_stamped_on_success(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            result = run_verify({"individuals": [{
                "name": "test", "source_url": "https://news.ycombinator.com/item?id=1", "evidence": EVIDENCE,
            }]})
        self.assertRegex(result["individuals"][0]["verified_at"], DATE_RE)

    def test_stamped_even_on_broken_source(self):
        """verified_at records when the check ran, not whether it passed —
        a broken source was still checked at a point in time."""
        with mock.patch.object(verify_sources, "fetch_text", return_value=(404, "")):
            result = run_verify({"individuals": [{
                "name": "test", "source_url": "https://example.com/dead", "evidence": EVIDENCE,
            }]})
        self.assertRegex(result["individuals"][0]["verified_at"], DATE_RE)


class TestOpenerGrounding(unittest.TestCase):
    def _prospect(self, opener: str) -> dict:
        return {"individuals": [{
            "name": "test",
            "source_url": "https://news.ycombinator.com/item?id=1",
            "evidence": EVIDENCE,
            "opener": opener,
        }]}

    def test_opener_grounded_in_evidence_is_not_flagged(self):
        grounded = "Saw you mentioned reconciling inventory in a Google Sheet every week — sounds brutal."
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            result = run_verify(self._prospect(grounded))
        self.assertNotIn("opener_grounding_note", result["individuals"][0])

    def test_opener_inventing_unrelated_specifics_is_flagged(self):
        invented = "Congrats on raising a Series B and hiring 10 engineers next quarter."
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            result = run_verify(self._prospect(invented))
        self.assertIn("opener_grounding_note", result["individuals"][0])

    def test_empty_opener_is_not_flagged(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            result = run_verify(self._prospect(""))
        self.assertNotIn("opener_grounding_note", result["individuals"][0])

    def test_flagged_opener_does_not_fail_the_run(self):
        """This is a softer signal than verification_tier — it must not trip
        the same exit(1) that broken/unsupported sources do."""
        invented = "Congrats on raising a Series B and hiring 10 engineers next quarter."
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            with tempfile.TemporaryDirectory() as tmp:
                input_path = Path(tmp) / "in.json"
                input_path.write_text(json.dumps(self._prospect(invented)), encoding="utf-8")
                argv = ["verify_sources.py", str(input_path)]
                with mock.patch.object(sys, "argv", argv):
                    try:
                        verify_sources.main()
                        exited_with = 0
                    except SystemExit as exc:
                        exited_with = exc.code
        self.assertEqual(exited_with, 0)


class TestWaybackFallback(unittest.TestCase):
    def _one_prospect(self, url: str = "https://example.com/gone") -> dict:
        return {"individuals": [{"name": "test", "source_url": url, "evidence": EVIDENCE}]}

    def test_dead_link_rescued_by_archive(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(404, "")):
            result = run_verify(
                self._one_prospect(),
                wayback=("https://web.archive.org/web/2026/https://example.com/gone", "20260101", REAL_PAGE),
            )
        prospect = result["individuals"][0]
        self.assertEqual(prospect["verification_tier"], TIER_VERIFIED)
        self.assertIn("Wayback", prospect["verification_note"])

    def test_dead_link_with_no_archive_stays_broken(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(404, "")):
            result = run_verify(self._one_prospect())
        self.assertEqual(result["individuals"][0]["verification_tier"], TIER_BROKEN)

    def test_thin_page_rescued_by_archive(self):
        """A JS-rendered page (too little text) should try the archive before
        settling for Unverified."""
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, "tiny spa shell")):
            result = run_verify(
                self._one_prospect("https://example.com/spa"),
                wayback=("https://web.archive.org/web/2026/https://example.com/spa", "20260201", REAL_PAGE),
            )
        self.assertEqual(result["individuals"][0]["verification_tier"], TIER_VERIFIED)

    def test_reddit_403_rescued_by_archive(self):
        """Reddit's bot wall is exactly what the archive route recovers from —
        an archived thread upgrades snippet-only to a real containment check."""
        with mock.patch.object(verify_sources, "fetch_text", return_value=(403, "")):
            result = run_verify(
                self._one_prospect("https://www.reddit.com/r/test/comments/1"),
                wayback=("https://web.archive.org/web/2026/reddit", "20260301", REAL_PAGE),
            )
        self.assertEqual(result["individuals"][0]["verification_tier"], TIER_VERIFIED)


class TestBattlecardVerification(unittest.TestCase):
    def _data(self, competitor_mentioned: str = "") -> dict:
        individual = {"name": "test", "source_url": "https://news.ycombinator.com/item?id=1", "evidence": EVIDENCE}
        if competitor_mentioned:
            individual["competitor_mentioned"] = competitor_mentioned
        return {
            "individuals": [individual],
            "competitive_context": {
                "top_competitors": ["SheetTracker"],
                "battlecard": [{
                    "competitor": "SheetTracker",
                    "claim": "Users complain reconciliation takes hours",
                    "evidence": EVIDENCE,
                    "source_url": "https://news.ycombinator.com/item?id=2",
                }],
            },
        }

    def test_battlecard_entry_gets_verified(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            result = run_verify(self._data())
        entry = result["competitive_context"]["battlecard"][0]
        self.assertEqual(entry["verification_tier"], TIER_VERIFIED)
        self.assertRegex(entry["verified_at"], DATE_RE)

    def test_corroborated_entry_counts_mentions(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            result = run_verify(self._data(competitor_mentioned="SheetTracker"))
        entry = result["competitive_context"]["battlecard"][0]
        self.assertEqual(entry["corroboration_count"], 1)
        self.assertNotIn("corroboration_note", entry)

    def test_single_source_entry_flagged(self):
        with mock.patch.object(verify_sources, "fetch_text", return_value=(200, REAL_PAGE)):
            result = run_verify(self._data())
        entry = result["competitive_context"]["battlecard"][0]
        self.assertEqual(entry["corroboration_count"], 0)
        self.assertIn("single-source", entry["corroboration_note"])

    def test_disqualified_battlecard_entry_does_not_fail_run(self):
        """A fabricated battlecard claim is dropped, not run-fatal — prospects
        alone decide the exit code."""
        data = self._data()
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "in.json"
            handoff_path = Path(tmp) / "handoff.json"
            input_path.write_text(json.dumps(data), encoding="utf-8")

            def fetch(url, timeout):
                if "item?id=2" in url:
                    return 200, "Completely unrelated page about gardening tips and tomato varieties. " * 20
                return 200, REAL_PAGE

            argv = ["verify_sources.py", str(input_path), "--handoff-out", str(handoff_path)]
            with mock.patch.object(verify_sources, "fetch_text", side_effect=fetch):
                with mock.patch.object(verify_sources, "fetch_wayback", return_value=NO_ARCHIVE):
                    with mock.patch.object(sys, "argv", argv):
                        try:
                            verify_sources.main()
                            exited_with = 0
                        except SystemExit as exc:
                            exited_with = exc.code
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        self.assertEqual(exited_with, 0)
        self.assertNotIn("battlecard", handoff.get("competitive_context", {}))


class TestTextExtractor(unittest.TestCase):
    def test_meta_and_ldjson_harvested_from_spa_shell(self):
        html = (
            '<html><head>'
            f'<meta property="og:description" content="{EVIDENCE}">'
            '<script type="application/ld+json">{"@type":"Article","headline":"Inventory pain"}</script>'
            '<script>var app = "should not appear";</script>'
            '</head><body><div id="root"></div></body></html>'
        )
        parser = verify_sources._TextExtractor()
        parser.feed(html)
        text = parser.text()
        self.assertIn("giant Google Sheet", text)
        self.assertIn("Inventory pain", text)
        self.assertNotIn("should not appear", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
