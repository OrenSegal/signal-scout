# signal-scout — agent instructions

This repository packages **signal-scout**, an agent skill that turns a startup URL or product description into an evidence-backed, source-verified shortlist of first customers (Individuals), market segments (Segments), and partnership targets (Companies), using public web signals only.

## If you were asked to *run* signal-scout

The skill definition is `skills/signal-scout/SKILL.md` — read it and follow its workflow. It is host-agnostic: it needs web search, web fetch, and a shell with Python 3.10+ (stdlib only). Tool names in the skill are generic capabilities; map them to whatever your environment provides.

Key entry points:

- `skills/signal-scout/references/report-artifact.md` — the full JSON schema for the output artifact.
- `skills/signal-scout/references/research-framework.md` — classification rules, scoring dimensions, query buckets, BD partner motions.
- `skills/signal-scout/scripts/finalize.py analysis.json` — the one-shot pipeline: validates the JSON, verifies every cited source against its live page, generates the HTML report, exports `prospects.csv`, and diffs against prior runs. `--validate-only` for the drafting loop.

Non-negotiables (see SKILL.md "Research safely"): public signals only, no scraped contact data or data brokers, no bypassing paywalls/logins, never send outreach — draft it.

## If you were asked to *modify* this repository

- Read `skills/signal-scout/references/roadmap.md` first — the roadmap is frozen on new mechanisms until real outcome data exists; prefer fixes and infrastructure over features.
- Scripts are Python 3.10+ stdlib only — no new dependencies.
- Run the tests: `cd skills/signal-scout/scripts && python3 -m pytest` (or `python3 test_*.py` individually).
- `verify_sources.py` and `signal_scout_core.py` are the product's load-bearing claim (open-book source verification); be paranoid about regressions there — it shipped inverted once (see CHANGELOG 1.3.0).
- Keep `SKILL.md` compact: schemas belong in `references/report-artifact.md`, mechanical checks belong in `finalize.py`, not prose.

## Install targets

The skill installs to `~/.agents/skills/signal-scout` (`npx signal-scout`), which Claude Code, Claude Cowork, OpenCode, and other agentskills-compatible hosts can read; `--dir` overrides the destination (e.g. a Codex skills directory or a project-local `.agents/skills/`).
