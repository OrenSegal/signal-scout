#!/usr/bin/env python3
"""signal-scout MCP server — sells the research skill directly to other
agents (B2A), not just to a human running Claude Code.

Requires ANTHROPIC_API_KEY (or an `ant auth login` profile — the SDK picks
either up automatically). No payment provider is wired in yet: every call
is metered to usage.jsonl via usage_meter.py so the founder can see real
per-call cost before choosing x402 vs Stripe MPP and adding an actual gate
(see ../MONETIZATION.md). This is a v0 scaffold — smoke-test with a real
API key before treating it as production.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema import ANALYSIS_SCHEMA  # noqa: E402
from usage_meter import calls_today, record_call  # noqa: E402

SKILL_SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "signal-scout" / "scripts"
OUTPUT_DIR = Path(os.environ.get("SIGNAL_SCOUT_OUTPUT_DIR", str(Path.home() / ".signal-scout" / "reports")))
MODEL = os.environ.get("SIGNAL_SCOUT_MODEL", "claude-sonnet-5")
MAX_PAUSE_TURNS = 3  # server-tool loops resume automatically; cap resends so a stuck run can't loop forever

# No payment gate exists yet (see ../MONETIZATION.md) — this is the only thing
# standing between a reachable server and an unbounded Anthropic bill if it's
# ever exposed before billing is wired in. Raise it deliberately, not by removing it.
DAILY_CALL_CAP = int(os.environ.get("SIGNAL_SCOUT_DAILY_CALL_CAP", "20"))

DEPTH_LIMITS = {"quick": 5, "standard": 10, "deep": 20}
FOCUS_VALUES = {"all", "individuals", "segments", "companies", "competitor-chasers", "design-partners"}

SYSTEM_PROMPT = """You are signal-scout: turn a startup URL into an evidence-backed shortlist of \
first customers, market segments, and companies worth pitching, using PUBLIC SIGNALS ONLY.

Classify every candidate as exactly one of:
- Individual: one addressable person you could plausibly reply to, DM, or comment at.
- Segment: an audience or demand pattern, not a person.
- Company: an organization evaluated as a BD/partnership/account target.

Use web_search and web_fetch to find explicit demand, pain, workaround, switching, and timing \
signals across forums, social posts, reviews, GitHub issues, and company pages. Prefer original \
pages over search snippets. Log every query you actually issued in search_queries_used and every \
source you actually opened in sources_consulted.

Score Individuals on pain_strength/product_fit/timing/reachability/evidence_quality (0-5 each); \
Segments on pain_strength/product_fit/timing/evidence_quality; Companies on \
strategic_fit/timing/execution_ease/evidence_quality. Never claim a prospect is interested, has \
consented, or will buy — these are hypotheses based on public signals.

Do not bypass paywalls, login walls, or robots restrictions. Do not use data brokers, scraped \
contact databases, or infer protected traits. A "contact path" for a Company must be a public, \
self-serve channel — never a scraped personal email.

Output must conform exactly to the JSON schema you were given — no prose outside the JSON."""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / ant auth profile


def _tools() -> list[dict[str, Any]]:
    return [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 25},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 15},
    ]


def _add_usage(total: Any, extra: Any) -> dict[str, int]:
    fields = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    merged = {f: (getattr(total, f, 0) or 0) + (getattr(extra, f, 0) or 0) for f in fields}
    return merged


class _UsageTotal:
    """Plain object so usage_meter's getattr-based reads work on the summed dict too."""

    def __init__(self, values: dict[str, int]) -> None:
        for key, value in values.items():
            setattr(self, key, value)


