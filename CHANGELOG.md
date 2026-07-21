# Changelog

## 1.6.0

Client-deliverable report capabilities (designed for the agency / fractional-GTM reader), verification-engine hardening, and a formal compliance posture.

- **Added: authored `executive_summary`** — optional client-facing block (overview, key findings, Monday-morning next steps) rendered under the hero. Synthesis-only by rule: every statement must trace to a verified prospect's fields, so it introduces no unverified claims.
- **Added: company account tiers** — optional `tier` (1/2/3) + required `tier_rationale` per company; the report groups Companies into **Tier 1 — pursue now / Tier 2 — nurture / Tier 3 — monitor**, turning a flat list into an account plan. Tiering rubric added to research-framework.md (tier = execution priority, not a restatement of the score).
- **Added: verified competitive battlecard** — optional `competitive_context.battlecard` entries (claim, quoted evidence, source_url, switching barrier, counter-angle). Entries are **verified exactly like prospects** (fetched, containment-checked, tier-badged); a disqualified entry is dropped from the report and handoff but does not fail the run. Each entry is also **cross-examined against the run's own prospects** via `competitor_mentioned` — zero corroboration renders a "Single-source" badge instead of shipping a one-source claim as consensus.
- **Added: trust-mark footer** — every report now states "N of M claims verified against their live or archived source" (prospects + battlecard combined) plus the public-signals-only disclosure, putting the product's core promise where a skeptical client looks.
- **Hardened: Wayback Machine fallback in `verify_sources.py`.** When a live page can't be read — dead link, bot wall (incl. Reddit 403), rate limit, or a JS shell with too little text — verification retries against the closest archived copy before assigning a failing tier, and the note discloses the archive date. Upgrades many former Broken/Snippet-only/Unverified results to real containment checks.
- **Hardened: SPA text extraction.** The HTML text extractor now harvests meta descriptions (`description`, `og:*`, `twitter:*`) and JSON-LD string values, so JS-rendered pages expose their substance to verification instead of failing at the 200-char minimum.
- Added: `finalize.py` validates the new sections (tier values, tier_rationale, battlecard required fields + URL) and reports non-verified battlecard entries in its condensed summary.
- Added: COMPLIANCE.md — the compliant-by-construction posture (no brokers, no scraped contacts, no access-control bypass, source disclosed on every claim), stated formally so users and their clients can point at it.
- Tests: 95 total across 6 suites — new coverage for Wayback fallback, SPA extraction, battlecard verification/corroboration/handoff-drop, tier rendering, exec summary, trust mark, and the new validations. Existing failure-path tests no longer touch the network.

## 1.5.0

- **Added: `scripts/finalize.py` — one-shot finishing pipeline.** Chains schema validation → source verification (annotate + handoff) → HTML report → CRM-ready `prospects.csv` → cross-run diff (when sibling snapshots exist) into a single command with a condensed summary that prints only prospects needing action. `--validate-only` machine-checks the JSON offline (required fields, per-type dimension sets, stage values, URL shape, and score-vs-dimensions arithmetic via `signal_scout_core.compute_score`), replacing the drafting-loop need to hold the full schema in context.
- **Changed: SKILL.md is now ~40% smaller in context.** Added standard agent-skills YAML frontmatter (`name`/`description` — previously absent, which broke skill discovery on frontmatter-requiring hosts). The full JSON schemas moved to `references/report-artifact.md` (now the schema authority, previously it pointed back at SKILL.md); SKILL.md keeps a compact shape summary and delegates enforcement to `finalize.py --validate-only`. The completeness checklist is split into machine-checked (delegated to `finalize.py`) and judgment-only items.
- **Changed: host-agnostic tool language.** SKILL.md refers to capabilities (web search, web fetch, browser automation, shell) instead of Claude Code-specific tool names, so the same skill file works in Claude Code, Claude Cowork, OpenCode, and Codex. Added repo-level `AGENTS.md` for AGENTS.md-reading agents (run instructions, modification guardrails, install targets).
- **Added: BD partner-motion taxonomy** in `research-framework.md` — five motions (integration, distribution/marketplace, co-marketing, reseller/agency, customer account), each with the value exchanged, the right first ask, and the typical internal owner; `what_to_propose` must name one.
- Added: CLI CSV export (`prospects.csv` from `finalize.py`) matching the HTML report's Export CSV columns, so a shortlist reaches a spreadsheet/CRM without opening the report.
- Fixed: stray non-English characters in `research-framework.md` ("Signal freshness" section).
- Versions: plugin/package manifests bumped to 1.5.0 (superseded by 1.6.0 in the same release cycle).

