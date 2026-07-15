# Report Artifact

Create a standalone HTML report from the final qualified prospect data. Use the bundled generator instead of writing report markup manually.

## Generate

```bash
python3 scripts/generate_report.py analysis.json outputs/signal-scout-report.html
```

Return a clickable absolute file link in the final response. Keep the JSON in a work or temporary directory unless the user asks for raw data.

## JSON schema

The full schema is defined in the main SKILL.md. This reference covers the required and optional fields, validation rules, and completeness scoring.

### Required top-level fields

| Field | Type | Notes |
|---|---|---|
| `title` | string | Short product name |
| `product` | string | One-line product description |
| `product_url` | string | Valid HTTP/HTTPS URL |
| `target_customer` | string | Primary ICP description |
| `search_scope` | string | Research scope summary |
| `generated_at` | string | ISO date YYYY-MM-DD |
| `verdict` | string | Whether the startup has reachable early-customer signals |
| `patterns` | array | 0-10 repeated signal patterns |
| `outreach_plan` | object | Seven-day outreach strategy |
| `limits` | array | 1+ strings disclosing missing evidence |

At least one of `individuals`, `segments`, `companies` (each an array, 0-20 items) must be present and non-empty. Omit an array entirely if empty — don't include `"individuals": []`.

### Optional top-level fields

| Field | Type | Notes |
|---|---|---|
| `adjacent_icp` | string | Secondary ICP description |
| `methodology` | string | 1-2 sentence research approach summary |
| `search_queries_used` | array of strings | Every query issued during research |
| `sources_consulted` | array of strings | Every source URL or platform visited |
| `competitive_context` | object | Competitor landscape |

### Prospect validation rules

Common to all three types:
- `name` must be non-empty.
- `source_url` must be a valid HTTP/HTTPS URL.
- `stage` must be one of: "High intent", "Problem aware", "Trigger present", "Potential fit".
- `score` must be 0-100, calculated from that type's dimension set.
- Every prospect with score >= 50 must have a source URL that resolves.

Per type:
- **Individual**: `dimensions` must include all 5 keys (`pain_strength`, `product_fit`, `timing`, `reachability`, `evidence_quality`), each 0-5. If `opener` is present, `suggested_channel` must not be "No public reply/DM channel exists."
- **Segment**: `dimensions` must include the 4 keys (`pain_strength`, `product_fit`, `timing`, `evidence_quality`), each 0-5. `content_angle` is required.
- **Company**: `dimensions` must include the 4 keys (`strategic_fit`, `timing`, `execution_ease`, `evidence_quality`), each 0-5. `execution_path` and `contact_path` are required.

### Completeness scoring

The report generator calculates a completeness score (0-100) based on:

| Criterion | Points |
|---|---|
| Product brief complete | 10 |
| Methodology documented | 5 |
| Search queries logged | 5 |
| Sources consulted logged | 5 |
| Verdict present | 5 |
| 5+ prospects (any type) with scores | 15 |
| 3+ patterns with counts | 10 |
| Outreach plan complete | 10 |
| Competitive context present | 10 |
| Limits disclosed | 5 |
| Research audit present | 5 |
| All source URLs valid | 10 |

The completeness score appears in the report header as a badge.

## Report sections

The HTML report renders these sections in order:

1. **Hero** — title, date, verdict, completeness badge
2. **Stats bar** — product, target customer, high-intent count, average score, completeness
3. **Best in category** — the top-scoring Individual, Segment, and Company shown as separate call-outs (only the types present in the data get a call-out — never a single cross-type "best overall")
4. **Individuals** — "People to message": each with signal, fit, channel, opener, evidence, and 5-dimension breakdown
5. **Segments** — "Markets to target": each with pain pattern, content angle, keywords, channels, evidence, and 4-dimension breakdown
6. **Companies** — "Partners to pitch": each with gap/trigger, execution path, contact path, BD angle, evidence, and 4-dimension breakdown
7. **Repeated patterns** — signals appearing across multiple prospects of any type
8. **Competitive context** — top competitors, switching barriers, differentiation (if provided)
9. **Seven-day outreach plan** — manual validation sequence
10. **Research audit** — queries issued, sources consulted, methodology (if provided)
11. **Limits** — missing evidence and assumptions

Sections 4-6 are omitted entirely when their array is empty or absent — the report never shows an empty "Companies" section with a placeholder card.

## Error handling

Common JSON issues and fixes:

| Error | Fix |
|---|---|
| `Missing prospects` | At least one of `individuals`/`segments`/`companies` must be non-empty |
| `Invalid source_url` | Ensure URL starts with http:// or https:// |
| `Score out of range` | Score must be 0-100; dimensions 0-5 |
| `Invalid stage` | Use exact strings: "High intent", "Problem aware", etc. |
| `Wrong dimension set for type` | Individual needs 5 keys incl. `reachability`; Segment/Company need 4 keys matching their own schema |
| `Empty patterns` | Provide at least one pattern or omit the field |

If the script fails twice, output the JSON directly and note the issue.
