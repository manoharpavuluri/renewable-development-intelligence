from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ClaimCategory(StrEnum):
    UNSUPPORTED_CERTAINTY = "UNSUPPORTED_CERTAINTY"
    SCREENING_VS_FINAL = "SCREENING_VS_FINAL"
    LEGAL_CONCLUSION_LEAKAGE = "LEGAL_CONCLUSION_LEAKAGE"
    INVENTED_DURATION = "INVENTED_DURATION"
    INVENTED_COST = "INVENTED_COST"
    INVENTED_CAUSAL_DEPENDENCY = "INVENTED_CAUSAL_DEPENDENCY"


@dataclass(frozen=True)
class OverclaimFinding:
    category: ClaimCategory
    pattern_name: str
    matched_text: str
    span: tuple[int, int]


# ------------------------------------------------------------
# Every pattern here maps directly to a "do not" item in
# CLAUDE_HANDOFF.md section 25 (Guardrails / Non-Negotiables),
# or to one of the BAD example phrases this project has been
# explicitly asked to avoid. These are deliberately blunt,
# always-flagged patterns: hedging language elsewhere in the
# same sentence does not excuse them, because the underlying
# claim (bankable yield, legal title, FAA clearance, etc.) is
# never something this system's deterministic capabilities
# actually establish.
# ------------------------------------------------------------

_PATTERNS: list[tuple[ClaimCategory, str, str]] = [
    # --- Unsupported certainty ---------------------------------
    (
        ClaimCategory.UNSUPPORTED_CERTAINTY,
        "bankable_yield_claim",
        r"\bbankable\b",
    ),
    (
        ClaimCategory.UNSUPPORTED_CERTAINTY,
        "unqualified_feasible_claim",
        r"\b(is|are|was|were)\s+feasible\b",
    ),
    (
        ClaimCategory.UNSUPPORTED_CERTAINTY,
        "absolute_no_risk_claim",
        r"\bno\s+(flood|species|environmental|regulatory|"
        r"aviation|cultural)\s+risk\b",
    ),
    (
        ClaimCategory.UNSUPPORTED_CERTAINTY,
        "final_poi_claim",
        r"\bfinal\s+(POI|point\s+of\s+interconnection)\b",
    ),
    (
        ClaimCategory.UNSUPPORTED_CERTAINTY,
        "constructible_gen_tie_claim",
        r"\bconstructible\s+gen-?tie\b",
    ),
    # --- Screening-vs-final distinction -------------------------
    (
        ClaimCategory.SCREENING_VS_FINAL,
        "faa_clearance_claim",
        r"\bFAA\s+(has\s+)?(cleared|clears|approved|"
        r"determined)\b",
    ),
    (
        ClaimCategory.SCREENING_VS_FINAL,
        "environmental_clearance_claim",
        r"\benvironmental(ly)?\s+clear(ed|ance)?\b",
    ),
    (
        ClaimCategory.SCREENING_VS_FINAL,
        "generic_clearance_claim",
        r"\bhas\s+cleared\b|\bis\s+cleared\b",
    ),
    (
        ClaimCategory.SCREENING_VS_FINAL,
        "gi_feasibility_confirmed_claim",
        r"\b(GI|interconnection)\s+(is\s+)?(confirmed|"
        r"established)\s+feasible\b",
    ),
    # --- Legal conclusion leakage --------------------------------
    (
        ClaimCategory.LEGAL_CONCLUSION_LEAKAGE,
        "reservation_land_claim",
        r"\bis\s+reservation\s+land\b",
    ),
    (
        ClaimCategory.LEGAL_CONCLUSION_LEAKAGE,
        "trust_land_claim",
        r"\bis\s+trust\s+land\b",
    ),
    (
        ClaimCategory.LEGAL_CONCLUSION_LEAKAGE,
        "unqualified_legal_status_claim",
        r"\bhas\s+legal\s+(title|right|ownership)\b",
    ),
    # --- Invented duration ---------------------------------------
    (
        ClaimCategory.INVENTED_DURATION,
        "will_complete_in_duration_claim",
        r"\bwill\s+complete\b[^.]{0,40}\bin\s+\d+\s*"
        r"(day|week|month|year)s?\b",
    ),
    (
        ClaimCategory.INVENTED_DURATION,
        "takes_duration_to_approve_claim",
        r"\btakes?\s+\d+\s*(day|week|month|year)s?\s+to\s+"
        r"(approve|complete|finish)\b",
    ),
    # --- Invented cost ---------------------------------------------
    (
        ClaimCategory.INVENTED_COST,
        "dollar_figure_claim",
        r"\$\s?[\d,]+(\.\d+)?\s*(million|billion|k|m|b)?\b",
    ),
    (
        ClaimCategory.INVENTED_COST,
        "upgrade_cost_stated_claim",
        r"\bupgrade\s+cost\s+(is|of|will\s+be)\b",
    ),
    # --- Invented causal dependency ----------------------------------
    (
        ClaimCategory.INVENTED_CAUSAL_DEPENDENCY,
        "guarantee_claim",
        r"\bguarantee(s|d)?\b",
    ),
    (
        ClaimCategory.INVENTED_CAUSAL_DEPENDENCY,
        "ensures_outcome_claim",
        r"\bensures?\s+(that\s+)?(approval|success|"
        r"feasibility)\b",
    ),
]


