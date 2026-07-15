# signal-scout: monetization plan (solo-founder edition)

This is the business plan behind `mcp-server/` and `skills/signal-scout/scripts/usage_stats.py`.
It exists so decisions about pricing, hosting, and payment rails get made
deliberately, gated on real evidence — not because "the whole 9 yards" means
build everything at once. For a solo founder, the biggest risk isn't
building the wrong feature; it's taking on a cost center (a hosted service
you pay for) before you know anyone will pay for it.

## 0. The thing that's easy to miss: today's cost structure is already great

signal-scout ships as a skill a user installs into *their own* Claude Code
session. Every research run's API cost is paid by the *user's* Claude
subscription or API key — not yours. You have **zero marginal cost** on
every free install today. That's not a placeholder state to "fix" by adding
a hosted product; it's a genuinely strong starting position, and the plan
below is explicit about which phases keep that property and which phases
give it up (hosting a product you pay for is a real financial commitment —
see Phase 2).

## 1. The value-add test — apply this before building or pricing anything

**Does this feature do something a bare "hey Claude, find me customers for
X" prompt inside Claude Code (or any capable agent) doesn't already do for
free?** If not, it isn't a product, it's a wrapper — and it's especially not
something to charge another agent for, since the most likely caller of the
MCP server *is* an agent like Claude Code with the same tools built in.

Run every feature through this before investing in it:

**Doesn't survive the test** (Claude Code and comparable agents already do
this): searching and fetching the web, general reasoning, summarizing what
it found. None of that is a moat — it's the commodity layer every capable
agent ships with today.

**Survives the test** (a bare LLM call doesn't do this reliably, or at all):
- The Individual/Segment/Company classification discipline and per-type
  scoring dimensions — a rubric almost nobody would think to ask for, and
  one a model won't apply consistently without it even if asked.
- Automated source verification (`verify_sources.py` actually fetches every
  cited URL and fuzzy-matches the evidence against the live page) — Claude
  won't double-check its own citations against a hallucinated or dead link
  on its own.
- The portable HTML report artifact — a shareable deliverable, not ephemeral
  chat output.
- Outcome-based recalibration that compounds across runs — stateful across
  sessions, not something a single conversation has.
- Patching real gaps in the platform's own tools where they exist — e.g.
  Claude Code's `webfetch` refuses `reddit.com` outright as a tool-level
  policy; `verify_sources.py`'s `old.reddit.com` rewrite is a genuine fix for
  something the platform doesn't do on its own.

This is why `mcp-server/` ships two tools, not one: `classify_and_score`
(no web tools, just the four things above, applied to findings the caller
already gathered) is the one that survives the test. `find_first_customers`
(does its own web research) only survives the test for a caller that has no
web tools of its own — running a second research agent to duplicate
capability the caller already has isn't a value-add, it's marked-up compute.
See `mcp-server/README.md` for the split. Apply this same test to every
future feature idea, not just the ones already built.

## 2. Cost model — what a run actually costs (if you're the one paying)

Using Claude Sonnet 5 pricing ($2/$10 per MTok intro through 2026-08-31,
cache reads at ~0.1x, cache writes at ~1.25x — see the `claude-api` skill's
pricing table) and a realistic token trace for one research run (~15-25
`web_search`/`web_fetch` calls, ~10 prospects):

| Depth | Rough cost per run (find_first_customers) |
|---|---|
| quick (≤5 prospects) | $0.10 – $0.30 |
| standard (≤10, default) | $0.30 – $0.75 |
| deep (≤20) | $1 – $3 |

`classify_and_score` costs meaningfully less than the table above for the
same depth — it skips the web-tool loop entirely, so it's a single
structured-output call against findings already in the prompt, not a
multi-turn research agent. `mcp-server/usage_meter.py` computes the real
number per call once you're running the server yourself — don't re-derive
either figure by hand once that's live.

## 3. Comparable pricing — what the market already pays for this job

B2B intent-data / monitoring tools doing a similar job (surface accounts
worth acting on) price from ~$99/mo (visitor-ID tools) up to $10-25K/year
(Warmly, G2 Buyer Intent) to $50-130K/year (Bombora, 6sense) — see the
research in the prior turn's chat for sources. signal-scout's watch mode is
a leaner version of the same job using public signals instead of paid
firmographic feeds, so a defensible indie price sits well below enterprise
tiers but far above the COGS floor: **$29-99/mo per tracked product** is a
plausible starting point once Phase 1 (below) shows repeat usage is real.

At $1/run COGS and a weekly cadence (~$4-16/mo COGS per tracked product),
gross margin at that price is 70-95%+. Margin was never the risk here —
demand is.

## 4. The moat — what actually protects this, since the code is MIT and public

Signal-scout's code is fully open source. Anyone can clone it, fork it,
rebrand it. **The moat can't be the code — it has to be something a fork
starts from zero on.** Two things fit, and both are buildable by one person
— and both are, not coincidentally, the same things that survive the
value-add test in Section 1:

**a) Compounding outcome data.** `log_outcome.py` / `recalibrate.py` already
capture which source types and query buckets actually convert (reply, no
reply, converted) per product. Today that lives in each user's local
`outputs/<slug>/outcomes.jsonl` — useful to them, but resets to zero for
anyone who forks the repo. If those outcomes are aggregated centrally
(anonymized: source type + query bucket + outcome, never the prospect or the
product) as usage grows, next month's scoring gets measurably better for
everyone on the hosted product — and a fork of the code has none of that
history. This is the same shape as Plaid's fraud models or Grammarly's
writing model: the code isn't the secret, the accumulated usage signal is.

