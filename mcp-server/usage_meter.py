"""Local call metering — no billing integration yet.

Logs every research call's token usage and an estimated cost to a JSONL
file, so the founder can see real per-call COGS and repeat-usage patterns
before wiring in an actual payment rail (x402 / Stripe MPP — see
../MONETIZATION.md). Nothing here talks to a payment provider; it's the
metering half a billing gate would read from.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

METER_LOG = Path(os.environ.get("SIGNAL_SCOUT_METER_LOG", str(Path.home() / ".signal-scout" / "usage.jsonl")))

# $ per million tokens. Keep in sync with shared/models.md in the claude-api
# skill (or platform.claude.com/docs/en/pricing) when pricing changes.
PRICING = {
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},  # intro pricing through 2026-08-31
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}
CACHE_READ_DISCOUNT = 0.1  # cache reads bill at ~0.1x the input rate
CACHE_WRITE_PREMIUM = 1.25  # cache writes (5-minute TTL) bill at ~1.25x the input rate


def _usage_field(usage: Any, name: str) -> int:
    return getattr(usage, name, None) or 0


def calls_today() -> int:
    """Count metered calls recorded today (UTC). No payment gate exists yet
    (see server.py's DAILY_CALL_CAP) — this is the only thing standing
    between a publicly reachable server and an unbounded Anthropic bill."""
    if not METER_LOG.exists():
        return 0
    today = datetime.now(timezone.utc).date().isoformat()
    count = 0
    with METER_LOG.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(record.get("at", "")).startswith(today):
                count += 1
    return count


def estimate_cost_usd(model: str, usage: Any) -> float:
    rates = PRICING.get(model, PRICING["claude-sonnet-5"])
    input_tokens = _usage_field(usage, "input_tokens")
    output_tokens = _usage_field(usage, "output_tokens")
    cache_read = _usage_field(usage, "cache_read_input_tokens")
    cache_write = _usage_field(usage, "cache_creation_input_tokens")
    cost = (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_read * rates["input"] * CACHE_READ_DISCOUNT
        + cache_write * rates["input"] * CACHE_WRITE_PREMIUM
    ) / 1_000_000
    return round(cost, 4)


def record_call(*, product_url: str, depth: str, focus: str, usage: Any, model: str) -> float:
    cost = estimate_cost_usd(model, usage)
    METER_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "product_url": product_url,
        "depth": depth,
        "focus": focus,
        "model": model,
        "input_tokens": _usage_field(usage, "input_tokens"),
        "output_tokens": _usage_field(usage, "output_tokens"),
        "cache_read_input_tokens": _usage_field(usage, "cache_read_input_tokens"),
        "cache_creation_input_tokens": _usage_field(usage, "cache_creation_input_tokens"),
        "estimated_cost_usd": cost,
    }
    with METER_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return cost
