# signal-scout

[![CI](https://github.com/OrenSegal/signal-scout/actions/workflows/ci.yml/badge.svg)](https://github.com/OrenSegal/signal-scout/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-black)](LICENSE)

signal-scout is an agent skill that finds early customers for a product. You give it a startup URL or a product description. You get back a short, scored shortlist of people, market segments, and companies worth approaching, each backed by a public source that was checked before the report was written.

It runs in Claude Code, Claude Cowork, OpenCode, Codex, and any [agent-skills](https://agentskills.io)-compatible host. It uses **public signals only**: no data brokers, no scraped emails or contact info, no private groups, no protected-trait targeting.

## Three prospect types

Generic "find me customers" prompts tend to return one flat list where nothing quite fits: an audience with a made-up outreach opener, or a company scored on how reachable it is personally. signal-scout puts every candidate into exactly one of three types, each with its own scoring and next action:

- **Individual**: one addressable person you could plausibly reply to, DM, or comment at.
- **Segment**: an audience or demand pattern, not a person (a recurring complaint thread, a search pattern). Worth a content or GTM angle, not a message.
- **Company**: an organization evaluated as a BD, partnership, or account target, reached through a public contact path, not a personal inbox.

## Output

- **Individuals** scored on 5 dimensions (pain strength, product fit, timing, reachability, evidence quality), each with an outreach opener and follow-up angle.
- **Segments** scored on 4 dimensions (reachability is left out, since you can't reach an audience directly), each with a content angle, target keywords, and channels.
- **Companies** scored on 4 dimensions (strategic fit, timing, execution ease, evidence quality), each with an execution path, public contact path, and BD angle.
- "Best in category" call-outs: the top scorer for each type present, so at most three. There is never one cross-type "top prospect".
- Repeated pain patterns, competitive landscape, a seven-day plan, and a research audit trail.
- A standalone, dependency-free HTML report with interactive filtering.

For a full worked example, see [`examples/finder-report.json`](examples/finder-report.json) and the rendered [`examples/finder-report.html`](examples/finder-report.html).

## Source verification

In most AI prospecting flows, the model that writes a claim about a prospect also grades its own confidence in that claim, and nothing makes it reopen the source. A self-graded `evidence_quality` score can't catch a bad claim for that reason.

`scripts/verify_sources.py` closes that gap. It fetches every cited URL and checks that the cited evidence is on the page, rather than paraphrased from a search snippet or invented. When the live page won't load, it tries a Wayback Machine or archive.ph copy; a bot-walled source with no archive is marked snippet-only instead of verified. When the source loads but doesn't contain the claim, the prospect is tagged **Not on page**, the run fails, and that prospect never reaches the report. The script also:

- runs on every report,
- stamps each prospect with `verified_at` so the report can show how old each check is,
- flags outreach openers that add specifics their evidence doesn't support.

The practical effect: a prospect whose evidence doesn't hold up is dropped, opener included, before you see it, so the output needs less cleanup before you send anything.

How this differs from grounding checkers: the ones I looked at (Vectara HHEM, Google `checkGrounding`, Ragas, Patronus Lynx, Galileo Luna, Guardrails) score a claim against text you supply and leave fetching the URL to you. In GTM tooling, "verified" usually means verified contact data (is this email deliverable), not a verified claim.

## Optional features

These go beyond a single report and are opt-in per product. [`skills/signal-scout/references/roadmap.md`](skills/signal-scout/references/roadmap.md) describes when the agent should offer each one.

- **Outcome feedback loop**: `scripts/log_outcome.py` records what happened after outreach (replied / converted / went cold). `scripts/recalibrate.py` turns that history into hit rates per source type and query bucket, so the next run for the same product leans toward what's working.
- **Watch mode**: `scripts/diff_reports.py` compares a product's *entire* saved run history, not just the last snapshot, and reports new prospects, prospects resurfacing after an absence, and dropped ones. It cross-references logged outcomes, so a prospect you already made a call on is flagged instead of repeated. The HTML report shows the same classification as New / Seen Nx / Resurfacing badges, and a report reopened weeks later doesn't look freshly generated. Pairs with a scheduled run.
- **Portfolio mode**: `scripts/portfolio_merge.py` cross-references saved reports across several products (each argument can be a glob over saved snapshots) and lists prospects relevant to more than one, which are worth a single conversation instead of two. Useful once you have 2+ products with saved history.
- **Vertical query packs**: [`skills/signal-scout/references/query-packs/`](skills/signal-scout/references/query-packs/) has query buckets and source mixes for devtools, health/wellness, and marketplace/SaaS products.

## Cost model

signal-scout runs on your own Claude Code or OpenCode session plus public web search and fetch, not a metered per-contact enrichment API. That is an architectural difference, not a measured one. Nobody has compared total cost against Clay or similar tools, so there's no number here.

## Scope

It does not do sending infrastructure at scale, CRM sync, or contact-data enrichment (finding emails or phone numbers). Its job ends at a verified, scored shortlist and a next action.

For the next step, use [signal-outreach](https://github.com/OrenSegal/first-to-first-sale). It takes a signal-scout report and produces the next action per type: an outreach sequence for an Individual, a content/GTM brief for a Segment, or a BD pitch one-pager for a Company.

## Install

All three methods install the same skill files.

### npx (recommended, no clone needed)

```bash
npx signal-scout
```

This copies the skill into `~/.agents/skills/signal-scout`, where Claude Code and OpenCode both look for it. Use `--dir` to install somewhere else:

```bash
npx signal-scout --dir ./.agents/skills/signal-scout
```

### Claude Code plugin marketplace

```
/plugin marketplace add OrenSegal/signal-scout
/plugin install signal-scout@signal-scout
```

Plugin-installed skills are namespaced with the plugin name, so invoke it as `/signal-scout:signal-scout`. To update later, run `/plugin marketplace update signal-scout`.

### Manual / git clone

```bash
git clone https://github.com/OrenSegal/signal-scout.git
cd signal-scout
./install.sh
```

Or, from the same cloned directory, copy the skill folder yourself:

```bash
mkdir -p ~/.agents/skills/signal-scout
cp -r skills/signal-scout/. ~/.agents/skills/signal-scout/
```

## Usage

In Claude Code or OpenCode:

```
/signal-scout https://your-startup.com
```

With modes:

```
/signal-scout --depth deep --focus companies https://your-startup.com
```

**Modes:** `--depth` quick (≤5 total) · standard (≤10, default) · deep (≤20), combined with `--focus` all (default) · individuals · segments · companies · competitor-chasers · design-partners

## One-command pipeline

Every script uses only the Python 3.10+ standard library and runs without an agent. `finalize.py` chains the whole finishing flow into one call and prints a condensed summary. The steps are schema validation, source verification, the HTML report, a CRM-ready `prospects.csv`, and the cross-run diff when prior snapshots exist:

```bash
python3 skills/signal-scout/scripts/finalize.py analysis.json --out outputs/signal-scout-report.html
```

During drafting, `--validate-only` checks the JSON (required fields, dimension sets, score arithmetic) without touching the network. Each script (`verify_sources.py`, `generate_report.py`, `diff_reports.py`, `portfolio_merge.py`, `recalibrate.py`, `log_outcome.py`) can also run on its own:

```bash
python3 skills/signal-scout/scripts/generate_report.py analysis.json outputs/signal-scout-report.html
```

## Compatibility

`SKILL.md` uses standard agent-skills frontmatter and refers to capabilities (web search, web fetch, shell) instead of host-specific tool names. Install to `~/.agents/skills/` for Claude Code, Cowork, or OpenCode, or pass `--dir` to target another host's skills directory. Codex and other agents that read AGENTS.md get repo-level guidance from [`AGENTS.md`](AGENTS.md).

## JSON schema

[`skills/signal-scout/references/report-artifact.md`](skills/signal-scout/references/report-artifact.md) defines the output schema (`individuals` / `segments` / `companies`). [`skills/signal-scout/references/research-framework.md`](skills/signal-scout/references/research-framework.md) covers classification rules, scoring dimensions, and query buckets.

## MCP server

[`mcp-server/`](mcp-server/) wraps the research workflow as a tool other agents can call. See [`mcp-server/README.md`](mcp-server/README.md) for setup and for what is tested and what isn't.

## Dependencies

- Python 3.10+ (stdlib only, no pip install required) for the report generator
- Claude Code or OpenCode with `websearch`, `webfetch`, and `bash` tools available
- Node.js 16+, only if installing via `npx`

## License

MIT