**b) Hosted convenience, not hosted secrecy.** This is the standard
open-core playbook (Sentry, GitLab, n8n, Plausible): the code stays open —
it's free marketing, SEO, and trust — and the paid product is "don't make me
run Python scripts, manage a `cron` job, or read `verify_sources.py` output
myself." Most people who'd pay for watch mode won't self-host it even though
they legally could, the same way most Sentry users don't self-host Sentry.
This needs exactly one deployed instance, run by you — not a platform team.

Distribution position (being the known name for "first customer discovery
via public signals") and workflow lock-in with the paired `signal-outreach`
skill are real secondary moats, but they compound slowly and aren't
buildable on demand — treat (a) and (b) as the two to actually invest in.

## 5. Phased plan, gated on evidence

Each phase has an explicit "don't proceed until" condition. This is the
actual discipline for a solo founder: it's cheap to keep shipping free,
zero-marginal-cost improvements (Phase 0); it's a real financial and time
commitment to run a paid hosted service (Phase 2+) — don't cross that line
speculatively.

### Phase 0 — done. Keep doing this; it's free.
Free skill distribution (npm, plugin marketplace), source verification,
vertical query packs, the outcome-feedback loop. Zero marginal cost to you.
No gate — just keep shipping.

### Phase 1 — validate repeat usage (now)
Run `skills/signal-scout/scripts/usage_stats.py` against your own
`outputs/` periodically, and once `signal-outreach` users start logging
outcomes, watch the repeat rate it reports. **Gate: don't price a
subscription or build billing until you see a real, stable repeat-usage
pattern across multiple products** — a single person re-running one product
twice isn't a signal. If nobody re-runs, watch mode isn't the answer; a
better one-shot report or a different vertical query pack might be.

### Phase 2 — hosted watch mode (only after Phase 1 clears)
Turn the recurring re-run + `diff_reports.py` flow into an actual scheduled,
hosted product (Claude's Managed Agents scheduled deployments are the
natural mechanism — see the `claude-api` skill's
`managed-agents-scheduled-deployments` docs). **This is the phase where you
start paying Anthropic for API usage instead of the user** — budget for it
like a real COGS line, not a rounding error, and price with the Section 2/3
numbers in hand before launching.

### Phase 3 — B2A distribution via the MCP server (parallel track, already scaffolded)
`mcp-server/` wraps the research/classification workflow as tools other
agents can call directly — reach for `classify_and_score` by default (see
Section 1); `find_first_customers` is the fallback for callers with no web
tools of their own. **Gate before making it publicly reachable: a payment
gate or a raised, deliberate `SIGNAL_SCOUT_DAILY_CALL_CAP`** (it defaults to
20/day specifically so this can't rack up an unbounded bill by accident —
see `mcp-server/server.py`). Sequence: (1) smoke-test with a real API key
privately, (2) pick a payment rail — x402 (crypto micropayments, good for
sub-cent per-call pricing, which `classify_and_score` calls often are) vs
Stripe's Machine Payments Protocol (session-based fiat billing, better if
per-call amounts are more like $0.50+ and you'd rather not touch crypto) —
this is a real research task pending your choice, not something to default
silently, (3) host it somewhere reachable (a small always-on box, or Managed
Agents), (4) list it in an MCP registry so other agents can find it. Do not
skip step (2)'s gate — it's the same "don't take on a cost center
speculatively" discipline as Phase 2.

## 6. What NOT to build yet (efficiency, not neglect)

- A full dashboard/UI — `usage_stats.py` and `verify_sources.py`'s stdout
  are enough until Phase 1 clears.
- Multi-tenant auth, teams, RBAC — a solo founder with a handful of paying
  customers doesn't need this; add it when support tickets ask for it.
- A custom payment processor integration beyond x402/Stripe MPP — both are
  turnkey; don't build billing infra from scratch.
- Growth/creator-economy plays from `references/roadmap.md`'s "invisible-user"
  angle — that's a report feature for signal-scout's *output*, unrelated to
  monetizing signal-scout itself; don't conflate the two.
- Any feature that fails Section 1's value-add test, however good the idea
  sounds in isolation — if it's just "Claude Code with extra steps," it's
  not worth building or charging for.

## 7. Immediate next actions

1. Run `usage_stats.py` against real `outputs/` data as it accumulates —
   this is the single fact that determines whether Phase 2 is worth doing.
2. Smoke-test `mcp-server/` with a real `ANTHROPIC_API_KEY` on one real
   product before trusting the schema/pipeline for anything real — try
   `classify_and_score` first, since it's the tool that's actually meant to
   carry the product.
3. Decide x402 vs. Stripe MPP only once (2) shows repeat usage — don't
   research payment providers before there's a product to attach one to.
