# Roadmap: what's built, and what's still a per-run offer

Every item below is now implemented as scripts + workflow steps in
SKILL.md — none of it runs automatically. Scan this list after delivering a
report and offer, in one or two sentences, whichever items fit the current
product; skip the ones that clearly don't apply (e.g. don't pitch "watch
mode" for a one-off competitor teardown the user called a one-time check).
Only *turn on* an item (schedule a job, start logging, add a pack) when the
user says yes — the mechanism existing doesn't mean it's opted into.

## 1. Outcome feedback loop — shipped, opt-in per product

`scripts/log_outcome.py` appends replied/no_reply/converted/not_pursued
records to `outputs/<slug>/outcomes.jsonl`. `scripts/recalibrate.py` reads
that file and reports which source types and query buckets are
outperforming or underperforming, so the next research run (SKILL.md step 2)
can weight toward what's actually converting instead of trusting self-graded
scores alone. Wired in as SKILL.md step 8. Propose logging once the user is
also using signal-outreach and reports back a real outcome — don't ask them
to fill out a form proactively, just log it when they mention one.

## 2. Automated source verification — shipped, always runs

`scripts/verify_sources.py` fetches every `source_url` and fuzzy-matches the
cited evidence against the live page. Required in the workflow (SKILL.md,
report-generation step 3) — nothing to propose, just don't skip it.

## 3. Watch mode / recurring scout — shipped, opt-in per product

`scripts/diff_reports.py` compares two dated snapshots and prints only new
prospects, dropped prospects, and growing patterns. Wired as SKILL.md step 7,
paired with the `schedule` skill for the recurring trigger. Offer this once
a user is clearly tracking a product over time rather than doing a single
check — it creates a standing scheduled job, so it needs explicit opt-in
every time, not just the first time it's offered.

## 4. Vertical query packs — shipped, extend on repeated signal

`references/query-packs/` ships three starting packs: devtools, health &
wellness, marketplace/SaaS. SKILL.md step 2 checks this directory before
falling back to generic buckets. Only propose *adding a new pack* after 2+
runs in the same untracked vertical show a repeatable pattern in which
queries/sources actually produced qualified prospects — don't write one from
a single run, and don't re-propose the three packs that already exist.

## 5. Scoring recalibration — shipped, data-gated

`recalibrate.py` (see item 1) is the recalibration mechanism — it surfaces
per-bucket/per-source hit rates once ≥3 outcomes are logged for a group
(`--min-samples`, default 3). The freshness decay function in
research-framework.md ("Signal freshness") is still a fixed step function
uniform across signal types; if outcome data clearly shows one signal type
decays slower or faster than the schedule assumes (e.g. hiring posts staying
relevant longer than forum complaints), propose editing that section — but
only once outcome data justifies it, not speculatively.
