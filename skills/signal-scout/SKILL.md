# Skill: signal-scout

# Signal Scout

Turn a startup URL or product description into a short, evidence-backed map of who has a reason to care right now. Use public signals, preserve privacy, and keep three genuinely different kinds of leads separate instead of forcing them into one ranked list.

Read [references/research-framework.md](references/research-framework.md) before researching or scoring. Read [references/report-artifact.md](references/report-artifact.md) before creating the final report.

After delivering a report, check [references/roadmap.md](references/roadmap.md) for standing follow-up ideas (feedback loop, watch mode, vertical query packs, etc.) and surface any that fit this run as an optional next step — propose them, don't build them without explicit user approval.

## Research Tools

This skill uses the following Claude Code / OpenCode tools:

- **`websearch`** — search the web for public pain signals, demand signals, and timing signals across forums, social posts, reviews, GitHub issues, and company pages.
- **`webfetch`** — fetch specific URLs found during research to read full pages, extract evidence, and verify claims.
- **`playwright_browser_navigate`** / **`playwright_browser_snapshot`** — for interactive browsing when webfetch cannot reach gated content (use sparingly; respect paywalls and login walls).
- **`github_search_code`** / **`github_search_issues`** / **`github_get_file_contents`** — for analyzing public repositories, issues, feature requests, and project activity.
- **`bash`** — to run `scripts/generate_report.py` for the final HTML report.

Use `Task` agents for parallel research when multiple query buckets need simultaneous coverage.

## Three prospect types — classify before you score

Every lead you find is exactly one of these. Don't blend them into one undifferentiated list — that's what made earlier reports feel generic (segments and companies forced through an "opener" field that didn't apply, scored on dimensions like "reachability" that don't mean the same thing for a person vs. an audience vs. an org).

| Type | What it is | Classification test | Next action |
|---|---|---|---|
| **Individual** | One specific, addressable person | Is there a real name or stable handle you could plausibly reply to, DM, or comment at? | Outreach opener + follow-up sequence |
| **Segment** | An audience, community, or repeated pattern — not one person | Does the evidence describe a pattern across many people, or search/demand intent with no single addressable person? | Content/GTM angle (SEO, ASO, community presence) |
| **Company** | A named organization evaluated as an account or partner | Is the value in the org's assets (customer base, platform, program) rather than one person's reply? | BD/partnership pitch |

**Edge case:** a solo maintainer or one-person company who posts publicly and is personally reachable is an **Individual** — a person is always the more actionable unit when one is available. Only classify as **Company** when what matters is the organization itself (its developer platform, its partnerships program, its customer base) and there's no single person's public post to reply to.

Log every classification call that wasn't obvious in the `limits` array.

## Structured Output

The skill produces a JSON artifact that feeds the report generator. Every field below is required unless marked optional. The agent must populate this JSON before calling the report script.

```json
{
  "title": "string — short product name",
  "product": "string — one-line product description",
  "product_url": "string — product URL",
  "target_customer": "string — primary ICP description",
  "adjacent_icp": "string — secondary ICP (optional)",
  "search_scope": "string — e.g. 'Public English-language sources, last 12 months'",
  "generated_at": "string — ISO date YYYY-MM-DD",
  "methodology": "string — 1-2 sentence summary of research approach",
  "search_queries_used": ["string — each query issued during research"],
  "sources_consulted": ["string — each source URL or platform visited"],
  "verdict": "string — whether the startup has reachable early-customer signals",
  "individuals": ["See individual schema below"],
  "segments": ["See segment schema below"],
  "companies": ["See company schema below"],
  "patterns": ["See pattern schema below"],
  "outreach_plan": "See outreach plan schema below",
  "competitive_context": "See competitive context schema below (optional)",
  "limits": ["string — missing evidence, assumptions, and classification calls"]
}
```

At least one of `individuals`, `segments`, `companies` must be non-empty. Omit an array entirely rather than including it empty.

### Individual schema

