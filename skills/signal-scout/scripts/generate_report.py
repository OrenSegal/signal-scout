#!/usr/bin/env python3
"""Generate a standalone Signal Scout HTML report from JSON.

Renders three distinct sections — Individuals, Segments, Companies — each with
its own card layout and its own scoring dimensions, instead of forcing every
kind of lead through one schema.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


# ── Per-type dimension specs ───────────────────────────────────────────────────

DIMENSION_SPECS: dict[str, list[tuple[str, str]]] = {
    "individual": [
        ("pain_strength", "Pain strength"),
        ("product_fit", "Product fit"),
        ("timing", "Timing"),
        ("reachability", "Reachability"),
        ("evidence_quality", "Evidence quality"),
    ],
    "segment": [
        ("pain_strength", "Pain strength"),
        ("product_fit", "Product fit"),
        ("timing", "Timing"),
        ("evidence_quality", "Evidence quality"),
    ],
    "company": [
        ("strategic_fit", "Strategic fit"),
        ("timing", "Timing"),
        ("execution_ease", "Execution ease"),
        ("evidence_quality", "Evidence quality"),
    ],
}

TYPE_LABEL = {"individual": "Individual", "segment": "Segment", "company": "Company"}
TYPE_ACCENT_CLASS = {"individual": "acc-acid", "segment": "acc-blue", "company": "acc-orange"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def clamp(value: Any, maximum: int = 100) -> int:
    try:
        number = round(float(value))
    except (TypeError, ValueError):
        number = 0
    return max(0, min(maximum, number))


def items(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def dicts(value: Any) -> list[dict[str, Any]]:
    return [x for x in items(value) if isinstance(x, dict)]


def safe_url(value: Any) -> str:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    return esc(raw) if parsed.scheme in {"http", "https"} and parsed.netloc else "#"


def stage_class(stage: Any) -> str:
    value = str(stage or "").lower()
    if "high" in value:
        return "hot"
    if "problem" in value or "trigger" in value:
        return "warm"
    return "cool"


def completeness_score(data: dict[str, Any], total_prospects: int) -> int:
    score = 0
    if data.get("product") and data.get("target_customer"):
        score += 10
    if data.get("methodology"):
        score += 5
    if data.get("search_queries_used"):
        score += 5
    if data.get("sources_consulted"):
        score += 5
    if data.get("verdict"):
        score += 5
    if total_prospects >= 5:
        score += 15
    elif total_prospects >= 1:
        score += total_prospects * 3
    patterns = items(data.get("patterns"))
    if len(patterns) >= 3:
        score += 10
    elif len(patterns) >= 1:
        score += len(patterns) * 3
    plan = data.get("outreach_plan")
    if isinstance(plan, dict) and plan.get("angle") and plan.get("first_step"):
        score += 10
    if data.get("competitive_context"):
        score += 10
    if data.get("limits"):
        score += 5
    if data.get("sources_consulted"):
        score += 10
    return min(100, score)


# ── Shared card sub-renderers ─────────────────────────────────────────────────

def render_dimensions(dimensions: Any, kind: str) -> str:
    dims = dimensions if isinstance(dimensions, dict) else {}
    rows = []
    for key, label in DIMENSION_SPECS[kind]:
        score = clamp(dims.get(key, 0), 5)
        pct = score * 20
        rows.append(
            f'<div class="metric">'
            f'<span>{esc(label)}</span>'
            f'<div class="track"><i style="width:{pct}%"></i></div>'
            f'<b>{score}/5</b>'
            f'</div>'
        )
    return "".join(rows)


def render_card_header(item: dict[str, Any], index: int, kind: str, eyebrow_override: str = "") -> tuple[str, int]:
    score = clamp(item.get("score"))
    stage = item.get("stage", "Potential fit")
    eyebrow = eyebrow_override or TYPE_LABEL[kind]
    header = f"""
      <header class="card-head">
        <div class="rank">{index:02d}</div>
        <div class="identity">
          <span class="eyebrow">{esc(eyebrow)}</span>
          <h3>{esc(item.get('name', f'{TYPE_LABEL[kind]} {index}'))}</h3>
          <div class="badges">
            <span class="stage {stage_class(stage)}">{esc(stage)}</span>
          </div>
        </div>
        <div class="score" style="--score:{score}" aria-label="Fit score {score} out of 100">
          <strong>{score}</strong><small>/100</small>
        </div>
      </header>"""
    return header, score


def render_evidence_details(item: dict[str, Any], kind: str) -> str:
    source = safe_url(item.get("source_url"))
    return f"""
      <details>
        <summary>Evidence and score breakdown</summary>
        <div class="evidence">
          <div><span>Evidence</span><p>{esc(item.get('evidence', ''))}</p></div>
          <div>
            <span>Source</span>
            <p>{esc(item.get('source_type', 'Public source'))} · {esc(item.get('signal_date', 'Date unavailable'))}</p>
            <a href="{source}" target="_blank" rel="noreferrer">{esc(item.get('source_title', 'Open original source'))} ↗</a>
          </div>
        </div>
        <div class="metrics">{render_dimensions(item.get('dimensions'), kind)}</div>
      </details>"""


# ── Type-specific card renderers ──────────────────────────────────────────────

def render_individual(item: dict[str, Any], index: int) -> str:
    header, score = render_card_header(item, index, "individual")
    competitor = item.get("competitor_mentioned", "")
    competitor_badge = f'<span class="badge competitor">Uses {esc(competitor)}</span>' if competitor else ""
    if competitor_badge:
        header = header.replace('</div>\n          <div class="score"', f'{competitor_badge}</div>\n          <div class="score"', 1) if False else header

    opener = item.get("opener", "")
    channel = item.get("suggested_channel", "")
    opener_html = f'<blockquote><span>Suggested opener</span>{esc(opener)}</blockquote>' if opener else (
        f'<blockquote class="no-channel"><span>Next action</span>No public reply/DM channel exists — evidence only, not a contactable lead.</blockquote>'
    )

    follow_ups = items(item.get("follow_up_sequence"))
    follow_up_html = ""
    if follow_ups:
        touches = "".join(
            f'<li><span>Follow-up {i}</span><p>{esc(fu)}</p></li>' for i, fu in enumerate(follow_ups, 1)
        )
        follow_up_html = f'<div class="follow-ups"><span>Follow-up sequence</span><ul>{touches}</ul></div>'

    return f"""
    <article class="card card-individual reveal" data-stage="{esc(str(item.get('stage', '')).lower())}" data-score="{score}">
      {header}
      <div class="signal"><span>Public signal</span><p>{esc(item.get('pain_signal', ''))}</p></div>
      <div class="info-grid">
        <div><span>Why it fits</span><p>{esc(item.get('why_fit', ''))}</p></div>
        <div><span>Why now</span><p>{esc(item.get('why_now', ''))}</p></div>
        <div><span>Suggested channel</span><p>{esc(channel or 'None found')}</p></div>
        <div><span>Caution</span><p>{esc(item.get('caution', 'Confirm current relevance before outreach.'))}</p></div>
      </div>
      {opener_html}
      {follow_up_html}
      {render_evidence_details(item, "individual")}
    </article>"""


def render_segment(item: dict[str, Any], index: int) -> str:
    header, score = render_card_header(item, index, "segment")
    keywords = items(item.get("target_keywords"))
    channels = items(item.get("suggested_channels"))
    proof_points = items(item.get("proof_points"))

    keyword_html = "".join(f'<span class="chip">{esc(k)}</span>' for k in keywords) or "<span>Not specified</span>"
    channel_html = "".join(f"<li>{esc(c)}</li>" for c in channels) or "<li>Not specified</li>"
    proof_html = "".join(f"<li>{esc(p)}</li>" for p in proof_points)

    return f"""
    <article class="card card-segment reveal" data-stage="{esc(str(item.get('stage', '')).lower())}" data-score="{score}">
      {header}
      <div class="signal"><span>Repeated pain pattern</span><p>{esc(item.get('pain_signal', ''))}</p></div>
      <div class="info-grid">
        <div><span>Why it fits</span><p>{esc(item.get('why_fit', ''))}</p></div>
        <div><span>Why now</span><p>{esc(item.get('why_now', ''))}</p></div>
        <div><span>Channels</span><ul>{channel_html}</ul></div>
        <div><span>Caution</span><p>{esc(item.get('caution', 'Segment-level evidence, not an individual lead.'))}</p></div>
      </div>
      <blockquote class="content-angle"><span>Content angle</span>{esc(item.get('content_angle', ''))}</blockquote>
      <div class="keywords"><span>Target keywords</span><div class="chip-row">{keyword_html}</div></div>
      {f'<div class="proof-points"><span>Proof points</span><ul>{proof_html}</ul></div>' if proof_points else ''}
      {render_evidence_details(item, "segment")}
    </article>"""


def render_company(item: dict[str, Any], index: int) -> str:
    header, score = render_card_header(item, index, "company", eyebrow_override=item.get("role", "Company"))
    return f"""
    <article class="card card-company reveal" data-stage="{esc(str(item.get('stage', '')).lower())}" data-score="{score}">
      {header}
      <div class="signal"><span>Gap or trigger</span><p>{esc(item.get('pain_signal', ''))}</p></div>
      <div class="info-grid">
        <div><span>Combined value</span><p>{esc(item.get('why_fit', ''))}</p></div>
        <div><span>Why now</span><p>{esc(item.get('why_now', ''))}</p></div>
        <div><span>Execution path</span><p>{esc(item.get('execution_path', 'Not specified'))}</p></div>
        <div><span>Contact path</span><p>{esc(item.get('contact_path', 'Not specified'))}</p></div>
      </div>
      <blockquote><span>BD pitch</span>{esc(item.get('bd_angle', ''))}</blockquote>
      <div class="info-grid" style="margin-top:9px">
        <div><span>What to propose</span><p>{esc(item.get('what_to_propose', ''))}</p></div>
        <div><span>Caution</span><p>{esc(item.get('caution', 'Inferred fit, not a stated partnership request.'))}</p></div>
      </div>
      {render_evidence_details(item, "company")}
    </article>"""


RENDERERS = {"individual": render_individual, "segment": render_segment, "company": render_company}
SECTION_META = {
    "individual": ("People to message.", "Every individual is tied to a public pain, demand, or timing signal with a real reply channel. Open the evidence before considering outreach."),
    "segment": ("Markets to target.", "Audiences and repeated patterns, sized for content, SEO, and ASO strategy — not a message to send."),
    "company": ("Partners to pitch.", "Organizations evaluated as accounts or partners, with a public contact path and a concrete first ask."),
}


def render_best_card(kind: str, item: dict[str, Any]) -> str:
    if not item:
        return ""
    score = clamp(item.get("score"))
    headline = item.get("why_now") or item.get("pain_signal") or item.get("content_angle") or item.get("bd_angle") or ""
    return f"""
    <div class="best-card {TYPE_ACCENT_CLASS[kind]}">
      <span class="best-label">Best {TYPE_LABEL[kind].lower()}</span>
      <h3>{esc(item.get('name', 'None qualified'))}</h3>
      <p>{esc(headline)}</p>
      <strong>{score}</strong>
    </div>"""


def render_pattern(pattern: dict[str, Any], index: int) -> str:
    return f"""
    <article class="pattern reveal">
      <span class="pattern-num">{index:02d}</span>
      <div><h3>{esc(pattern.get('title', 'Repeated signal'))}</h3><p>{esc(pattern.get('insight', ''))}</p></div>
      <strong>{clamp(pattern.get('count'), 999)}x</strong>
    </article>"""


def render_competitive_context(ctx: dict[str, Any]) -> str:
    competitors = items(ctx.get("top_competitors"))
    comp_list = "".join(f"<li>{esc(c)}</li>" for c in competitors)
    return f"""
    <section class="competitive">
      <header class="section-head">
        <h2>The landscape they already live in.</h2>
        <p>What prospects currently use and where this product wins.</p>
      </header>
      <div class="comp-grid">
        <div class="comp-card">
          <span>Top competitors</span>
          <ul>{comp_list or '<li>Not mapped</li>'}</ul>
        </div>
        <div class="comp-card">
          <span>Switching barriers</span>
          <p>{esc(ctx.get('switching_barriers', 'Not specified'))}</p>
        </div>
        <div class="comp-card">
          <span>Where this product wins</span>
          <p>{esc(ctx.get('differentiation_angle', 'Not specified'))}</p>
        </div>
      </div>
    </section>"""


def render_research_audit(data: dict[str, Any]) -> str:
    queries = items(data.get("search_queries_used"))
    sources = items(data.get("sources_consulted"))
    methodology = data.get("methodology", "")

    query_list = "".join(f"<li><code>{esc(q)}</code></li>" for q in queries[:20])
    source_list = "".join(f"<li><code>{esc(s)}</code></li>" for s in sources[:30])

    return f"""
    <section class="audit">
      <header class="section-head">
        <h2>How this research was done.</h2>
        <p>Full audit trail for reproducibility and trust.</p>
      </header>
      <div class="audit-grid">
        <div class="audit-card">
          <span>Methodology</span>
          <p>{esc(methodology or 'Not documented')}</p>
        </div>
        <div class="audit-card">
          <span>Queries issued ({len(queries)})</span>
          <ul>{query_list or '<li>Not logged</li>'}</ul>
        </div>
        <div class="audit-card">
          <span>Sources consulted ({len(sources)})</span>
          <ul>{source_list or '<li>Not logged</li>'}</ul>
        </div>
      </div>
    </section>"""


def render_type_section(kind: str, items_list: list[dict[str, Any]]) -> str:
    if not items_list:
        return ""
    title, subtitle = SECTION_META[kind]
    cards = "".join(RENDERERS[kind](x, i) for i, x in enumerate(items_list, 1))
    return f"""
      <section>
        <header class="section-head">
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </header>
        <div class="cards">
          {cards}
        </div>
      </section>"""


# ── Main HTML builder ─────────────────────────────────────────────────────────

def build_html(data: dict[str, Any]) -> str:
    individuals = dicts(data.get("individuals"))
    segments = dicts(data.get("segments"))
    companies = dicts(data.get("companies"))
    all_prospects = individuals + segments + companies
    patterns = dicts(data.get("patterns"))

    scores = [clamp(x.get("score")) for x in all_prospects]
    high_intent = sum(1 for x in all_prospects if "high" in str(x.get("stage", "")).lower())
    average = round(sum(scores) / len(scores)) if scores else 0

    best_individual = max(individuals, key=lambda x: clamp(x.get("score")), default={})
    best_segment = max(segments, key=lambda x: clamp(x.get("score")), default={})
    best_company = max(companies, key=lambda x: clamp(x.get("score")), default={})

    plan = data.get("outreach_plan") if isinstance(data.get("outreach_plan"), dict) else {}
    limits = items(data.get("limits"))
    completeness = completeness_score(data, len(all_prospects))
    comp_ctx = data.get("competitive_context") if isinstance(data.get("competitive_context"), dict) else {}

    individuals_html = render_type_section("individual", individuals)
    segments_html = render_type_section("segment", segments)
    companies_html = render_type_section("company", companies)

    best_row = "".join([
        render_best_card("individual", best_individual),
        render_best_card("segment", best_segment),
        render_best_card("company", best_company),
    ])

    product_url = safe_url(data.get("product_url"))
    limits_html = "".join(f"<li>{esc(x)}</li>" for x in limits)
    pattern_html = "".join(render_pattern(x, i) for i, x in enumerate(patterns, 1))

    comp_section = render_competitive_context(comp_ctx) if comp_ctx else ""
    audit_section = render_research_audit(data)

    channels = plan.get("channels_to_prioritize")
    channels_html = ""
    if channels:
        items_list = "".join(f"<li>{esc(ch)}</li>" for ch in items(channels))
        channels_html = f'<div><span>Channels to prioritize</span><ul>{items_list}</ul></div>'

    patterns_section = f"""
      <section>
        <header class="section-head">
          <h2>Signals that repeat.</h2>
          <p>Patterns across individuals, segments, and companies reveal the strongest positioning, workflow, and outreach angles.</p>
        </header>
        <div class="patterns">
          {pattern_html or '<p>No repeated patterns supplied.</p>'}
        </div>
      </section>""" if patterns else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>{esc(data.get('title', 'Signal Scout'))}</title>
  <style>
    :root {{
      --bg: #090b0f;
      --panel: #12161d;
      --panel2: #191f28;
      --ink: #f5f2ea;
      --muted: #9ca6b5;
      --line: #2b3340;
      --acid: #d9ff63;
      --blue: #69b7ff;
      --orange: #ff8f5a;
      --cyan: #5ee8d0;
      --red: #ff6b6b;
      --radius: 18px;
      --shadow: 0 24px 80px rgba(0, 0, 0, .38);
    }}
    *, *::before, *::after {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .3;
      background: repeating-linear-gradient(135deg, rgba(255, 255, 255, .018) 0 1px, transparent 1px 12px);
      mask-image: linear-gradient(#000, transparent 82%);
    }}
    a {{ color: inherit; }}
    ul {{ margin: 0; padding-left: 1.2em; }}
    li {{ margin: 2px 0; }}

    .skip {{ position: absolute; left: -9999px; }}
    .skip:focus {{ left: 16px; top: 16px; z-index: 9; background: var(--acid); color: #111; padding: 10px; border-radius: 8px; }}
    button:focus-visible, summary:focus-visible, a:focus-visible {{ outline: 3px solid var(--blue); outline-offset: 3px; }}

    .shell {{ width: min(1180px, calc(100% - 40px)); margin: auto; position: relative; }}

    .top {{ display: flex; justify-content: space-between; align-items: center; padding: 22px 0; border-bottom: 1px solid var(--line); }}
    .brand {{ font-weight: 850; display: flex; align-items: center; gap: 10px; }}
    .brand i {{ width: 12px; height: 12px; border-radius: 50%; background: var(--acid); box-shadow: 0 0 22px var(--acid); }}
    .meta {{ display: flex; gap: 8px; align-items: center; }}
    .chip, .badge {{
      border: 1px solid var(--line); border-radius: 999px; padding: 7px 10px; color: var(--muted);
      font: 750 11px ui-monospace, monospace; text-transform: uppercase; letter-spacing: .07em; display: inline-block;
    }}
    .badge.competitor {{ border-color: rgba(255, 107, 107, .5); color: var(--red); }}
    .completeness-badge {{
      background: var(--acid); color: #111; padding: 7px 12px; border-radius: 999px;
      font: 800 12px ui-monospace, monospace; display: flex; align-items: center; gap: 6px;
    }}
    .completeness-badge i {{ width: 8px; height: 8px; border-radius: 50%; background: #111; }}
    button {{ background: var(--ink); color: #111; border: 0; border-radius: 999px; padding: 9px 14px; font: 800 13px inherit; cursor: pointer; }}

    .hero {{ display: grid; grid-template-columns: 1.45fr .55fr; gap: 36px; align-items: end; padding: 72px 0 42px; }}
    .eyebrow {{ color: var(--acid); font: 750 11px ui-monospace, monospace; text-transform: uppercase; letter-spacing: .11em; }}
    h1 {{ font-size: clamp(48px, 7vw, 92px); line-height: .92; letter-spacing: -.065em; margin: 13px 0 24px; }}
    .verdict {{ font-size: clamp(18px, 2.1vw, 25px); color: #dce1e9; max-width: 820px; margin: 0; }}
    .hero-card {{ background: var(--acid); color: #10120d; padding: 26px; border-radius: var(--radius); box-shadow: var(--shadow); transform: rotate(1deg); }}
    .hero-card span {{ font: 800 11px ui-monospace, monospace; text-transform: uppercase; letter-spacing: .08em; }}
    .hero-card strong {{ display: block; font-size: 64px; line-height: 1; letter-spacing: -.08em; margin: 15px 0 6px; }}
    .hero-card p {{ margin: 0; font-weight: 700; font-size: 13px; }}

    .stats {{ display: grid; grid-template-columns: repeat(5, 1fr); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; margin-bottom: 28px; }}
    .stats > div {{ padding: 18px; background: var(--panel); }}
    .stats > div + div {{ border-left: 1px solid var(--line); }}
    .stats span, .info-grid span, .signal span, .evidence span, blockquote span,
    .audit-card span, .comp-card span, .follow-ups span, .keywords span, .proof-points span {{
      display: block; color: var(--muted); font: 700 10px ui-monospace, monospace;
      text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px;
    }}
    .stats strong {{ font-size: 17px; }}

    .filter-bar {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; padding: 14px 0; border-bottom: 1px solid var(--line); }}
    .filter-bar button {{ background: var(--panel); color: var(--muted); border: 1px solid var(--line); padding: 7px 14px; font: 700 12px inherit; transition: all .15s; }}
    .filter-bar button:hover {{ border-color: var(--acid); color: var(--ink); }}
    .filter-bar button.active {{ background: var(--acid); color: #111; border-color: var(--acid); }}
    .filter-bar input {{ background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: 999px; padding: 7px 14px; font: 700 12px inherit; width: 200px; }}
    .filter-bar input::placeholder {{ color: var(--muted); }}

    .best-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 72px; }}
    .best-card {{ padding: 24px; border-radius: var(--radius); box-shadow: var(--shadow); color: #111; }}
    .best-card.acc-acid {{ background: var(--acid); }}
    .best-card.acc-blue {{ background: var(--blue); }}
    .best-card.acc-orange {{ background: var(--orange); }}
    .best-label {{ font: 800 11px ui-monospace, monospace; text-transform: uppercase; letter-spacing: .1em; }}
    .best-card h3 {{ font-size: clamp(22px, 3vw, 32px); letter-spacing: -.03em; line-height: 1.05; margin: 8px 0; }}
    .best-card p {{ margin: 0 0 10px; font-size: 13px; }}
    .best-card strong {{ font-size: 34px; }}

    .section-head {{ display: flex; justify-content: space-between; align-items: end; gap: 24px; padding-bottom: 18px; border-bottom: 1px solid var(--line); margin-bottom: 18px; }}
    .section-head h2 {{ font-size: clamp(34px, 5vw, 62px); line-height: .98; letter-spacing: -.055em; margin: 0; }}
    .section-head p {{ color: var(--muted); max-width: 470px; margin: 0; }}

    .cards {{ display: grid; gap: 16px; margin-bottom: 76px; }}
    .card {{ background: linear-gradient(135deg, var(--panel), #0f1319); border: 1px solid var(--line); border-radius: var(--radius); padding: 25px; box-shadow: 0 12px 38px rgba(0, 0, 0, .18); }}
    .card.hidden {{ display: none; }}
    .card-head {{ display: grid; grid-template-columns: 54px 1fr 92px; gap: 17px; align-items: start; }}
    .rank {{ font: 850 24px ui-monospace, monospace; color: var(--acid); padding-top: 8px; }}
    .identity h3 {{ font-size: 29px; letter-spacing: -.04em; margin: 6px 0 10px; }}
    .badges {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .stage {{ display: inline-block; }}
    .stage.hot {{ color: var(--orange); border-color: rgba(255, 143, 90, .5); }}
    .stage.warm {{ color: var(--cyan); border-color: rgba(94, 232, 208, .45); }}
    .score {{
      --score: 0; width: 88px; height: 88px; border-radius: 50%; display: grid; place-content: center; text-align: center;
      background: radial-gradient(circle, var(--panel) 58%, transparent 60%), conic-gradient(var(--acid) calc(var(--score) * 1%), var(--line) 0);
    }}
    .score strong {{ font-size: 26px; line-height: 1; }}
    .score small {{ color: var(--muted); }}
    .signal {{ margin: 21px 0 12px; padding: 16px; background: var(--panel2); border-left: 4px solid var(--acid); }}
    .card-segment .signal {{ border-left-color: var(--blue); }}
    .card-company .signal {{ border-left-color: var(--orange); }}
    .signal p {{ font-size: 17px; margin: 0; }}
    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }}
    .info-grid > div, .evidence > div, .comp-card {{ border: 1px solid var(--line); border-radius: 12px; padding: 15px; background: rgba(255, 255, 255, .018); }}
    .info-grid p {{ margin: 0; }}
    .info-grid ul {{ margin: 0; padding-left: 1.1em; }}
    blockquote {{ margin: 12px 0 0; padding: 16px; border: 1px dashed rgba(217, 255, 99, .55); border-radius: 12px; color: #eaf6c6; }}
    blockquote.no-channel {{ border-color: rgba(156, 166, 181, .4); color: var(--muted); }}
    blockquote.content-angle {{ border-color: rgba(105, 183, 255, .55); color: #dbeaff; }}
    .card-company blockquote {{ border-color: rgba(255, 143, 90, .55); color: #ffe6d8; }}
    details {{ margin-top: 10px; }}
    summary {{ cursor: pointer; color: var(--acid); font-weight: 800; padding: 10px 0; }}
    .evidence {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }}
    .evidence a {{ display: inline-block; color: var(--blue); margin-top: 8px; word-break: break-word; }}
    .evidence p {{ margin: 0; }}
    .metrics {{ display: grid; gap: 8px; margin-top: 14px; }}
    .metric {{ display: grid; grid-template-columns: 145px 1fr 40px; gap: 12px; align-items: center; font-size: 13px; }}
    .track {{ height: 8px; background: var(--line); border-radius: 8px; overflow: hidden; }}
    .track i {{ display: block; height: 100%; background: linear-gradient(90deg, var(--blue), var(--acid)); border-radius: 8px; }}
    .follow-ups, .keywords, .proof-points {{ margin-top: 14px; padding: 16px; background: var(--panel2); border-radius: 12px; }}
    .follow-ups ul, .proof-points ul {{ list-style: none; padding: 0; }}
    .follow-ups li, .proof-points li {{ padding: 8px 0; border-bottom: 1px solid var(--line); }}
    .follow-ups li:last-child, .proof-points li:last-child {{ border-bottom: 0; }}
    .follow-ups li span {{ font: 700 10px ui-monospace, monospace; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-bottom: 4px; display: block; }}
    .follow-ups li p {{ margin: 0; font-size: 14px; }}
    .chip-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip-row .chip {{ color: var(--ink); border-color: var(--line); }}

    .patterns {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 76px; }}
    .pattern {{ display: grid; grid-template-columns: 42px 1fr auto; gap: 15px; align-items: start; padding: 20px; border: 1px solid var(--line); border-radius: 14px; background: var(--panel); }}
    .pattern-num {{ color: var(--acid); font: 800 13px ui-monospace, monospace; }}
    .pattern h3 {{ margin: 0 0 5px; }}
    .pattern p {{ margin: 0; color: var(--muted); }}
    .pattern > strong {{ font-size: 30px; color: var(--acid); }}

    .competitive {{ margin-bottom: 76px; }}
    .comp-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .comp-card span {{ margin-bottom: 8px; }}
    .comp-card p {{ margin: 0; }}
    .comp-card ul {{ margin: 0; padding-left: 1.2em; }}

    .plan {{ display: grid; grid-template-columns: .8fr 1.2fr; gap: 28px; background: var(--acid); color: #111; padding: 29px; border-radius: var(--radius); margin-bottom: 30px; }}
    .plan h2 {{ font-size: 38px; line-height: 1; letter-spacing: -.045em; margin: 10px 0; }}
    .plan-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }}
    .plan-grid > div {{ border: 1px solid rgba(0, 0, 0, .24); border-radius: 11px; padding: 13px; }}
    .plan-grid span {{ display: block; font: 750 10px ui-monospace, monospace; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 5px; }}
    .plan-grid p {{ margin: 0; }}
    .plan-grid ul {{ margin: 0; padding-left: 1.2em; }}

    .audit {{ margin-bottom: 76px; }}
    .audit-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }}
    .audit-card {{ border: 1px solid var(--line); border-radius: 14px; padding: 20px; background: var(--panel); }}
    .audit-card ul {{ list-style: none; padding: 0; max-height: 200px; overflow-y: auto; }}
    .audit-card li {{ font-size: 13px; padding: 3px 0; color: var(--muted); word-break: break-all; }}
    .audit-card code {{ font-size: 12px; color: var(--cyan); }}

    .limits {{ border: 1px solid var(--line); border-radius: var(--radius); padding: 24px; color: var(--muted); margin-bottom: 60px; }}
    .limits h2 {{ color: var(--ink); margin-top: 0; }}

    footer {{ display: flex; justify-content: space-between; gap: 20px; border-top: 1px solid var(--line); padding: 22px 0 40px; color: var(--muted); font-size: 12px; }}

    .reveal {{ animation: rise .4s ease both; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(12px); }} }}

    @media (max-width: 820px) {{
      .shell {{ width: min(100% - 24px, 1180px); }}
      .hero, .plan {{ grid-template-columns: 1fr; }}
      .hero {{ padding-top: 44px; }}
      .hero-card {{ transform: none; }}
      .stats {{ grid-template-columns: 1fr 1fr; }}
      .stats > div + div {{ border-left: 0; border-top: 1px solid var(--line); }}
      .card-head {{ grid-template-columns: 38px 1fr; }}
      .score {{ grid-column: 1 / -1; }}
      .info-grid, .evidence, .patterns, .plan-grid, .comp-grid, .audit-grid {{ grid-template-columns: 1fr; }}
      .meta .chip {{ display: none; }}
      .filter-bar input {{ width: 100%; }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important; transition: none !important; scroll-behavior: auto !important; }}
    }}

    @media print {{
      body {{ background: #fff; color: #111; }}
      body::before, .top button, .filter-bar {{ display: none; }}
      .shell {{ width: 100%; }}
      .card, .pattern, .limits, .audit-card, .comp-card {{ background: #fff; color: #111; break-inside: avoid; }}
      .info-grid span, .signal span, .evidence span, blockquote span, .stats span,
      .audit-card span, .comp-card span, .follow-ups span {{ color: #444; }}
      .card.hidden {{ display: block !important; }}
    }}
  </style>
</head>
<body>
  <a class="skip" href="#main">Skip to report</a>
  <div class="shell">
    <header class="top">
      <div class="brand"><i></i> Signal Scout</div>
      <div class="meta">
        <span class="chip">Public signals only</span>
        <span class="completeness-badge"><i></i> Completeness {completeness}%</span>
        <button type="button" onclick="window.print()">Print / Save PDF</button>
      </div>
    </header>

    <main id="main">
      <section class="hero">
        <div>
          <span class="eyebrow">Early-customer report · {esc(data.get('generated_at', ''))}</span>
          <h1>{esc(data.get('title', 'Signal Scout'))}</h1>
          <p class="verdict">{esc(data.get('verdict', 'No verdict supplied.'))}</p>
        </div>
        <aside class="hero-card">
          <span>Qualified prospects</span>
          <strong>{len(all_prospects)}</strong>
          <p>Potential customers, markets, and partners based on public signals.</p>
        </aside>
      </section>

      <section class="stats">
        <div><span>Product</span><strong><a href="{product_url}" target="_blank" rel="noreferrer">{esc(data.get('product', 'Not specified'))}</a></strong></div>
        <div><span>Individuals</span><strong>{len(individuals)}</strong></div>
        <div><span>Segments</span><strong>{len(segments)}</strong></div>
        <div><span>Companies</span><strong>{len(companies)}</strong></div>
        <div><span>Completeness</span><strong>{completeness}%</strong></div>
      </section>

      <div class="best-row">
        {best_row}
      </div>

      <div class="filter-bar" id="filterBar">
        <button class="active" data-filter="all">All ({len(all_prospects)})</button>
        <button data-filter="hot">High intent</button>
        <button data-filter="warm">Problem aware / trigger</button>
        <button data-filter="cool">Potential fit</button>
        <input type="text" id="searchInput" placeholder="Search all prospects...">
      </div>

      {individuals_html}
      {segments_html}
      {companies_html}

      {patterns_section}

      {comp_section}

      <section class="plan">
        <div>
          <span class="eyebrow" style="color:#111">Seven-day manual plan</span>
          <h2>{esc(plan.get('angle', 'Validate the pain before pitching the product.'))}</h2>
        </div>
        <div class="plan-grid">
          <div><span>First step</span><p>{esc(plan.get('first_step', ''))}</p></div>
          <div><span>Follow-up</span><p>{esc(plan.get('follow_up', ''))}</p></div>
          <div><span>Success signal</span><p>{esc(plan.get('success', ''))}</p></div>
          <div><span>Research scope</span><p>{esc(data.get('search_scope', 'Not specified'))}</p></div>
          {channels_html}
        </div>
      </section>

      {audit_section}

      <section class="limits">
        <h2>Use this shortlist responsibly</h2>
        <ul>{limits_html or '<li>These are potential customers, markets, and partners inferred from public signals, not confirmed buyers.</li>'}</ul>
      </section>
    </main>

    <footer>
      <span>Generated by signal-scout</span>
      <span>Outreach is never sent automatically.</span>
    </footer>
  </div>

  <script>
    document.querySelectorAll('.filter-bar button').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.filter-bar button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        document.querySelectorAll('.card').forEach(card => {{
          if (filter === 'all' || card.dataset.stage === filter) {{
            card.classList.remove('hidden');
          }} else {{
            card.classList.add('hidden');
          }}
        }});
      }});
    }});

    document.getElementById('searchInput').addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      document.querySelectorAll('.card').forEach(card => {{
        const text = card.textContent.toLowerCase();
        card.classList.toggle('hidden', q.length > 0 && !text.includes(q));
      }});
      if (q.length > 0) {{
        document.querySelectorAll('.filter-bar button').forEach(b => b.classList.remove('active'));
      }} else {{
        document.querySelector('.filter-bar button[data-filter="all"]').classList.add('active');
      }}
    }});
  </script>
</body>
</html>"""


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to report JSON")
    parser.add_argument("output", type=Path, help="Path to output HTML")
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("Input JSON must contain an object at the top level.")

    if not any(dicts(data.get(k)) for k in ("individuals", "segments", "companies")):
        raise SystemExit("At least one of individuals, segments, or companies must be a non-empty array.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(data), encoding="utf-8")
    print(f"Created report: {args.output.resolve()}")


if __name__ == "__main__":
    main()
