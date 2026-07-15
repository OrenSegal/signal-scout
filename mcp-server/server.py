#!/usr/bin/env python3
"""signal-scout MCP server — makes the research skill callable by other
agents (B2A distribution), not just usable by a human running Claude Code.
Free and self-hostable, on purpose — see ../MONETIZATION.md Section 7 for
why this stays a distribution channel into a paid hosted layer rather than
a metered product in its own right.

Two tools, deliberately split by what actually adds value on top of what a
capable calling agent (Claude Code included) already has for free:

- `classify_and_score` — the one to reach for by default. Takes findings the
  caller already gathered with its own web_search/web_fetch and does only
  what a bare LLM call doesn't do reliably: disciplined Individual/Segment/
  Company classification, per-type scoring, automated source verification,
  and a portable HTML report. No web tools, no re-researching — cheaper,
  and it doesn't pay to redo work the caller can already do itself.
- `find_first_customers` — does its own web research end-to-end. Only worth
  paying for when the caller has no web_search/web_fetch of its own; if the
  caller is Claude Code or similar, prefer `classify_and_score` — running a
  second research agent to duplicate tools the caller already has isn't a
  real value-add, it's just marked-up compute.

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

CLASSIFICATION_RULES = """Classify every candidate as exactly one of:
- Individual: one addressable person you could plausibly reply to, DM, or comment at.
- Segment: an audience or demand pattern, not a person.
- Company: an organization evaluated as a BD/partnership/account target.

Score Individuals on pain_strength/product_fit/timing/reachability/evidence_quality (0-5 each); \
Segments on pain_strength/product_fit/timing/evidence_quality; Companies on \
strategic_fit/timing/execution_ease/evidence_quality. Never claim a prospect is interested, has \
consented, or will buy — these are hypotheses based on public signals.

A "contact path" for a Company must be a public, self-serve channel — never a scraped personal \
email. Output must conform exactly to the JSON schema you were given — no prose outside the JSON."""

# Used by find_first_customers, which does its own web research. Most callers that
# already have their own web_search/web_fetch (Claude Code included) should reach for
# classify_and_score instead — see the module docstring and mcp-server/README.md for why.
RESEARCH_SYSTEM_PROMPT = f"""You are signal-scout: turn a startup URL into an evidence-backed \
shortlist of first customers, market segments, and companies worth pitching, using PUBLIC \
SIGNALS ONLY.

Use web_search and web_fetch to find explicit demand, pain, workaround, switching, and timing \
signals across forums, social posts, reviews, GitHub issues, and company pages. Prefer original \
pages over search snippets. Log every query you actually issued in search_queries_used and every \
source you actually opened in sources_consulted.

Do not bypass paywalls, login walls, or robots restrictions. Do not use data brokers, scraped \
contact databases, or infer protected traits.

{CLASSIFICATION_RULES}"""

# Used by classify_and_score, which takes findings the CALLER already gathered (its own
# web_search/web_fetch) and does only the part a bare LLM call doesn't do reliably:
# disciplined 3-type classification, per-type scoring, and citing only the given sources.
CLASSIFY_SYSTEM_PROMPT = f"""You are signal-scout's classification layer. You are given a list of \
findings someone else already researched (source URL, title, and the evidence text they found) —
do NOT invent additional prospects, additional evidence, or additional sources beyond what's \
provided. Your job is only to classify, score, and structure exactly these findings.

For each finding, decide whether it's usable evidence at all — a finding with no real pain, \
demand, or timing signal is not a qualified prospect and should be left out rather than forced in \
at a low score. Copy `source_url` and `evidence` from the input into your output verbatim (a \
downstream script re-fetches each URL and fuzzy-matches your `evidence` text against the live \
page — a paraphrase that drifts from the original evidence will fail that check).

{CLASSIFICATION_RULES}"""


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


def _complete(system: str, user_prompt: str, *, tools: list[dict[str, Any]] | None) -> tuple[dict[str, Any], _UsageTotal]:
    """Shared call+continuation+parse loop. `tools=None` skips web tools entirely —
    classify_and_score never needs them, which is most of why it's cheaper."""
    client = _client()
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]

    def _call() -> Any:
        kwargs: dict[str, Any] = dict(
            model=MODEL,
            max_tokens=16000,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
            messages=messages,
        )
        if tools:
            kwargs["tools"] = tools
        return client.messages.create(**kwargs)

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
            "Request was declined by safety classifiers "
            f"(stop_details={getattr(response, 'stop_details', None)})."
        )
    if response.stop_reason == "pause_turn":
        raise RuntimeError(f"Did not finish within {MAX_PAUSE_TURNS} continuation turns.")

    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    if not text.strip():
        raise RuntimeError(f"No text output returned (stop_reason={response.stop_reason}).")
    analysis = json.loads(text)
    return analysis, _UsageTotal(usage_totals)


def _run_research(product_url: str, depth: str, focus: str) -> tuple[dict[str, Any], _UsageTotal]:
    max_prospects = DEPTH_LIMITS[depth]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user_prompt = (
        f"Research {product_url} and produce a signal-scout analysis. "
        f"Depth: {depth} (up to {max_prospects} total prospects across all types). "
        f"Focus: {focus}. Today's date: {today}."
    )
    return _complete(RESEARCH_SYSTEM_PROMPT, user_prompt, tools=_tools())


