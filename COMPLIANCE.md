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

## What the user is still responsible for

signal-scout produces research; the user performs the outreach. When contacting a prospect:

- Honor opt-outs and platform norms; one manual, relevant, low-volume message is the designed use — not bulk sequences.
- If asked "where did you get my information," answer with the public source the report cites.
- Applicable law depends on the recipient's jurisdiction (GDPR, CCPA/CPRA, CAN-SPAM, PECR). This document describes the tool's data practices; it is not legal advice, and no DPA is currently offered.
