# Compliance posture

signal-scout is compliant-by-construction with the tightening GDPR/CCPA stance on B2B prospecting data, because of what it structurally does not do. This page states that posture so a user — or their client — can point at it.

## What signal-scout never does

- **No data brokers, no scraped contact databases.** Prospects come from public web search and public pages only. There is no enrichment API, no purchased list, no email-finder.
- **No personal contact discovery.** No personal email addresses, phone numbers, or home addresses — ever. An Individual's `suggested_channel` is the public channel already attached to their own post (reply, DM on the platform they posted on). A Company's `contact_path` must be a public, self-serve channel (partnerships page, developer program), never a scraped executive contact.
- **No bypassing access controls.** No login walls, paywalls, private groups, rate-limit evasion, or robots violations. When a platform blocks automated reading (e.g. Reddit), the claim is downgraded to a disclosed lower-confidence tier, not scraped harder.
- **No protected-trait targeting.** No inference or use of health status, financial hardship, political belief, religion, sexuality, or other sensitive attributes — for any prospect type.
- **No automated outreach.** signal-scout drafts; a human sends. Nothing is ever sent, submitted, followed, or connected automatically.

## What signal-scout affirmatively does

- **Every claim discloses its source.** Every prospect and battlecard entry carries a `source_url`, and `verify_sources.py` re-fetches it to confirm the cited evidence is on the page before the report ships. Under GDPR's legitimate-interest basis for B2B outreach, being able to tell a person *where you got their information* is a requirement — a signal-scout report has that answer built into every card.
- **Data minimization by design.** A report contains what a person or company published publicly, quoted minimally, plus analysis. No profile assembly beyond the cited signal.
- **Auditability.** Every report logs the queries issued and sources consulted, so the research process is reproducible and reviewable.

## People data and no-people mode

A report can name individuals: the Individuals section, plus any name, handle, or profile link that turns up in an evidence quote. Three rules govern where that data may appear:

1. **Every public or directory surface is Companies and Segments only.** That covers the Claude plugin directory, MCP registries, Apify, and any hosted demo.
2. **A public proof page never carries Individuals.** Individuals live only in the client-gated deliverable.
3. **The paid private report keeps Individuals for now, and only until a privacy lawyer reviews it.** The buyer is the controller for any outreach. If the review says the Individuals section makes the seller a data broker, or needs GDPR Art. 14 notices that cannot be met, Individuals are cut from the paid report too.

The hard filter that enforces rules 1 and 2 is `finalize.py --no-people` (or `"people": false` in the analysis JSON). The MCP server (`mcp-server/server.py`) applies it by default; a caller must pass `people=True` to get Individuals. `--focus companies` is not a filter: it only prioritizes companies, so people can still appear.

What the filter does:

- Drops the `individuals` array before source verification, so no person is fetched or verified.
- Drops any Segment, Company, or battlecard entry whose own source is a personal profile or a post under a personal account (LinkedIn `/in/`, X/Twitter, Instagram, Facebook, TikTok, Threads, Reddit `/user/`, Hacker News user pages, bare GitHub profiles, Bluesky profiles, `/@name` pages).
- After verification, redacts from every remaining string: the names and handles of the dropped Individuals, any `@handle` or `u/handle`, personal email addresses (shared role inboxes such as `partners@` stay), and personal profile URLs. Source lists lose any entry that is only a profile URL.
- Adds a line to `limits` saying how many Individuals, prospects, and references were removed.
- Writes the filtered JSON, `handoff.json`, the HTML report, and `prospects.csv` to a `public/` folder. The input file is left untouched and is private working data: never publish it. Verify sources against that private draft, not the public copy: redacted quotes no longer match the page word for word.

What it does not do: it is pattern matching plus removal of names the analysis recorded as Individuals, not named-entity recognition. A person mentioned only by a bare name inside a quote, who was never recorded as an Individual, is not detected. In no-people mode the skill is told not to write such names, but check a public report by eye before publishing it.

## What the user is still responsible for

signal-scout produces research; the user performs the outreach. When contacting a prospect:

- Honor opt-outs and platform norms; one manual, relevant, low-volume message is the designed use — not bulk sequences.
- If asked "where did you get my information," answer with the public source the report cites.
- Applicable law depends on the recipient's jurisdiction (GDPR, CCPA/CPRA, CAN-SPAM, PECR). This document describes the tool's data practices; it is not legal advice, and no DPA is currently offered.
