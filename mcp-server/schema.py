"""JSON Schema for signal-scout's analysis artifact, trimmed for structured
outputs (Anthropic's output_config.format).

Structured outputs forbids a few things the full hand-authored schema in
SKILL.md uses freely: no additionalProperties beyond `false`, no min/max
length or numeric bounds, no recursive $ref. Optional fields become
nullable (`["string", "null"]`) instead of omitted, since strict mode
requires every declared property to be listed in `required`. This is a v0
subset (individuals/segments/companies + patterns + outreach_plan + limits)
— growth_playbook and competitive_context are left out to keep the schema
small; add them the same way if a later version needs them.
"""

from __future__ import annotations

STAGE_ENUM = ["High intent", "Problem aware", "Trigger present", "Potential fit"]


def _dims(*keys: str) -> dict:
    return {
        "type": "object",
        "properties": {k: {"type": "number", "description": f"0-5 score, {k.replace('_', ' ')}"} for k in keys},
        "required": list(keys),
        "additionalProperties": False,
    }


def _obj(properties: dict, nullable: tuple[str, ...] = ()) -> dict:
    """Build a strict object schema: every property required, properties in
    `nullable` get `null` added to their type union instead of being omitted."""
    props = {}
    for key, spec in properties.items():
        if key in nullable:
            spec = dict(spec)
            t = spec.get("type", "string")
            spec["type"] = [t, "null"] if isinstance(t, str) else list(t) + ["null"]
        props[key] = spec
    return {
        "type": "object",
        "properties": props,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


INDIVIDUAL_SCHEMA = _obj(
    {
        "name": {"type": "string", "description": "Real name or stable public handle"},
        "stage": {"type": "string", "enum": STAGE_ENUM},
        "score": {"type": "number", "description": "0-100, computed from dimensions"},
        "pain_signal": {"type": "string"},
        "evidence": {"type": "string"},
        "why_fit": {"type": "string"},
        "why_now": {"type": "string"},
        "source_title": {"type": "string"},
        "source_url": {"type": "string"},
        "source_type": {"type": "string"},
        "signal_date": {"type": "string", "description": "Publication date if visible, else 'Date unavailable'"},
        "suggested_channel": {"type": "string", "description": "Or 'No public reply/DM channel exists'"},
        "opener": {"type": "string", "description": "Under 90 words; null if no channel exists"},
        "follow_up_sequence": {"type": "array", "items": {"type": "string"}},
        "caution": {"type": "string"},
        "competitor_mentioned": {"type": "string"},
        "dimensions": _dims("pain_strength", "product_fit", "timing", "reachability", "evidence_quality"),
    },
    nullable=("opener", "competitor_mentioned"),
)

SEGMENT_SCHEMA = _obj(
    {
        "name": {"type": "string"},
        "stage": {"type": "string", "enum": STAGE_ENUM},
        "score": {"type": "number"},
        "pain_signal": {"type": "string"},
        "evidence": {"type": "string"},
        "why_fit": {"type": "string"},
        "why_now": {"type": "string"},
        "source_title": {"type": "string"},
        "source_url": {"type": "string"},
        "source_type": {"type": "string"},
        "signal_date": {"type": "string"},
        "content_angle": {"type": "string"},
        "target_keywords": {"type": "array", "items": {"type": "string"}},
        "suggested_channels": {"type": "array", "items": {"type": "string"}},
        "proof_points": {"type": "array", "items": {"type": "string"}},
        "caution": {"type": "string"},
        "competitor_mentioned": {"type": "string"},
        "dimensions": _dims("pain_strength", "product_fit", "timing", "evidence_quality"),
    },
    nullable=("competitor_mentioned",),
)

COMPANY_SCHEMA = _obj(
    {
        "name": {"type": "string"},
        "role": {"type": "string"},
        "stage": {"type": "string", "enum": STAGE_ENUM},
        "score": {"type": "number"},
        "pain_signal": {"type": "string"},
        "evidence": {"type": "string"},
        "why_fit": {"type": "string"},
        "why_now": {"type": "string"},
        "source_title": {"type": "string"},
        "source_url": {"type": "string"},
        "source_type": {"type": "string"},
        "signal_date": {"type": "string"},
        "execution_path": {"type": "string"},
        "contact_path": {"type": "string"},
        "bd_angle": {"type": "string"},
        "what_to_propose": {"type": "string"},
        "caution": {"type": "string"},
        "dimensions": _dims("strategic_fit", "timing", "execution_ease", "evidence_quality"),
    },
)

PATTERN_SCHEMA = _obj(
    {
        "title": {"type": "string"},
        "count": {"type": "number"},
        "insight": {"type": "string"},
    }
)

OUTREACH_PLAN_SCHEMA = _obj(
    {
        "angle": {"type": "string"},
        "first_step": {"type": "string"},
        "follow_up": {"type": "string"},
        "success": {"type": "string"},
        "channels_to_prioritize": {"type": "array", "items": {"type": "string"}},
        "personalization_notes": {"type": "string"},
    }
)

ANALYSIS_SCHEMA = _obj(
    {
        "title": {"type": "string"},
        "product": {"type": "string"},
        "product_url": {"type": "string"},
        "target_customer": {"type": "string"},
        "search_scope": {"type": "string"},
        "generated_at": {"type": "string", "description": "ISO date YYYY-MM-DD"},
        "methodology": {"type": "string"},
        "search_queries_used": {"type": "array", "items": {"type": "string"}},
        "sources_consulted": {"type": "array", "items": {"type": "string"}},
        "verdict": {"type": "string"},
        "individuals": {"type": "array", "items": INDIVIDUAL_SCHEMA},
        "segments": {"type": "array", "items": SEGMENT_SCHEMA},
        "companies": {"type": "array", "items": COMPANY_SCHEMA},
        "patterns": {"type": "array", "items": PATTERN_SCHEMA},
        "outreach_plan": OUTREACH_PLAN_SCHEMA,
        "limits": {"type": "array", "items": {"type": "string"}},
    }
)
