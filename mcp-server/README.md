# signal-scout MCP server (v0 — agent-to-agent interface)

Wraps signal-scout as a callable tool for *other agents*, not just for a human
running Claude Code. Any MCP client — another agent, a sales-ops bot, a
workflow orchestrator — can call it and get back a scored, verified report,
machine-to-machine.

This is a v0 scaffold. The research loop and classification are
implemented but untested; source verification, the no-people filter, and
report generation are the shared scripts covered by the skill's tests
(see "What's tested vs. not" below).

It is self-hostable. Every call is metered locally to
`usage.jsonl` (tokens and an estimated USD cost), so per-call cost is
visible to whoever runs it.

## Two tools, split by what actually adds value

A capable calling agent — Claude Code very much included — already has
`web_search`/`web_fetch` and can reason well on its own. Having this server
redo that research spends a second set of search and model tokens for the
same findings. So there are two tools, and which one is worth calling
depends on what the caller already has:

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

## No named people by default

Both tools take `people: bool = False`. With the default, the server returns
Segments and Companies only: it drops every Individual before verification,
then redacts person names, @handles, u/handles, personal emails, and profile
URLs from every other field, from `handoff-<date>.json`, and from the
verification text it returns. A segment, company, or battlecard entry whose
only source is a personal profile or a post under a personal account is
dropped. `focus="individuals"` is refused unless `people=True`.

Each call is metered before verification runs. Verification has a timeout sized to depth (180s, 360s, 720s); if it runs out, the tool still returns a report but sets `verification_timed_out: true` and says the report is unverified. Pass
`people=True` only for a private, access-controlled run, never for a server that
other people's agents can reach. Details and limits: [COMPLIANCE.md](../COMPLIANCE.md).

## What it does

1. Runs a Claude Sonnet 5 agent — either researching from scratch
   (`find_first_customers`) or classifying supplied findings
   (`classify_and_score`) — against a structured-output schema (`schema.py`,
   a trimmed version of the skill's JSON schema), with continuation turns
   for long-running server-tool loops (`pause_turn`).
2. Writes the result to `analysis-<date>.json`.
3. Runs `verify_sources.py` with `--annotate-out`/`--handoff-out` (drops
   broken/not-on-page prospects, tags bot-walled ones) — the same script the
   human-facing skill uses. In the default no-people mode, Individuals are
   dropped before this step and person references are redacted after it.
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

Nothing in `mcp-server/` has automated tests. There is no test file here and
CI does not run this directory. The scripts it shells out to
(`verify_sources.py`, `generate_report.py`) are covered by the tests under
`skills/signal-scout/scripts/` and by `evals/pipeline/`. The server's own
logic (JSON parsing, `pause_turn` continuation, `refusal` handling, input
validation, usage metering) has not been exercised, with a mock or otherwise.

**Not yet tested: an actual live call.** The `web_search_20260209` /
`web_fetch_20260209` tool declarations and the `output_config.format` JSON
schema are written to the documented API shape, but structured outputs
combined with a long server-tool research loop hasn't been verified against
the real API. **Run one real call and inspect the output before relying on
this for anything that matters.** If the schema needs adjusting (e.g. a field the
model can't populate under strict mode), `schema.py` is the only file that
should need edits.

## What's still missing before this reaches other people's agents

- **No per-caller cost control.** `SIGNAL_SCOUT_DAILY_CALL_CAP` (default 20)
  is a global spend backstop, not per-caller auth or quotas — raise it
  deliberately if you intend to allow more calls.
- **Hosting.** This runs over stdio locally. To be callable by *other
  people's* agents (not just your own), it needs to run somewhere reachable
  — a small always-on host, or Anthropic's Managed Agents / MCP hosting.
- **A public listing.** Other agents can only call a server they can
  discover. Once hosted, list it in an MCP registry so other agents can
  find it.
