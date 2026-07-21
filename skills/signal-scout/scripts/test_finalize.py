#!/usr/bin/env python3
"""Tests for finalize.py's offline pieces: validation and CSV export.

The subprocess steps (verify/report/diff) are covered by their own scripts'
tests; these tests exercise only what finalize.py adds itself. No network.
"""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from finalize import CSV_COLUMNS, next_action_for, validate, write_csv


def valid_individual() -> dict:
    dims = {"pain_strength": 4, "product_fit": 4, "timing": 4, "reachability": 3, "evidence_quality": 3}
    return {
        "name": "Jane Doe", "stage": "High intent",
        "score": 74,  # matches compute_score("individual", dims)
        "pain_signal": "p", "evidence": "e", "why_fit": "w", "why_now": "n",
        "source_title": "t", "source_url": "https://example.com/post",
        "source_type": "Forum", "signal_date": "2026-07-01",
        "suggested_channel": "Forum reply", "opener": "hi", "caution": "c",
        "dimensions": dims,
    }


def valid_report() -> dict:
    return {
        "title": "T", "product": "P", "product_url": "https://example.com",
        "target_customer": "c", "search_scope": "s", "generated_at": "2026-07-21",
        "verdict": "v", "outreach_plan": {"angle": "a"}, "limits": ["l"],
        "individuals": [valid_individual()],
    }


class ValidateTests(unittest.TestCase):
    def test_valid_report_passes(self):
        self.assertEqual(validate(valid_report()), [])

    def test_missing_top_level_field(self):
        data = valid_report()
        del data["verdict"]
        self.assertTrue(any("verdict" in e for e in validate(data)))

    def test_no_prospects_fails(self):
        data = valid_report()
        del data["individuals"]
        self.assertTrue(any("non-empty" in e for e in validate(data)))

    def test_score_drift_flagged(self):
        data = valid_report()
        data["individuals"][0]["score"] = 15
        self.assertTrue(any("does not match" in e for e in validate(data)))

    def test_prospect_schema_violation_named(self):
        data = valid_report()
        data["individuals"][0]["stage"] = "Very keen"
        errors = validate(data)
        self.assertTrue(any("Jane Doe" in e and "stage" in e for e in errors))


class CsvTests(unittest.TestCase):
    def test_next_action_per_type(self):
        self.assertEqual(next_action_for("individuals", {"opener": "hi"}), "hi")
        self.assertEqual(next_action_for("individuals", {"suggested_channel": "DM"}), "DM")
        self.assertEqual(next_action_for("segments", {"content_angle": "angle"}), "angle")
        self.assertEqual(next_action_for("companies", {"bd_angle": "pitch"}), "pitch")

    def test_write_csv_columns_and_rows(self):
        data = valid_report()
        data["individuals"][0]["verification_tier"] = "verified"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "prospects.csv"
            self.assertEqual(write_csv(data, out), 1)
            with out.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
        self.assertEqual(rows[0], list(CSV_COLUMNS))
        row = dict(zip(rows[0], rows[1]))
        self.assertEqual(row["type"], "individual")
        self.assertEqual(row["verification"], "Verified")
        self.assertEqual(row["next_action"], "hi")


class ClientSectionValidationTests(unittest.TestCase):
    def _company(self, **extra) -> dict:
        company = {
            "name": "Acme", "stage": "High intent", "score": 80,
            "source_url": "https://example.com/acme",
            "execution_path": "Self-serve program", "contact_path": "partner page",
            "dimensions": {"strategic_fit": 4, "timing": 4, "execution_ease": 4, "evidence_quality": 4},
        }
        company.update(extra)
        return company

    def test_tier_without_rationale_fails(self):
        data = valid_report()
        data["companies"] = [self._company(tier=1)]
        errors = validate(data)
        self.assertTrue(any("tier_rationale" in e for e in errors))

    def test_invalid_tier_value_fails(self):
        data = valid_report()
        data["companies"] = [self._company(tier=5, tier_rationale="r")]
        errors = validate(data)
        self.assertTrue(any("tier must be 1, 2, or 3" in e for e in errors))

    def test_valid_tiered_company_passes(self):
        data = valid_report()
        data["companies"] = [self._company(tier=2, tier_rationale="warm BD only")]
        self.assertEqual(validate(data), [])

    def test_battlecard_missing_fields_and_url_fail(self):
        data = valid_report()
        data["competitive_context"] = {"battlecard": [
            {"competitor": "Comp", "claim": "", "evidence": "e", "counter_angle": "a", "source_url": "not-a-url"},
        ]}
        errors = validate(data)
        self.assertTrue(any("missing claim" in e for e in errors))
        self.assertTrue(any("source_url" in e for e in errors))

    def test_valid_battlecard_passes(self):
        data = valid_report()
        data["competitive_context"] = {"battlecard": [
            {"competitor": "Comp", "claim": "c", "evidence": "e",
             "counter_angle": "a", "source_url": "https://example.com/c"},
        ]}
        self.assertEqual(validate(data), [])


if __name__ == "__main__":
    unittest.main()