def _run_research(product_url: str, depth: str, focus: str) -> tuple[dict[str, Any], _UsageTotal]:
    client = _client()
    max_prospects = DEPTH_LIMITS[depth]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user_prompt = (
        f"Research {product_url} and produce a signal-scout analysis. "
        f"Depth: {depth} (up to {max_prospects} total prospects across all types). "
        f"Focus: {focus}. Today's date: {today}."
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]

    def _call() -> Any:
        return client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            tools=_tools(),
            output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
            messages=messages,
        )

    response = _call()
    usage_totals = _add_usage(_UsageTotal({}), response.usage)

    turns = 0
    while response.stop_reason == "pause_turn" and turns < MAX_PAUSE_TURNS:
        messages.append({"role": "assistant", "content": response.content})
        response = _call()
        usage_totals = _add_usage(_UsageTotal(usage_totals), response.usage)
        turns += 1

    if response.stop_reason == "refusal":
        raise RuntimeError(
            "Research request was declined by safety classifiers "
            f"(stop_details={getattr(response, 'stop_details', None)})."
        )
    if response.stop_reason == "pause_turn":
        raise RuntimeError(f"Research did not finish within {MAX_PAUSE_TURNS} continuation turns.")

    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    if not text.strip():
        raise RuntimeError(f"No text output returned (stop_reason={response.stop_reason}).")
    analysis = json.loads(text)
    return analysis, _UsageTotal(usage_totals)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "product"


mcp = FastMCP(
    "signal-scout",
    instructions=(
        "Turns a startup URL into an evidence-backed shortlist of first customers, market "
        "segments, and companies worth pitching, using public signals only. Call "
        "find_first_customers with a product URL to get a scored report."
    ),
)


@mcp.tool()
def find_first_customers(product_url: str, depth: str = "standard", focus: str = "all") -> dict[str, Any]:
    """Research a startup URL and return an evidence-backed shortlist of first customers,
    market segments, and companies worth pitching, using public signals only.

    Args:
        product_url: The startup's URL, repo, or a one-line product description.
        depth: "quick" (<=5 prospects), "standard" (<=10, default), or "deep" (<=20).
        focus: "all" (default), "individuals", "segments", "companies",
            "competitor-chasers", or "design-partners".

    Returns a summary plus paths to the full JSON analysis and the standalone HTML report
    (verified via verify_sources.py --apply before the report is generated).
    """
    if depth not in DEPTH_LIMITS:
        raise ValueError(f"depth must be one of {sorted(DEPTH_LIMITS)}, got {depth!r}")
    if focus not in FOCUS_VALUES:
        raise ValueError(f"focus must be one of {sorted(FOCUS_VALUES)}, got {focus!r}")
    if calls_today() >= DAILY_CALL_CAP:
        raise RuntimeError(
            f"Daily call cap ({DAILY_CALL_CAP}) reached and no payment gate exists yet — "
            "refusing to spend more API budget today. Raise SIGNAL_SCOUT_DAILY_CALL_CAP "
            "once you've priced this deliberately (see ../MONETIZATION.md)."
        )

    analysis, usage = _run_research(product_url, depth, focus)

    slug = _slugify(analysis.get("title") or product_url)
    run_dir = OUTPUT_DIR / slug
    run_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    analysis_path = run_dir / f"analysis-{stamp}.json"
    analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "verify_sources.py"), str(analysis_path), "--apply"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    report_path = run_dir / f"report-{stamp}.html"
    generate = subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "generate_report.py"), str(analysis_path), str(report_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if generate.returncode != 0:
        raise RuntimeError(f"Report generation failed: {generate.stderr.strip()}")

    reloaded = json.loads(analysis_path.read_text(encoding="utf-8"))  # verify --apply may have edited it in place
    cost = record_call(product_url=product_url, depth=depth, focus=focus, usage=usage, model=MODEL)

    return {
        "verdict": reloaded.get("verdict"),
        "individuals": len(reloaded.get("individuals") or []),
        "segments": len(reloaded.get("segments") or []),
        "companies": len(reloaded.get("companies") or []),
        "analysis_path": str(analysis_path),
        "report_path": str(report_path),
        "source_verification": verify.stdout.strip(),
        "estimated_cost_usd": cost,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
