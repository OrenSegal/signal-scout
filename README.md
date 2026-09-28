# signal-scout

[![CI](https://github.com/OrenSegal/signal-scout/actions/workflows/ci.yml/badge.svg)](https://github.com/OrenSegal/signal-scout/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-black)](LICENSE)

An agent skill for Claude Code, Claude Cowork, OpenCode, Codex, and any [agent-skills](https://agentskills.io)-compatible host. It turns a startup URL or product description into a short, evidence-backed shortlist of first customers, market segments, and companies worth pitching, using **public signals only**. No data brokers, no scraped emails or contact info, no private groups, no protected-trait targeting.

**It checks itself before it ships.** In most AI prospecting flows, the model that writes a claim about a prospect also grades its own confidence in that claim, and nothing forces it to reopen the source. `scripts/verify_sources.py` does: it fetches every cited URL and confirms the evidence is actually on the page, not paraphrased from a search snippet or invented. A claim that fails never reaches the report. See [What this actually fixes](#what-this-actually-fixes).

Most "find me customers" prompts return a flat list of "prospects" that don't quite fit anything: an audience with a fake outreach opener, a company scored on personal reachability. signal-scout classifies every candidate as exactly one of three types, each with its own scoring model and next action:

- **Individual**: one addressable person you could plausibly reply to, DM, or comment at.
- **Segment**: an audience or demand pattern, not a person (a recurring complaint thread, a search pattern). Worth a content or GTM angle, not a message.
- **Company**: an organization evaluated as a BD, partnership, or account target, reached through a public contact path, not a personal inbox.

## What it produces

- **Individuals** scored across 5 dimensions (pain strength, product fit, timing, reachability, evidence quality), each with an outreach opener and follow-up angle
- **Segments** scored across 4 dimensions (no reachability, since an audience isn't reachable), each with a content angle, target keywords, and channels
- **Companies** scored across 4 dimensions (strategic fit, timing, execution ease, evidence quality), each with an execution path, public contact path, and BD angle
- "Best in category" call-outs: up to three highest scorers, one per type present, never one cross-type "top prospect"
- Repeated pain patterns, competitive landscape, a seven-day plan, and a research audit trail
- A standalone, dependency-free HTML report with interactive filtering

See [`examples/finder-report.json`](examples/finder-report.json) and its rendered [`examples/finder-report.html`](examples/finder-report.html) for a full worked example.

## What this actually fixes

Three specific, well-worn complaints about AI-assisted prospecting, addressed by mechanism rather than promise:

- **"The output needs a cleanup pass before I can send anything."** Every prospect's evidence is checked against its live source before the report ships, instead of being graded by the model that wrote it. Every outreach opener is cross-checked against that same evidence too: `verify_sources.py` flags any opener that invents specifics the evidence doesn't support. A prospect whose evidence doesn't hold up is dropped, opener and all, before you see it.
- **"Research goes stale fast, and refreshing it means redoing the work."** `scripts/diff_reports.py` checks a product's full run history, not just the last snapshot, and reports only what's new. A prospect who briefly dropped off and resurfaced isn't re-announced as new, and one with a logged outcome is flagged instead of repeated. The HTML report badges every prospect New / Seen Nx / Resurfacing and shows each verification's age, so a report reopened weeks later doesn't look freshly generated.
- **"Enrichment tools charge per row and the meter never stops."** signal-scout runs on your own Claude Code or OpenCode session plus public web search and fetch, not a metered per-contact API. That's an architectural difference, not a measured one: nobody has compared total cost against Clay or similar tools, so there's no number here.

What it deliberately doesn't do: send infrastructure at scale, CRM sync, or contact-data enrichment (finding emails or phone numbers). signal-scout's job ends at a verified, scored shortlist and a next action. Pair it with [signal-outreach](https://github.com/OrenSegal/first-to-first-sale) for the send step.

## Beyond the one-off report

Five things push this past a single static list, all opt-in per product (see [`skills/signal-scout/references/roadmap.md`](skills/signal-scout/references/roadmap.md) for when the agent should offer each):

- **Source verification**: `scripts/verify_sources.py` fetches every cited source and checks that the cited evidence is in the live page before a report ships. A claim whose source loads but doesn't contain it is tagged **Not on page**, fails the run, and never reaches the report. A self-graded `evidence_quality` score can't catch this, because the model rating the evidence is the model that wrote it. It runs every time, stamps every prospect with `verified_at` so the report can show its age, and flags outreach openers that invent specifics their evidence doesn't support.

  How this differs from grounding checkers: the ones I looked at (Vectara HHEM, Google `checkGrounding`, Ragas, Patronus Lynx, Galileo Luna, Guardrails) score a claim against text you supply and leave fetching the URL to you. And "verified" in GTM tooling usually means verified contact data (is this email deliverable), not a verified claim.
- **Outcome feedback loop**: `scripts/log_outcome.py` records what happened after outreach (replied / converted / went cold), and `scripts/recalibrate.py` turns that history into hit rates per source type and query bucket, so the next run for the same product weights toward what's working.
- **Watch mode**: `scripts/diff_reports.py` compares a product's *entire* saved run history and surfaces new prospects, prospects resurfacing after an absence, and dropped ones, cross-referenced against logged outcomes so a prospect you already decided about doesn't reappear. The same classification shows on the HTML report as New / Seen Nx / Resurfacing badges. Pairs with a scheduled run.
- **Portfolio mode**: `scripts/portfolio_merge.py` cross-references saved reports across several products (each argument can be a glob over saved snapshots) and surfaces prospects relevant to more than one, worth a single conversation instead of two. Opt-in once you have 2+ products with saved history.
- **Vertical query packs**: [`skills/signal-scout/references/query-packs/`](skills/signal-scout/references/query-packs/) has query buckets and source mixes for devtools, health/wellness, and marketplace/SaaS products.

## Install

Pick whichever fits how you work. All three install the same skill files.

### npx (recommended, no clone needed)

```bash
npx signal-scout
```

This copies the skill into `~/.agents/skills/signal-scout`, where Claude Code and OpenCode both look for it. Pass `--dir` to install somewhere else:

```bash
npx signal-scout --dir ./.agents/skills/signal-scout
```

### Claude Code plugin marketplace

```
/plugin marketplace add OrenSegal/signal-scout
/plugin install signal-scout@signal-scout
```

Once installed, invoke it as `/signal-scout:signal-scout` (plugin-installed skills are namespaced with the plugin name). Update it later with `/plugin marketplace update signal-scout`.

### Manual / git clone

```bash
git clone https://github.com/OrenSegal/signal-scout.git
cd signal-scout
./install.sh
```

Or copy the skill directory directly:

```bash
cp -r signal-scout/skills/signal-scout ~/.agents/skills/signal-scout
```

## Usage

Once installed, invoke the skill in Claude Code or OpenCode:

```
/signal-scout https://your-startup.com
```

With modes:

```
/signal-scout --depth deep --focus companies https://your-startup.com
```

**Modes:** `--depth` quick (≤5 total) · standard (≤10, default) · deep (≤20), crossed with `--focus` all (default) · individuals · segments · companies · competitor-chasers · design-partners

## One-command pipeline

All scripts have zero external dependencies (Python 3.10+ stdlib only) and work independently of any agent. `finalize.py` chains the whole finishing flow (schema validation, source verification, HTML report, CRM-ready `prospects.csv`, and the cross-run diff when prior snapshots exist) into one call with a condensed summary:

```bash
python3 skills/signal-scout/scripts/finalize.py analysis.json --out outputs/signal-scout-report.html
```

`--validate-only` machine-checks the JSON (required fields, dimension sets, score arithmetic) without touching the network, for the drafting loop. The individual scripts (`verify_sources.py`, `generate_report.py`, `diff_reports.py`, `portfolio_merge.py`, `recalibrate.py`, `log_outcome.py`) still run on their own:

```bash
python3 skills/signal-scout/scripts/generate_report.py analysis.json outputs/signal-scout-report.html
```

## Compatibility

The skill is host-agnostic: `SKILL.md` has standard agent-skills frontmatter and refers to capabilities (web search, web fetch, shell), not host-specific tool names. Install to `~/.agents/skills/` for Claude Code / Cowork / OpenCode, or pass `--dir` to target another host's skills directory. Codex and other AGENTS.md-reading agents get repo-level guidance from [`AGENTS.md`](AGENTS.md).

## JSON schema

See [`skills/signal-scout/references/report-artifact.md`](skills/signal-scout/references/report-artifact.md) for the full output schema (`individuals` / `segments` / `companies`) and [`skills/signal-scout/references/research-framework.md`](skills/signal-scout/references/research-framework.md) for classification rules, scoring dimensions, and query buckets.

## Turning results into outreach

signal-scout finds and scores prospects; it doesn't write the outreach. Pair it with [signal-outreach](https://github.com/OrenSegal/first-to-first-sale), which takes a signal-scout report and produces the next action per type: an outreach sequence for an Individual, a content/GTM brief for a Segment, or a BD pitch one-pager for a Company.

## Calling it from another agent (MCP server)

[`mcp-server/`](mcp-server/) wraps the research workflow as a tool other agents can call. See [`mcp-server/README.md`](mcp-server/README.md) for setup and what's tested vs. not.

## Dependencies

- Python 3.10+ (stdlib only, no pip install required) for the report generator
- Claude Code or OpenCode with `websearch`, `webfetch`, and `bash` tools available
- Node.js 16+ only if installing via `npx`

## License

MIT
