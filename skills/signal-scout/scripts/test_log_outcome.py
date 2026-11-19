#!/usr/bin/env python3
"""Tests for log_outcome.py and the recalibrate.py that reads its file. No network."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True)


class LogOutcomeTests(unittest.TestCase):
    def test_list_shows_a_record_logged_without_optional_flags(self):
        # --score, --source-type and --query-bucket are optional when logging.
        with tempfile.TemporaryDirectory() as tmp:
            log = str(Path(tmp) / "outcomes.jsonl")
            logged = run("log_outcome.py", log, "--name", "jdoe", "--type", "individual",
                         "--outcome", "replied", "--date", "2026-07-14")
            self.assertEqual(logged.returncode, 0, logged.stderr)
            listed = run("log_outcome.py", log, "--list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("jdoe", listed.stdout)
            self.assertIn("1 outcomes logged", listed.stdout)

    def test_list_shows_the_score_when_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = str(Path(tmp) / "outcomes.jsonl")
            run("log_outcome.py", log, "--name", "acme", "--type", "company", "--score", "82",
                "--outcome", "converted", "--date", "2026-07-14", "--source-type", "Forum")
            listed = run("log_outcome.py", log, "--list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertRegex(listed.stdout, r"Forum\s+82\s+converted")

    def test_recalibrate_reads_what_log_outcome_wrote(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = str(Path(tmp) / "outcomes.jsonl")
            for outcome in ("replied", "no_reply", "converted"):
                run("log_outcome.py", log, "--name", "n", "--type", "segment", "--outcome", outcome,
                    "--date", "2026-07-14", "--source-type", "Forum", "--query-bucket", "pain")
            out = run("recalibrate.py", log)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("67% across 3 logged prospects", out.stdout)
            self.assertRegex(out.stdout, r"Forum\s+n=3\s+67%")


if __name__ == "__main__":
    unittest.main()
