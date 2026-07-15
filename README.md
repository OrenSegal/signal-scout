# signal-scout

A Claude Code / OpenCode skill that turns a startup URL or product description into a short, evidence-backed shortlist of first customers, market segments, and companies worth pitching — using **public signals only**. No data brokers, no scraped emails or contact info, no private groups, no protected-trait targeting.

Most "find me customers" prompts return a flat list of "prospects" that don't quite fit anything — an audience with a fake outreach opener, a company scored on personal reachability. signal-scout classifies every candidate as exactly one of three types, each with its own scoring model and next action:

- **Individual** — one addressable person you could plausibly reply to, DM, or comment at.
- **Segment** — an audience or demand pattern, not a person (a recurring complaint thread, a search pattern) — worth a content/GTM angle, not a message.
- **Company** — an organization evaluated as a BD, partnership, or account target, reached through a public contact path, not a personal inbox.

## What it produces

- **Individuals** scored across 5 dimensions (pain strength, product fit, timing, reachability, evidence quality), each with an outreach opener and follow-up angle
- **Segments** scored across 4 dimensions (no reachability — an audience isn't reachable), each with a content angle, target keywords, and channels
- **Companies** scored across 4 dimensions (strategic fit, timing, execution ease, evidence quality), each with an execution path, public contact path, and BD angle
- "Best in category" call-outs — up to three separate highest-scorers, one per type present, never one false cross-type "top prospect"
- Repeated pain patterns, competitive landscape, a seven-day plan, and a research audit trail
- A standalone, dependency-free HTML report with interactive filtering

See [`examples/finder-report.json`](examples/finder-report.json) and its rendered [`examples/finder-report.html`](examples/finder-report.html) for a full worked example.

## Beyond the one-off report

Four things push this past a single static list, all opt-in per product (see [`skills/signal-scout/references/roadmap.md`](skills/signal-scout/references/roadmap.md) for when the agent should offer each):

- **Source verification** — `scripts/verify_sources.py` fetches every cited source and fuzzy-matches the evidence against the live page before a report ships, catching dead links and paraphrased-from-a-snippet evidence that self-graded scores miss. Runs automatically every time.
- **Outcome feedback loop** — `scripts/log_outcome.py` records what actually happened after outreach (replied / converted / went cold); `scripts/recalibrate.py` turns that history into per-source-type and per-query-bucket hit rates, so the next run for the same product weights toward what's actually working instead of trusting self-graded evidence quality alone.
- **Watch mode** — `scripts/diff_reports.py` compares two dated snapshots of the same product and surfaces only new prospects, dropped prospects, and growing patterns — pairs with a recurring scheduled run instead of a full re-read every time.
- **Vertical query packs** — [`skills/signal-scout/references/query-packs/`](skills/signal-scout/references/query-packs/) ships tuned query buckets and source mixes for devtools, health/wellness, and marketplace/SaaS products, extendable as new verticals show a repeatable pattern.

## Install

Pick whichever fits how you work — all three install the same skill files.

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

## Standalone report generation

The report generator has zero external dependencies (Python 3.10+ stdlib only) and works independently of the agent:

```bash
python3 skills/signal-scout/scripts/generate_report.py analysis.json outputs/signal-scout-report.html
```

## JSON schema

See [`skills/signal-scout/references/report-artifact.md`](skills/signal-scout/references/report-artifact.md) for the full output schema (`individuals` / `segments` / `companies`) and [`skills/signal-scout/references/research-framework.md`](skills/signal-scout/references/research-framework.md) for classification rules, scoring dimensions, and query buckets.

## Turning results into outreach

signal-scout finds and scores prospects — it doesn't write the outreach itself. Pair it with [signal-outreach](https://github.com/OrenSegal/first-to-first-sale), which takes a signal-scout report and produces the right next action per type: an outreach sequence for an Individual, a content/GTM brief for a Segment, or a BD pitch one-pager for a Company.

## Dependencies

- Python 3.10+ (stdlib only — no pip install required) for the report generator
- Claude Code or OpenCode with `websearch`, `webfetch`, and `bash` tools available
- Node.js 16+ only if installing via `npx`

## License

MIT
