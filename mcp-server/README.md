# signal-scout MCP server (v0 — B2A distribution)

Wraps signal-scout as a callable tool for *other agents*, not just for a human
running Claude Code. Any MCP client — another agent, a sales-ops bot, a
workflow orchestrator — can call it and get back a scored, verified report,
machine-to-machine.

This is a v0 scaffold: the research loop, classification, source
verification, and report generation are real and tested (see below).

**This code is free and self-hostable, permanently — that's deliberate, not
a placeholder.** Per `../MONETIZATION.md`, restricting access to a Python
script and some prompts doesn't create real defensibility, it just throws
away distribution. The actual paid product (if/when built) is a *hosted*
version of this — no self-managed `ANTHROPIC_API_KEY`/infra, a higher daily
call limit, and the cross-user recalibration engine that only exists once
many people's usage accumulates in one place. Every call is metered locally
to `usage.jsonl` regardless, so real per-call cost is visible either way.

## Two tools, split by what actually adds value

A capable calling agent — Claude Code very much included — already has
`web_search`/`web_fetch` and can reason well on its own. Paying this server
to redo that work isn't a real value-add, it's just marked-up compute. So
there are two tools, and which one is worth calling depends on what the
caller already has:

- **`classify_and_score(product_url, findings, ...)`** — the default. Takes
  findings the caller already gathered with its own web tools and adds only
  what a bare LLM call doesn't do reliably: disciplined Individual/Segment/
  Company classification, per-type scoring, automated source verification,
  and a portable HTML report. No web tools declared — cheaper, and it
  doesn't duplicate research the caller can already do.
- **`find_first_customers(product_url, ...)`** — does its own research
  end-to-end via server-side `web_search`/`web_fetch`. Only worth calling
  when the caller has no web tools of its own.

Both funnel into the same downstream pipeline (below).

## What it does

1. Runs a Claude Sonnet 5 agent — either researching from scratch
   (`find_first_customers`) or classifying supplied findings
   (`classify_and_score`) — against a structured-output schema (`schema.py`,
   a trimmed version of the skill's JSON schema), with continuation turns
   for long-running server-tool loops (`pause_turn`).
2. Writes the result to `analysis-<date>.json`.
3. Runs `verify_sources.py --apply` (drops dead sources, flags bot-walled
   ones) — the same script the human-facing skill uses.
4. Runs `generate_report.py` to produce the standalone HTML report.
5. Logs token usage and an estimated cost to `usage.jsonl`.

## Setup

```bash
cd mcp-server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or `ant auth login`
python3 server.py   # runs over stdio — point an MCP client at this command
```

Environment variables (all optional):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` / `ant auth login` | — | Required to call the Claude API |
| `SIGNAL_SCOUT_MODEL` | `claude-sonnet-5` | Model used for research |
| `SIGNAL_SCOUT_OUTPUT_DIR` | `~/.signal-scout/reports` | Where analysis JSON + HTML reports land |
| `SIGNAL_SCOUT_METER_LOG` | `~/.signal-scout/usage.jsonl` | Where call metering is logged |

## What's tested vs. not

Tested without spending API money (mocked Anthropic client): the full
pipeline — JSON parsing, `pause_turn` continuation, `refusal` handling,
input validation, subprocess calls to `verify_sources.py`/`generate_report.py`,
and usage metering.

**Not yet tested: an actual live call.** The `web_search_20260209` /
`web_fetch_20260209` tool declarations and the `output_config.format` JSON
schema are written to the documented API shape, but structured outputs
combined with a long server-tool research loop hasn't been verified against
the real API. **Run one real call and inspect the output before relying on
this for anything paid.** If the schema needs adjusting (e.g. a field the
model can't populate under strict mode), `schema.py` is the only file that
should need edits.

## What's still missing before this reaches other people's agents

- **Not a payment gate — per `../MONETIZATION.md`, don't build one.** As of
  mid-2026, nobody in this specific niche (B2B sales-intelligence MCP
  servers) charges per call — Apollo, Clay, Warmly, and Brand24 all bundle
  MCP access free into their existing subscription. Building x402/Stripe MPP
  billing now would be payment infrastructure for demand that doesn't exist
  yet in this category. Revisit only if that changes.
- **Hosting.** This runs over stdio locally. To be callable by *other
  people's* agents (not just your own), it needs to run somewhere reachable
  — a small always-on host, or Anthropic's Managed Agents / MCP hosting.
  `SIGNAL_SCOUT_DAILY_CALL_CAP` is the gate for a hosted instance (raise it
  for paying subscribers), not a per-call charge.
- **A public listing.** An MCP server nobody can find gets no B2A traffic.
  Once hosted, list it in an MCP registry / marketplace so other agents can
  discover it — but treat this as distribution for the same paid core
  product (Section 7 of `../MONETIZATION.md`), not a separate revenue line.