## 1.4.0

- Added: `verify_sources.py` stamps every prospect with `verified_at` (today's date, regardless of tier); `generate_report.py` renders it as a client-side "· Nd ago" age suffix on the verification badge, computed against the viewer's own clock so a report reopened weeks later shows its true age instead of looking permanently fresh.
- Added: `opener_grounding_note` — `verify_sources.py` checks each Individual's `opener` against its own `evidence` (not the live page) and flags it when the opener invents specifics the evidence doesn't support. A softer, separate signal from `verification_tier`: it doesn't fail the run or drop the prospect, just renders an inline warning on the card.
- Added: cross-run novelty badges on the HTML report. `generate_report.py` auto-detects sibling `analysis-*.json` snapshots and an `outcomes.jsonl` in the same directory (override with `--history`/`--no-history`/`--outcomes`) and badges each prospect New / Seen Nx / Resurfacing, reusing `diff_reports.py`'s own cumulative history and outcome index so the report and the CLI diff never disagree about what counts as new.
- Changed: `diff_reports.py`'s snapshot accumulation is now a shared function (`accumulate_history`), reused by both its own CLI and `generate_report.py`'s novelty badges instead of two separate implementations of "have we seen this prospect before."
- Changed: `portfolio_merge.py` accepts a glob per product (e.g. `outputs/<slug>/analysis-*.json`) instead of only a single file, and cross-references each product's full cumulative history rather than just its latest snapshot — a prospect dropped from product A's latest run still surfaces if it's currently live in product B's. Single-file-per-product usage is unchanged.
- Added: `test_generate_report.py` (17 tests) and `test_portfolio_merge.py` (19 tests); extended `test_verify_sources.py` with 6 tests covering `verified_at` and `opener_grounding_note`.
- Docs: SKILL.md, `references/report-artifact.md`, and `references/roadmap.md` updated to document all of the above.

## 1.3.0

- **Fixed (critical): source verification was inverted and certified fabricated evidence as "Verified."** `verify_sources.py` scored cited evidence against the live page with `difflib.SequenceMatcher.quick_ratio()`, which compares multisets of characters and normalises by the combined length of *both* inputs. A ~200-character quote against a ~40,000-character page is therefore mathematically capped near 0.01 and could never reach the 0.15 threshold, while any claim at all against a short page scored high. Measured on a live page: a real quote scored 0.0337 and was flagged `LOW_MATCH`, and an entirely fabricated claim on the same page scored 0.3664 and passed as `Verified`. Because `LOW_MATCH` did not fail the run, every report shipped with the badge either wrong or backwards.
- **Changed: evidence matching is now containment, not similarity.** `signal_scout_core.evidence_signals()` reports two independent numbers, both divided by the evidence alone so page length cannot move them: `quoted` (n-gram containment — proves quotation) and `topical` (distinctive-term containment — survives rewording). Verbatim evidence now scores 1.00 on pages from 500 to 120,000 characters; fabricated evidence scores 0.00 at every size.
- **Added: `unsupported` verification tier ("Not on page")** — the source loaded and was readable and the claim is not in it. Previously indistinguishable from an honest paraphrase. This is the fabrication signal, and it is strictly worse than a dead link: `verify_sources.py` now exits non-zero on it, `--handoff-out` drops it, and the report badges it in red.
- Changed: `low_match` renders as "Paraphrased" in amber rather than red — rewording a real signal is legitimate and should not look like an error.
- Removed: `--match-threshold`. Its semantics don't exist under the new metric; thresholds now live in `signal_scout_core` as `QUOTED_THRESHOLD` / `SUPPORTED_THRESHOLD`.
- **Fixed: the report's editorial serif was dead code.** `body` declared the display face and the very next rule re-declared `body` with the UI sans stack, so every heading silently fell back to system sans — the reason the report read as generic SaaS. Display and UI faces are now separate variables applied to separate elements.
- Report: prospect cards carry a colour-coded spine (individual/segment/company) so type is legible while scrolling; best-in-category scores align on one baseline instead of floating at three different heights; score rings inherit their type's accent colour.
- **Fixed: HTTP 429 outside Reddit was recorded as a broken source.** The rate-limit special case checked `is_reddit(url)` before the status code, so a throttled fetch to any other domain (found via dogfooding: Hacker News rate-limited a run's IP after heavy fetching) was indistinguishable from a dead link — `TIER_BROKEN` instead of `TIER_SNIPPET_ONLY`. 429 now always means snippet-only, on any domain; 403 stays Reddit-specific since elsewhere it can mean genuinely forbidden/gated content, not just an anti-bot wall. Added `test_verify_sources.py` (6 tests, mocked HTTP, no network).
- **Fixed: `diff_reports.py` only compared the immediately-previous snapshot, so a prospect could be wrongly re-flagged "new" after merely skipping one run.** It now takes every saved snapshot for a product, sorts by `generated_at`, and classifies each current prospect as new (never seen in any prior snapshot), recurring (seen before), or dropped (in the last snapshot, absent now) — the CLI still accepts exactly 2 files unchanged. Added `--outcomes outcomes.jsonl` to cross-reference recurring prospects against logged outcomes, matching on `(name, source_url)` when both are available and falling back to name alone. `log_outcome.py` now accepts and stores `--source-url` to make that precise match possible. Added `test_diff_reports.py` (9 tests).

## 1.2.0

- Added: `verify_sources.py --annotate-out` tags every prospect in-place with `verification_tier`/`verification_note` (verified / snippet_only / low_match / broken); `generate_report.py` renders it as a badge on each card, and it's a new column in the CSV export.
- Added: `verify_sources.py --handoff-out` writes a filtered copy of the report with broken-source prospects dropped, so signal-outreach (or any other consumer) never receives dead links.
- Added: `scripts/signal_scout_core.py` — a small shared module for the genuinely deterministic pieces (score-weighting formula, schema validation, verification-tier vocabulary), now imported by both `verify_sources.py` and `generate_report.py` instead of duplicating the constants. Classification and dimension ratings stay LLM judgment, not code — this module doesn't attempt to encode that.
- Added: `scripts/portfolio_merge.py` — cross-references saved reports across multiple products, surfacing prospects (by exact source URL or normalized name) that appear in 2+ products. Wired as SKILL.md step 9, opt-in once a user has 2+ product reports.
- Docs: SKILL.md, `references/report-artifact.md`, and `references/roadmap.md` updated to document all of the above.

## 1.1.0

- Fixed: `SKILL.md` carried a stale absolute path (`Base directory: file:///Users/.../first-to-first-sale/signal-scout`) left over from before this skill was extracted into its own repo. Removed — `<skill_dir>` now resolves relative to wherever the skill is actually installed.
- Added: "Export CSV" button on the HTML report. Flattens individuals/segments/companies into one CSV (type, name, stage, score, pain signal, why fit, why now, source, next action, caution) for pasting into a spreadsheet or CRM.

## 1.0.1

- Report polish, Reddit-blocked handling, CLI-styled action prompts.

## 1.0.0

- Initial release: source verification, outcome feedback loop, watch mode, vertical query packs.