_COMPILED = [
    (category, name, re.compile(pattern, re.IGNORECASE))
    for category, name, pattern in _PATTERNS
]


# Patterns that name a target STATE TO BE ESTABLISHED (e.g.
# "identify a constructible gen-tie route", or "map a
# constructible gen-tie route" buried mid-sentence after "and")
# rather than asserting that state already holds are legitimate
# diligence-task phrasing, not overclaiming.
#
# An earlier version of this checker tried to detect that framing
# grammatically (matching a diligence verb at the start of the
# sentence, including gerund/infinitive forms). That approach was
# fragile in practice: the recommendation-stability eval caught
# real drafts like "Define a constructible gen-tie route..." (verb
# not in the list) and "Start ... and map a constructible gen-tie
# route..." (the verb is present, but mid-sentence, not at the
# start) still being flagged.
#
# The robust signal is not grammar, it's which FIELD the text
# came from. The drafter's own prompt (recommendation_drafter.py)
# defines critical_conditions and next_diligence as inherently
# action-item fields ("concrete items that must be resolved",
# "concrete, actionable next steps") and rationale /
# unresolved_risks as inherently descriptive fields. Exemption is
# applied per field via scan_draft_fields_for_overclaiming, not by
# parsing each sentence's grammar.
EXEMPT_IN_ACTION_FIELDS = {
    "final_poi_claim",
    "constructible_gen_tie_claim",
}

ACTION_ITEM_FIELDS = {"critical_conditions", "next_diligence"}
DECLARATIVE_FIELDS = {"rationale", "unresolved_risks"}


# Patterns that assert an ACHIEVED STATE ("has cleared", "is
# feasible", "is reservation land", "guarantees") are legitimate,
# appropriately hedged statements when negated ("has NOT
# received environmental clearance", "does not guarantee").
# Patterns that assert a specific INVENTED NUMBER (a duration or
# a dollar figure) stay flagged even when negated, because
# negating a specific figure still asserts that figure was
# meaningfully derived ("will not take less than 18 months"
# still invents "18 months"); absolute_no_risk_claim is itself
# already a negation-shaped claim and is excluded from this
# double-negation logic for the same reason.
_NEGATION_SENSITIVE_PATTERNS = {
    "bankable_yield_claim",
    "unqualified_feasible_claim",
    "final_poi_claim",
    "constructible_gen_tie_claim",
    "faa_clearance_claim",
    "environmental_clearance_claim",
    "generic_clearance_claim",
    "gi_feasibility_confirmed_claim",
    "reservation_land_claim",
    "trust_land_claim",
    "unqualified_legal_status_claim",
    "guarantee_claim",
    "ensures_outcome_claim",
}

_NEGATION_CUE_RE = re.compile(
    r"\b(no|not|without|lacks?|lacking|never|none|cannot|"
    r"can't|hasn't|has\s+not|doesn't|does\s+not|isn't|"
    r"is\s+not|absence\s+of)\b",
    re.IGNORECASE,
)

_NEGATION_LOOKBACK_CHARS = 50


def _is_negated_context(text: str, match_start: int) -> bool:

    window_start = max(0, match_start - _NEGATION_LOOKBACK_CHARS)

    preceding = text[window_start:match_start]

    return bool(_NEGATION_CUE_RE.search(preceding))


def scan_text_for_overclaiming(
    text: str,
) -> list[OverclaimFinding]:

    findings: list[OverclaimFinding] = []

    for category, name, compiled in _COMPILED:

        for match in compiled.finditer(text):

            if (
                name in _NEGATION_SENSITIVE_PATTERNS
                and _is_negated_context(text, match.start())
            ):
                continue

            findings.append(
                OverclaimFinding(
                    category=category,
                    pattern_name=name,
                    matched_text=match.group(0),
                    span=match.span(),
                )
            )

    return findings


def scan_strings_for_overclaiming(
    strings: list[str],
) -> dict[str, list[OverclaimFinding]]:

    return {
        text: scan_text_for_overclaiming(text)
        for text in strings
        if scan_text_for_overclaiming(text)
    }


def scan_draft_fields_for_overclaiming(
    *,
    rationale: str,
    critical_conditions: list[str],
    unresolved_risks: list[str],
    next_diligence: list[str],
) -> dict[str, list[OverclaimFinding]]:

    """
    Field-aware scan of a recommendation draft. critical_conditions
    and next_diligence are action-item fields by construction, so
    a target-state-naming pattern (EXEMPT_IN_ACTION_FIELDS) found
    there is not flagged; every other pattern, and every pattern
    in the declarative fields (rationale, unresolved_risks), is
    flagged regardless of phrasing.
    """

    fields = {
        "rationale": [rationale],
        "critical_conditions": critical_conditions,
        "unresolved_risks": unresolved_risks,
        "next_diligence": next_diligence,
    }

    violations: dict[str, list[OverclaimFinding]] = {}

    for field_name, items in fields.items():

        is_action_field = field_name in ACTION_ITEM_FIELDS

        for item in items:

            findings = scan_text_for_overclaiming(item)

            if is_action_field:

                findings = [
                    f
                    for f in findings
                    if f.pattern_name
                    not in EXEMPT_IN_ACTION_FIELDS
                ]

            if findings:
                violations[f"{field_name}: {item}"] = findings

    return violations
