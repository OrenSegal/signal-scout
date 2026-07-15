# signal-scout: monetization plan (solo-founder edition, 2026-2027 outlook)

This is the business plan behind `mcp-server/` and `skills/signal-scout/scripts/usage_stats.py`.
It exists so decisions about pricing, hosting, gating, and payment rails get
made deliberately, gated on real evidence — not because "the whole 9 yards"
means build everything at once. For a solo founder, the biggest risk isn't
building the wrong feature; it's taking on a cost center, or gating away the
thing that actually drives distribution, before the evidence justifies it.

Last full competitive research pass: 2026-07 (see Section 4 for sourcing).

## 0. The thing that's easy to miss: today's cost structure is already great

signal-scout ships as a skill a user installs into *their own* Claude Code
session. Every research run's API cost is paid by the *user's* Claude
subscription or API key — not yours. You have **zero marginal cost** on
every free install today. That's not a placeholder state to "fix" by gating
things off; it's a genuinely strong starting position, and every decision
below is explicit about which layers keep that property and which take on
real cost or restriction.

## 1. The value-add test — apply this before building, pricing, or gating anything

**Does this feature do something a bare "hey Claude, find me customers for
X" prompt inside Claude Code (or any capable agent) doesn't already do for
free?** If not, it isn't a product, it's a wrapper — and it's especially not
something to gate, since restricting access to a wrapper just kills
distribution without creating real defensibility.

**Doesn't survive the test** (every capable agent already does this for
free): searching and fetching the web, general reasoning, summarizing what
it found.