```json
{
  "name": "string — real name or stable public handle",
  "stage": "string — High intent | Problem aware | Trigger present | Potential fit",
  "score": "number 0-100",
  "pain_signal": "string — the specific public pain or demand signal",
  "evidence": "string — what was observed and where",
  "why_fit": "string — why the product solves their stated problem",
  "why_now": "string — what timing trigger makes this relevant today",
  "source_title": "string — title of the source page or post",
  "source_url": "string — valid URL to the public source",
  "source_type": "string — Forum | Social post | Review | GitHub issue | Company page | Changelog | Job post | Directory | Other",
  "signal_date": "string — publication date if visible, else 'Date unavailable'",
  "suggested_channel": "string — recommended outreach channel, or 'No public reply/DM channel exists' if none",
  "opener": "string — suggested first message under 90 words, or omit if no channel exists",
  "follow_up_sequence": ["string — 2-3 follow-up messages for the outreach companion skill"],
  "caution": "string — risk or caveat before outreach",
  "competitor_mentioned": "string — competitor they currently use or mentioned (optional)",
  "dimensions": {
    "pain_strength": "number 0-5",
    "product_fit": "number 0-5",
    "timing": "number 0-5",
    "reachability": "number 0-5",
    "evidence_quality": "number 0-5"
  }
}
```

If `suggested_channel` is "No public reply/DM channel exists," omit `opener` and `follow_up_sequence` rather than writing "N/A" — the report generator treats a missing field as not applicable, not a filled-but-empty one.

### Segment schema

```json
{
  "name": "string — short segment name, e.g. '[Competitor] comparison-shoppers'",
  "stage": "string — High intent | Problem aware | Trigger present | Potential fit",
  "score": "number 0-100",
  "pain_signal": "string — the repeated pain or demand pattern",
  "evidence": "string — what was observed and where (aggregate, not one post)",
  "why_fit": "string — why the product solves this pattern's job-to-be-done",
  "why_now": "string — what makes this pattern current",
  "source_title": "string",
  "source_url": "string",
  "source_type": "string",
  "signal_date": "string",
  "content_angle": "string — the searchable or shareable angle to take (see references/research-framework.md)",
  "target_keywords": ["string — search terms this segment actually uses"],
  "suggested_channels": ["string — e.g. SEO/blog, ASO, Reddit reply-when-relevant, YouTube comparison"],
  "proof_points": ["string — evidence-backed claims to use in the content"],
  "caution": "string",
  "competitor_mentioned": "string (optional)",
  "dimensions": {
    "pain_strength": "number 0-5",
    "product_fit": "number 0-5",
    "timing": "number 0-5",
    "evidence_quality": "number 0-5"
  }
}
```

### Company schema

```json
{
  "name": "string — organization name",
  "role": "string — Potential customer account | Integration/distribution partner | Expansion partner",
  "stage": "string — High intent | Problem aware | Trigger present | Potential fit",
  "score": "number 0-100",
  "pain_signal": "string — the product gap or business trigger",
  "evidence": "string — what was observed and where",
  "why_fit": "string — the combined value proposition: what this unlocks for both sides",
  "why_now": "string — the trigger event or timing signal",
  "source_title": "string",
  "source_url": "string",
  "source_type": "string",
  "signal_date": "string",
  "execution_path": "string — Self-serve program | Warm BD | Cold BD",
  "contact_path": "string — the public channel (e.g. 'self-serve developer platform signup,' 'corporate partnerships page') — never a scraped personal contact",
  "bd_angle": "string — suggested opening pitch, under 90 words",
  "what_to_propose": "string — the concrete first ask",
  "caution": "string",
  "dimensions": {
    "strategic_fit": "number 0-5",
    "timing": "number 0-5",
    "execution_ease": "number 0-5",
    "evidence_quality": "number 0-5"
  }
}
```

### Pattern schema

```json
{
  "title": "string — short pattern name",
  "count": "number — how many prospects (any type) show this pattern",
  "insight": "string — what this means for positioning or outreach"
}
```

### Outreach plan schema

```json
{
  "angle": "string — the core outreach strategy",
  "first_step": "string — what to do first",
  "follow_up": "string — what to do after initial contact",
  "success": "string — what success looks like in 7 days",
  "channels_to_prioritize": ["string — ranked list of outreach channels"],
  "personalization_notes": "string — how to personalize beyond templates"
}
```

### Competitive context schema

```json
{
  "top_competitors": ["string — 3-5 competitors the prospects likely use"],
  "switching_barriers": "string — what makes switching hard",
  "differentiation_angle": "string — the clearest reason to choose this product instead"
}
```