def _run_classification(
    product_url: str, target_customer: str, findings: list[dict[str, Any]], depth: str, focus: str
) -> tuple[dict[str, Any], _UsageTotal]:
    max_prospects = DEPTH_LIMITS[depth]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user_prompt = (
        f"Product: {product_url}\n"
        f"Target customer: {target_customer or 'not specified'}\n"
        f"Depth: {depth} (up to {max_prospects} total prospects across all types). Focus: {focus}. "
        f"Today's date: {today}.\n\n"
        f"Findings already researched (classify, score, and structure only these):\n"
        f"{json.dumps(findings, indent=2)}"
    )
    return _complete(CLASSIFY_SYSTEM_PROMPT, user_prompt, tools=None)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "product"


def _finish_run(analysis: dict[str, Any], usage: _UsageTotal, *, product_url: str, depth: str, focus: str) -> dict[str, Any]:
    """Shared post-processing for both tools: write, verify, generate the report, meter."""
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


mcp = FastMCP(
    "signal-scout",
    instructions=(
        "Turns research findings into an evidence-backed, verified shortlist of first customers, "
        "market segments, and companies worth pitching. Prefer classify_and_score if you already "
        "gathered findings with your own web_search/web_fetch — it's cheaper and doesn't duplicate "
        "work you can already do. Use find_first_customers only if you have no web tools of your own."
    ),
)


def _validate_depth_focus(depth: str, focus: str) -> None:
    if depth not in DEPTH_LIMITS:
        raise ValueError(f"depth must be one of {sorted(DEPTH_LIMITS)}, got {depth!r}")
    if focus not in FOCUS_VALUES:
        raise ValueError(f"focus must be one of {sorted(FOCUS_VALUES)}, got {focus!r}")
    # Checked before the (paid) model call, not after — a cap that only fires once the
    # expensive call already happened wouldn't protect the budget it exists to protect.
    if calls_today() >= DAILY_CALL_CAP:
        raise RuntimeError(
            f"Daily call cap ({DAILY_CALL_CAP}) reached and no payment gate exists yet — "
            "refusing to spend more API budget today. Raise SIGNAL_SCOUT_DAILY_CALL_CAP "
            "once you've priced this deliberately (see ../MONETIZATION.md)."
        )


@mcp.tool()
def classify_and_score(
    product_url: str,
    findings: list[dict[str, Any]],
    target_customer: str = "",
    depth: str = "standard",
    focus: str = "all",
) -> dict[str, Any]:
    """Classify and score findings YOU already researched — the default choice for a caller
    that has its own web_search/web_fetch (Claude Code included). Does not re-research
    anything; it only adds what a bare LLM call doesn't do reliably: disciplined
    Individual/Segment/Company classification, per-type scoring, automated source
    verification, and a portable HTML report.

    Args:
        product_url: The startup's URL, repo, or a one-line product description.
        findings: A list of dicts you already gathered, each with at least
            "source_url" and "evidence" (the exact text supporting the signal), plus
            whatever of "source_title", "source_type", "signal_date" you have. Do not
            pad this with fabricated findings — classification only covers what's given.
        target_customer: Your ICP description, if known (optional — improves fit scoring).
        depth: "quick" (<=5 prospects), "standard" (<=10, default), or "deep" (<=20) —
            caps how many of `findings` get promoted to the primary shortlist.
        focus: "all" (default), "individuals", "segments", "companies",
            "competitor-chasers", or "design-partners".

    Returns a summary plus paths to the full JSON analysis and the standalone HTML report
    (verified via verify_sources.py --apply before the report is generated).
    """
    _validate_depth_focus(depth, focus)
    if not findings:
        raise ValueError("findings must be a non-empty list — nothing to classify.")

    analysis, usage = _run_classification(product_url, target_customer, findings, depth, focus)
    return _finish_run(analysis, usage, product_url=product_url, depth=depth, focus=focus)


@mcp.tool()
def find_first_customers(product_url: str, depth: str = "standard", focus: str = "all") -> dict[str, Any]:
    """Research a startup URL end-to-end and return an evidence-backed shortlist of first
    customers, market segments, and companies worth pitching, using public signals only.

    Only reach for this if you have no web_search/web_fetch of your own — if you do (most
    agent harnesses, including Claude Code, already have both), gather findings yourself
    and call classify_and_score instead. Paying this tool to re-run searches you could run
    yourself for free doesn't add value; it just marks up compute.

    Args:
        product_url: The startup's URL, repo, or a one-line product description.
        depth: "quick" (<=5 prospects), "standard" (<=10, default), or "deep" (<=20).
        focus: "all" (default), "individuals", "segments", "companies",
            "competitor-chasers", or "design-partners".

    Returns a summary plus paths to the full JSON analysis and the standalone HTML report
    (verified via verify_sources.py --apply before the report is generated).
    """
    _validate_depth_focus(depth, focus)
    analysis, usage = _run_research(product_url, depth, focus)
    return _finish_run(analysis, usage, product_url=product_url, depth=depth, focus=focus)


if __name__ == "__main__":
    mcp.run(transport="stdio")