**Survives the test** (a bare LLM call doesn't do this reliably, or at all):
the Individual/Segment/Company classification discipline and per-type
scoring dimensions; automated source verification (`verify_sources.py`
actually fetches every cited URL and fuzzy-matches the evidence); the
portable HTML report artifact; outcome-based recalibration that compounds
across runs; patching real gaps in platform tools (Claude Code's `webfetch`
refuses `reddit.com` outright — `verify_sources.py`'s `old.reddit.com`
rewrite is a genuine fix for something the platform doesn't do on its own).

This is also the test to apply to gating decisions (Section 7): gate what's
structurally scarce (data that only exists because many people used the
hosted product, infra you're paying to run), not what's merely convenient to
restrict. Restricting access to markdown instructions and Python scripts
doesn't make them scarce — it just makes them less-distributed.

## 2. Cost model — what a run actually costs (if you're the one paying)

Using Claude Sonnet 5 pricing ($2/$10 per MTok intro through 2026-08-31,
cache reads at ~0.1x, cache writes at ~1.25x) and a realistic token trace:

| Path | Rough cost per run |
|---|---|
| `find_first_customers` (own research), quick/standard/deep | $0.10 – $0.30 / $0.30 – $0.75 / $1 – $3 |
| `classify_and_score` (caller supplies findings) | a fraction of the above — no web-tool loop, a single structured-output call |

`mcp-server/usage_meter.py` computes the real number per call once the
server is running — don't re-derive it by hand.

## 3. Comparable pricing — the full landscape, not just one competitor

| Player | What they charge | Notes |
|---|---|---|
| Redreach | $19–99/mo (+ a $12 3-day pass) | Closest mechanism to us; no classification, no verification |
| Reddinbox | $39–99/mo | Cites sources, no typed classification |
| Syften | $30–120/mo | Already shipped MCP access (May 2026), same niche |
| Brand24 | $79–299/mo | Enterprise listening, full MCP server (Feb 2026) |
| Awario | $49–399/mo | API/agent access gated to $399/mo Enterprise |
| IdeaBrowser | $499–2,999/yr (~$42–250/mo) | Different market (ideation), reviewed weakness: unlinked claims |
| Trends.vc | ~$300–700/yr | Different market (curated editorial reports), no agent signal |
| Bombora / 6sense / Warmly | $10K–130K/yr | Enterprise intent data, way beyond solo-founder positioning |

Given signal-scout's actual comparable mechanism and buyer (indie
founders/small teams, not enterprise), the Redreach/Reddinbox/Syften band —
**$19–49/mo entry, scaling to $79–149/mo for a team/agency tier** — is the
grounded anchor, with a premium justified by being the only one in that band
that verifies and classifies. IdeaBrowser's $499+/yr tier confirms people
*will* pay meaningfully more than that for AI research output in this
neighborhood, but that's a different buyer (ideation, coaching, community) —
don't price against it directly.

## 4. Competitive landscape, 2026 — corrected and sourced

Research this pass covered IdeaBrowser, Trends.vc, Exploding Topics,
Redreach, Reddinbox, Syften, Brand24, Awario, and (for B2A context)
Apollo/Clay/Warmly/6sense/Bombora. One claim from an earlier draft of this
document was checked and **retracted**: IdeaBrowser has not been confirmed
to ship an official MCP connector — that traced back to a third party's
unrelated blog post. What *is* confirmed directly from his own posts: Greg
Isenberg (IdeaBrowser's founder) is the most vocal public evangelist for
"agents are the new customer, build for agents, MCP is your sales team" —
real quotes, no product evidence yet. Treat IdeaBrowser as a **fast-follower
risk** (huge audience, founder already telegraphing the exact move), not a
confirmed head start.

**Ideation lane** (not our market — don't compete here): IdeaBrowser,
Trends.vc, Exploding Topics. Exploding Topics is now owned by Adobe (via the
$1.9B Semrush acquisition, closed April 2026) and folded into an enterprise
SEO suite — effectively neutralized as a fast mover.

**Reddit/social monitoring lane** (closest mechanism, real whitespace
remains): Redreach, Reddinbox, Syften, Brand24, Awario. None of them do
typed classification (person/audience/company) or live citation
verification. Syften and Brand24 already ship MCP/agent access in this
exact niche — agent-callable access is becoming table stakes here fast (the
"just have an MCP server" differentiator has maybe a 12-18 month window
before it's assumed table stakes, and that window opened in early-mid
2026).

**Sales-intelligence lane** (better funded, different data model): Apollo,
Clay, Warmly, 6sense all shipped MCP/agent access in H1 2026. They operate
on owned/licensed contact and firmographic databases — a fundamentally
different, proprietary-data business, not live public-signal verification.
Bombora has no standalone MCP; it's embedded inside Warmly/6sense.

**What survives across every lane, unchanged**: nobody — not the ideation
tools, not the scrappy Reddit tools, not the funded sales-intelligence
platforms — combines typed Individual/Segment/Company classification with
per-type scoring *and* live verification of cited public evidence. That
combination is the moat (Section 6), and it doesn't erode as the MCP
landscape commoditizes around it.

## 5. B2A — real, but as distribution, not as a revenue line

Infrastructure and demand point in opposite directions here, and conflating
them was a mistake in an earlier pass of this document.

**Infrastructure is real and accelerating**: MCP servers hit 9,400 published
in Q2 2026 (+58% QoQ, three quarters running); Cloudflare and AWS both
shipped x402 edge support within two weeks of each other; the x402
Foundation counts Google, Visa, AWS, Circle, Anthropic, and Vercel as
members.

**Transactional demand is not there yet**: real x402 daily volume has been
reported around $28K against a multi-billion-dollar ecosystem valuation,
with roughly half of transactions flagged as wash-trading by one analytics
firm. Under 5% of published MCP servers are monetized at all. In the
specific B2B sales-intelligence MCP niche, there are only ~8 servers total,
and **not one of them charges per call** — Apollo, Clay, Warmly, and Brand24
all give MCP access away free as a value-add to their existing subscription.
A credible skeptic argues real B2B agentic commerce won't hit an inflection
point before 2028, citing unresolved trust/regulatory/insurance gaps.

**Conclusion**: keep the MCP server — it's table stakes for staying visible
as agent-native distribution normalizes, and every serious competitor above
is either shipping one or evangelizing one. But **do not build x402/Stripe
MPP per-call billing as a monetization plan right now** — that would be
payment infrastructure for demand that doesn't exist anywhere in this
category yet. Use the MCP server the way every one of these competitors
actually uses theirs: free distribution into the same paid core product
(Section 7), not a separate metered line. Revisit per-call billing only if
the landscape changes (watch: does anyone in the sales-intelligence niche
actually start charging per call?).

## 6. The moat — what actually protects this, since the code is MIT and public

Signal-scout's code is fully open source. Anyone can clone it, fork it,
rebrand it. **The moat can't be the code — it has to be something a fork
starts from zero on, and something that survives every competitor above
eventually shipping their own MCP server.** Two things fit:

**a) Compounding outcome data.** `log_outcome.py` / `recalibrate.py` already
capture which source types and query buckets actually convert. Today that
lives in each user's local `outputs/<slug>/outcomes.jsonl` — useful to them,
but resets to zero for anyone who forks the repo. Centralized (anonymized:
source type + query bucket + outcome, never the prospect or the product),
it compounds across every hosted user and a fork has none of that history.
This is the one piece of the business that's *structurally* hosted-only —
not because access is restricted, but because the value literally doesn't
exist until many people's usage accumulates in one place.

**b) Hosted convenience, not hosted secrecy.** The open-core playbook
(Sentry, GitLab, n8n, Plausible): the code stays open — free marketing, SEO,
trust — and the paid product is "don't make me run this myself." Most
people who'd pay for watch mode won't self-host it even though they legally
could.

Verification + typed classification (Section 1) is what makes the *product*
differentiated from every competitor; (a) and (b) above are what make the
*business* defensible once competitors catch up on features. All three
point the same direction: keep the code and the self-run path open, gate
the hosted/aggregate layer.

## 7. What's free vs. what's gated — the actual business model

The either/or in the brief — "make it a business while still offering the
skill/MCP, or gate everything if there's juice to it" — resolves cleanly
once you separate *the code* from *the hosted layer*:

**Stays free and open, permanently:**
- The skill (`skills/signal-scout/`) — install via npx/plugin marketplace,
  run in the user's own Claude Code session, their own API cost.
- The MCP server code (`mcp-server/`) — anyone can clone and self-host it
  with their own `ANTHROPIC_API_KEY`, for free, forever.
- `verify_sources.py`, `generate_report.py`, `usage_stats.py` — all of it.

**Why not gate these:** there's no real "juice" in restricting access to
markdown instructions and Python scripts — they're trivially copyable, so a
paywall here doesn't create defensibility, it just throws away the
distribution, SEO, and trust that make this a known name in the space at
all. This is also the layer we have no technical ability to meter anyway —
once installed, it runs in the user's own Claude Code session; there's
nothing to gate without DRM-style nonsense that contradicts an MIT license.

**Where the actual paid product lives — a hosted layer, gated because it's
genuinely scarce, not because we restricted it:**
- **Hosted watch mode** — scheduled re-runs + `diff_reports.py`, no cron/
  infra required from the user. Priced per tracked product, $19-49/mo entry
  (Section 3's anchor).
- **The centralized recalibration engine** — access to cross-user,
  anonymized source-type/query-bucket hit rates (Section 6a). This is the
  one feature that is *structurally* exclusive to the hosted product — a
  self-hosted fork starts at zero here even running identical code, because
  the value is the aggregate history, not the script.
- **Hosted MCP access for external agents** who don't want to run their own
  `ANTHROPIC_API_KEY`/infra — free up to `SIGNAL_SCOUT_DAILY_CALL_CAP` (today
  20/day, self-hosted), with a paid tier raising that limit once hosted.
  Per Section 5, this is priced as part of the same subscription, not
  metered per call.
- **Team/agency tier** ($79-149/mo) — multiple tracked products, higher API
  limits; only worth building once Phase 1 (below) shows individual watch
  mode has real repeat demand.

This is the same shape as every competitor in Section 4 that's monetizing
successfully: Sentry/GitLab-style open core, Apollo/Clay/Warmly-style "MCP
access bundled into the subscription, not sold a la carte." Nobody in this
space is winning by gating the tool itself — they're winning by hosting
convenience and owning data (theirs is contact data; ours is the outcome
history).

## 8. Phased plan, gated on evidence

### Phase 0 — done. Keep doing this; it's free.
Free skill + MCP server distribution, source verification, vertical query
packs, the outcome-feedback loop. Zero marginal cost. No gate — keep
shipping.

### Phase 1 — validate repeat usage (now)
Run `usage_stats.py` periodically. **Gate: don't build the hosted layer in
Section 7 until you see a real, stable repeat-usage pattern across multiple
products** — a single re-run isn't a signal.

### Phase 2 — hosted watch mode + recalibration engine (only after Phase 1 clears)
Build the two things Section 7 identifies as genuinely gate-able: scheduled
hosted runs, and the centralized recalibration engine. This is the phase
where you start paying Anthropic for API usage instead of the user — budget
for it as real COGS, price with Section 2/3 numbers in hand.

### Phase 3 — MCP server as distribution, not revenue (parallel, already scaffolded)
Keep `mcp-server/` free and self-hostable. If/when you host it publicly,
gate by raising `SIGNAL_SCOUT_DAILY_CALL_CAP` for paying subscribers rather
than building per-call billing (Section 5). **Competitive watch list**:
Redreach and Syften (closest, most agile — watch for either shipping typed
classification or source verification), Brand24 (fastest-moving MCP
shipper), and IdeaBrowser (fast-follower risk given Isenberg's public
positioning — watch for a shipped agent/MCP feature, not just more posts
about wanting one).

## 9. What NOT to build yet (efficiency, not neglect)

- A full dashboard/UI — `usage_stats.py` and stdout are enough until Phase 1
  clears.
- x402 / Stripe MPP integration — no evidence anyone is getting paid per
  call in this niche yet (Section 5). Revisit if that changes.
- Multi-tenant auth, teams, RBAC — add when support tickets ask for it.
- Any attempt to gate or DRM the open skill/MCP code itself — no juice
  there, only distribution loss (Section 7).
- Any feature that fails Section 1's value-add test, however good it sounds.

## 10. Immediate next actions

1. Run `usage_stats.py` against real `outputs/` data as it accumulates —
   the single fact that determines whether Phase 2 is worth building.
2. Smoke-test `mcp-server/` with a real `ANTHROPIC_API_KEY` — try
   `classify_and_score` first.
3. Once Phase 1 clears, build hosted watch mode + the recalibration engine
   before touching payment rails of any kind.
4. Keep an eye on the Section 8 competitive watch list roughly quarterly —
   this space is moving fast enough that a 2026-07 snapshot won't hold
   through 2027 unexamined.

## 11. Related, but deliberately separate: `../backshift/`

`backshift/SPEC.md` records a different idea — a high-touch, per-client
managed-AI-employee *service* business, as opposed to signal-scout's
self-serve *product*. It's a spec only, not built, and not part of
signal-scout's roadmap. The only intended connections: it would use
signal-scout + `signal-outreach` to find its own first clients (dogfooding),
and its reliability-engineering notes are a reference for signal-scout's own
Phase 2 hosted watch mode, once that's actually being built. Don't let it
absorb roadmap attention beyond that until there's a concrete reason to.