## Workflow

### 1. Understand the product

- Inspect the supplied URL, repository, landing-page copy, or product description using `webfetch` or `playwright_browser_*`.
- Identify the product, outcome, buyer, user, price or buying motion, geography, and strongest use case.
- Define one primary ICP, one adjacent ICP, pain triggers, positive signals, and disqualifiers.
- Map the competitive landscape: who are the 3-5 products prospects likely already use.
- Infer missing context when safe and label the inference. Ask one concise question only when ambiguity would materially change the search.
- Log every inference in the `limits` array so the user knows what was assumed.
- If the product has zero paying customers yet (pre-launch, pre-revenue, or stated directly by the user), apply [references/research-framework.md#zero-sales-priority-mode](references/research-framework.md#zero-sales-priority-mode) for the rest of the run — it changes how Individuals are weighted and what the seven-day plan should lead with. This applies to any product category, not a specific one.

### 2. Build a public-signal search plan

Before writing generic queries, check [references/query-packs/](references/query-packs/README.md) for a pack matching the product's vertical (devtools, health/wellness, marketplace/SaaS) and start from its tuned buckets and source mix instead of the generic list below. Still cover anything a pack doesn't address using the generic buckets.

If `outcomes.jsonl` exists from a prior run on this product (see step 7), run `python3 <skill_dir>/scripts/recalibrate.py outcomes.jsonl` first and weight this run's queries toward the source types and buckets it flags as outperforming.

Search current public sources for:

- Explicit tool or alternative requests
- First-person descriptions of the target problem
- Manual workflows and repeated workaround complaints
- Migration, churn, or competitor-frustration signals
- Public company changes that create timing, such as hiring, launching, expanding, or adopting a relevant workflow
- Competitor switching signals: cancellation posts, migration threads, feature-gap complaints
- Budget and procurement signals: "justify the spend," "need ROI," "looking for free alternative"

Use `websearch` with multiple query angles and source types. Prefer original pages over search snippets. For each result, use `webfetch` to read the full page and extract evidence. Record the source URL, source type, publication date when visible, and the exact evidence supporting qualification.

**Record every query issued** in `search_queries_used` and every source visited in `sources_consulted`. This creates an audit trail.

### 3. Research safely

- Use public, intentionally shared professional or business information only.
- Do not bypass login walls, paywalls, access controls, rate limits, or robots restrictions.
- Do not use data brokers, leaked datasets, private groups, personal email discovery, phone enrichment, or sensitive personal information — this applies identically to Company prospects. A "contact path" for a company must be a public, self-serve channel (developer platform signup, partnerships page, published BD contact) — never a scraped executive's personal email or an inferred direct line.
- Do not infer protected traits or target people using health, financial hardship, political belief, sexuality, religion, or other sensitive attributes.
- Prefer companies, public professional profiles, public requests, and community posts relevant to the product.
- Quote minimally and paraphrase by default. Link every material pain or timing signal.

### 4. Classify, qualify, and deduplicate

For each candidate, classify as Individual, Segment, or Company using the test in the table above, then score using the matching dimension set (see [references/research-framework.md](references/research-framework.md)):

- **Individual:** pain strength, product fit, timing, reachability, evidence quality.
- **Segment:** pain strength, product fit, timing, evidence quality.
- **Company:** strategic fit, timing, execution ease, evidence quality.

Remove duplicates and weak matches. A prospect without a cited pain, need, or timing signal is only a speculative fit and must not appear in the primary shortlist.

**Deduplication rules:**
- Same person posting in multiple threads: keep the strongest signal, note the other in evidence.
- Same company with multiple contacts: classify as Company (org-level) unless one named person is the clear entry point, in which case also list that person as an Individual and cross-reference.
- Similar pain but different industry: keep as one Segment if the job-to-be-done is identical; split if only surface-level overlap.

Never claim that a prospect is interested, has consented, or will buy. Label the output "potential customer based on public signals."

### 5. Draft the next action — never send or execute it

- **Individual:** recommend the most natural channel already associated with the source, write one opener grounded only in cited public context, and 2-3 follow-up variations for the outreach companion skill. If no public reply/DM channel exists, say so and omit the opener rather than inventing one.
- **Segment:** write a content angle (searchable, shareable, or both — see references/research-framework.md), target keywords, suggested channels, and the proof points to cite. This is a content/GTM brief, not a message to send.
- **Company:** write a BD angle (the combined value proposition — what this unlocks for both sides), the public contact path, and a concrete first ask. This is a partnership pitch, not a cold-email drip sequence.

Across all three: avoid pretending to know the person or organization, overstating familiarity, or mentioning unrelated private details. Do not send messages, submit forms, connect, follow, comment, apply to a program, or create CRM records unless the user separately requests and authorizes that action.

### 6. Produce the report

Lead with the most actionable evidence. Use this order:

1. **Verdict** — whether the startup has reachable early-customer signals.
2. **ICP** — buyer, job, trigger, and disqualifiers.
3. **Best in category** — the strongest Individual, Segment, and Company (up to three separate call-outs — do not force a single cross-type "top prospect," since a person, an audience, and a company aren't ranked on the same scale).
4. **Individuals** — people to message: source, pain signal, fit score, stage, channel, opener.
5. **Segments** — markets to target: pain pattern, fit score, content angle, keywords, channels.
6. **Companies** — partners to pitch: pain/gap, fit score, execution path, contact path, BD angle.
7. **Repeated patterns** — pains and triggers appearing across prospects of any type.
8. **Competitive context** — what prospects currently use and where this product wins.
9. **Seven-day outreach plan** — a manual, low-volume validation sequence.
10. **Research audit** — queries issued, sources consulted, and methodology notes.
11. **Limits** — missing evidence, assumptions, and classification calls that must be confirmed through real conversations.

Create a standalone HTML report unless the user explicitly requests chat-only output:

1. Write structured JSON following the schema above and in [references/report-artifact.md](references/report-artifact.md).
2. Save the JSON to a temp file: `analysis.json` in the workspace.
3. Run `python3 <skill_dir>/scripts/verify_sources.py analysis.json --apply` and review the output. It fetches every `source_url` (routing `reddit.com`/`www.reddit.com` through their `old.reddit.com` equivalent — see [references/research-framework.md](references/research-framework.md#source-mix) for why) and fuzzy-matches the cited `evidence` against the live page — this catches dead links and evidence paraphrased from a search snippet that self-graded `evidence_quality` scores miss. `--apply` makes the cleanup automatic and robust instead of manual: it rewrites `analysis.json` in place, dropping any prospect whose source came back `UNREACHABLE`/`INVALID_URL` and adding an unverified-evidence caution to anything `BOT_BLOCKED` (a platform that 403/429s script fetches outright, e.g. a bare API endpoint or LinkedIn/X/Glassdoor/Indeed — not necessarily a dead link). For `LOW_MATCH` entries — not auto-fixed, since these need judgment — re-read the source and either tighten the `evidence` quote or note the mismatch in `limits`; a low match isn't always wrong (paraphrase, page redesign), but it must not pass silently.
4. Run `python3 <skill_dir>/scripts/generate_report.py analysis.json outputs/signal-scout-report.html` (use the absolute path to the skill's scripts directory).
5. Verify every section rendered, source links resolve, scores and dimensions match the type they belong to, and no card shows an empty/"N/A" field.
6. Return a clickable absolute file link in the final response.

**Error recovery:** If the report script fails, read the error message, fix the JSON (most common issue: missing required fields, invalid URLs, or a prospect in the wrong type array), and retry once. If it fails again, output the JSON directly and note the script issue.

**Caching:** If the product URL was already analyzed in this session and the user asks for a refresh, re-run only the search phase. If they ask for the same product, reuse cached research and re-score only if new signals appeared.

**Storage convention (enables steps 7-8 below):** save each run's JSON at `outputs/<product-slug>/analysis-<YYYY-MM-DD>.json` (slug the product name, e.g. `outputs/acme-crm/analysis-2026-07-14.json`) instead of a single throwaway `analysis.json`, whenever the user is likely to revisit this product. This is what makes `diff_reports.py` and `recalibrate.py` useful later — a one-off `analysis.json` in a temp dir works fine for a single-shot ask, but don't use it for a product the user is actively working.

### 7. Watch mode (offer, don't assume)

If the user is actively working a product rather than doing a one-off check, offer to schedule a recurring re-run via the `schedule` skill (e.g. weekly). Each scheduled run should: re-run only the search phase (per the caching rule above) against the same product, save the new snapshot per the storage convention, then run `python3 <skill_dir>/scripts/diff_reports.py outputs/<slug>/analysis-<previous-date>.json outputs/<slug>/analysis-<current-date>.json` and report only the new prospects, dropped prospects, and growing patterns it prints — not the full report again. This needs explicit user opt-in since it creates a standing scheduled job.

### 8. Close the loop with outcomes (when available)

signal-scout's scores are self-graded — there is no ground truth until someone acts on a prospect. If the user later reports what happened after outreach (via [signal-outreach](https://github.com/OrenSegal/first-to-first-sale) or directly), log it:

```bash
python3 <skill_dir>/scripts/log_outcome.py outputs/<slug>/outcomes.jsonl \
  --name "<prospect name>" --type individual --source-type "Forum" \
  --query-bucket pain --score 82 --outcome replied --date <YYYY-MM-DD>
```

`--outcome` is one of `replied`, `no_reply`, `converted`, `not_pursued`. Do this opportunistically, not by asking the user to fill out a form — if they mention a reply or a conversion in passing, log it. On the *next* research run for the same product, step 2 already checks for this file and runs `recalibrate.py` automatically.

## Modes

Two independent axes — combine them freely.

**`--depth`** controls how much research happens:
- **quick**: up to 5 total prospects across all types. Fastest path to action.
- **standard** (default): up to 10 total prospects.
- **deep**: up to 20 total prospects, with repeated pain patterns mapped across types.

**`--focus`** controls which prospect types get emphasized (default: `all`):
- **all**: research and report all three types as the evidence supports.
- **individuals**: prioritize addressable people over segments or companies.
- **segments**: prioritize audience/demand patterns — best when the goal is content/GTM strategy, not 1:1 outreach.
- **companies**: prioritize B2B accounts and partnership targets.
- **competitor-chasers**: within any focus, specifically surface people, segments, or companies actively switching away from a named competitor.
- **design-partners**: within any focus, prioritize prospects likely to test and give feedback over immediate buyers.

Use `standard` + `all` by default.

## Completeness Checklist

Before delivering, verify every item:

- [ ] Product brief is complete (product, buyer, job, trigger, alternatives, disqualifiers).
- [ ] At least 3 search query buckets were used (explicit demand, pain, workaround, switching, timing).
- [ ] Every prospect was classified as exactly one of Individual / Segment / Company, with non-obvious calls logged in `limits`.
- [ ] Every prospect has a source URL that resolves.
- [ ] Every prospect has a score with the dimension set matching its type (5 for Individual, 4 for Segment, 4 for Company).
- [ ] No Individual card has an "N/A" opener — either a real opener or the field is omitted with a stated reason.
- [ ] Every Segment has a content angle, keywords, and channels — not an outreach opener.
- [ ] Every Company has an execution path, a public contact path, and a BD angle — not a 4-touch drip sequence.
- [ ] Deduplication was performed (no repeat prospects, no person double-counted as their own company without cross-reference).
- [ ] Patterns are backed by 2+ prospects each.
- [ ] Competitive context identifies 3-5 real competitors.
- [ ] Research audit logs queries and sources.
- [ ] Limits array discloses all assumptions, missing evidence, and classification calls.
- [ ] Report was generated and the file link works.
- [ ] `scripts/verify_sources.py --apply` was run and every `UNREACHABLE`/`INVALID_URL` result was resolved (prospect auto-dropped or source fixed) before the final report.

## Quality bar

- Link every prospect to at least one meaningful public signal.
- Prefer ten strong matches over a long generic lead list.
- Make uncertainty and stale evidence visible.
- Personalize from the source, not from invented assumptions.
- Keep outreach manual and respectful.
- Treat the shortlist as a research hypothesis, not a customer database.
- Log your research process so someone could reproduce it.
- Name the competitors so the user can validate the landscape.
- Never force a prospect into the wrong type just to keep one list tidy — a mis-typed prospect gets the wrong next action.

Base directory for this skill: file:///Users/orensegal/Documents/GitHub/first-to-first-sale/signal-scout
Relative paths in this skill (e.g., scripts/, references/) are relative to this base directory.
