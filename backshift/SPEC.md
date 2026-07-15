# Backshift — spec (draft, not yet built)

Status: **spec only**. Nothing in this directory runs yet. This exists to record
the idea, its scope, and its relationship to signal-scout before any code gets
written, following the same evidence-gated discipline as `../MONETIZATION.md`.

## What this is

A playbook-and-toolkit for running a **solo, managed "AI employee" service**
for small legacy-vertical businesses — the operator sells an always-on AI
that handles a specific job for a client (not a self-serve SaaS seat), priced
as a flat monthly retainer, with the client never touching models, tokens, or
infrastructure. Inspiration: Greg Isenberg's *Startup Ideas Podcast* episode
"The $1M+ Solo AI Agent Business," featuring Nick Vasilescu (Orgo) — general
research notes are recorded here in our own words for planning purposes; this
directory does not reproduce, and should not come to reproduce, the episode's
transcript.

## Why this is not signal-scout, and shouldn't become it

Signal-scout is a self-serve, low-touch, open-core **product**: install a
skill, run it, get a report, zero marginal cost to us. Backshift, as
described, is a high-touch, per-client, ongoing **service** — bespoke setup,
account management, and uptime responsibility per customer. Merging the two
under one roadmap would blur signal-scout's positioning and isn't a good use
of a solo founder's limited attention. They stay separate projects.

## Where they connect (the only two ties, deliberately kept narrow)

1. **Client acquisition.** If Backshift is pursued, `signal-scout` +
   `signal-outreach` are literally the tool for finding its first paying
   clients — businesses in the target verticals showing a real, current pain
   or timing signal for automating a specific role. This is dogfooding, not
   scope creep, and it feeds real outcome data back into signal-scout's own
   recalibration loop.
2. **Reliability engineering reference.** The operational problem Backshift
   has to solve — keep many customers' always-on automated agents running,
   detect failures, restart cleanly — is the same problem signal-scout's own
   *hosted* watch mode (`../MONETIZATION.md` Phase 2) eventually has to solve
   for its own scheduled runs. Revisit this directory's architecture notes
   when Phase 2 is actually being built, not before.

No other coupling is intended. Backshift does not depend on signal-scout's
code, and signal-scout does not depend on Backshift existing at all.

## The offer, in our own words

- **Sell a role, not a tool.** The pitch is "this handles job X for you," not
  "here's an AI agent platform." The buyer is paying to stop doing a task,
  the same way they'd pay a part-time hire — not to operate new software.
- **One flat price, unlimited use.** A single monthly retainer covering
  unlimited usage and support removes the friction of a client having to
  reason about tokens, seats, or overage — the same reason phone/internet
  flat-rate plans outsell metered ones for non-technical buyers.
- **Target legacy, non-regulated verticals first**: trades and professional
  services that run on manual, repetitive work but aren't already deep in
  compliance regimes — e.g. marketing agencies, law firms, insurance
  brokers, manufacturers, wholesalers, real estate. Avoid healthcare and
  finance to start: both carry compliance/liability overhead (HIPAA,
  licensing, audit trails) that turns a scrappy one-person service into a
  regulatory project before it has its first few clients.
- **Narrow scope per client.** One or a small handful of well-defined jobs
  per engagement, not an open-ended "AI does everything" promise — matches
  what a solo operator can actually stand behind on uptime and quality.

## Reference architecture (functional layers, not a fixed vendor list)

Whatever gets built should cover these functions — described generically so
the actual implementation isn't locked to any single vendor's product line:

| Layer | Job it does | Why it matters for a solo operator |
|---|---|---|
| Reasoning/orchestration | Runs the model, coordinates tool calls, manages session state across a long-lived task | This is "the agent" itself — needs to survive longer than one chat turn |
| Always-on runtime | An environment the agent keeps running in independent of the operator's own machine being online | A client-facing service can't go down when the founder closes their laptop |
| Delegated app access | Lets the agent act inside the client's actual tools (docs, calendars, CRM) without handing over the operator's personal credentials | Keeps blast radius and liability contained per client |
| Dedicated comms identity | A phone/email/chat identity that's the agent's, not the operator's personal one | Separates business and personal surface area; scales to many clients |
| Observability & reliability | Logs tool calls, costs, errors, and recurring failure patterns; restarts cleanly on failure | The single biggest operational risk in "I sell an always-on employee" is the employee going quiet |
| Durable external memory | Notes/context that persist outside any one chat session | An "employee" that forgets everything between sessions isn't credible |
| Market-signal research | Ongoing input on what a given vertical actually needs | This is where signal-scout plugs in, per the connection above |

## Open questions before any build starts

- Is there real founder appetite to run a high-touch service business at all,
  versus staying fully product-only? This spec doesn't answer that — it only
  exists so the option is scoped if the answer is yes.
- If pursued: which single vertical and which single job get picked first?
  Don't build the general platform before one real client is signed.
- Naming: **Backshift** — checked against npm (unclaimed) and general web
  search (no same-market collision found; one small, differently-spelled,
  different-industry business — outsourced back-office services for
  construction firms — uses a hyphenated near-variant of the name). Treat
  this as a good-faith check, not a substitute for a real trademark/domain
  search before committing to the name commercially.

## Non-goals for this spec

- Not a rewrite or extension of signal-scout's schema, scripts, or MCP
  server.
- Not a commitment to build anything — this is a placeholder for the idea,
  gated the same way every other roadmap item in this repo is: don't build
  until there's a concrete reason to (a specific client conversation already
  in progress is the trigger, not "this seems like a good idea").
