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
# "identify a constructible gen-tie route") rather than asserting
# that state already holds are legitimate diligence-task phrasing,
# not overclaiming — but only when the sentence is actually framed
# as an action item. Every other pattern (bankable, cleared,
# guarantees, reservation land, cost figures, ...) is flagged
# regardless of framing, because those claims are never
# appropriate to assert even as a to-do target.
_TASK_FRAMING_EXEMPT_PATTERNS = {
    "final_poi_claim",
    "constructible_gen_tie_claim",
}

_DILIGENCE_ACTION_VERBS = (
    r"identify|confirm|determine|establish|verify|obtain|"
    r"assess|investigate|complete|resolve|retrieve|request|"
    r"commission|open|map|perform|replace|initiate|conduct"
)

_TASK_FRAMING_RE = re.compile(
    rf"^\s*({_DILIGENCE_ACTION_VERBS})\b",
    re.IGNORECASE,
)


def _is_diligence_task_framing(text: str) -> bool:

    return bool(_TASK_FRAMING_RE.match(text))


def scan_text_for_overclaiming(
    text: str,
) -> list[OverclaimFinding]:

    findings: list[OverclaimFinding] = []

    task_framed = _is_diligence_task_framing(text)

    for category, name, compiled in _COMPILED:

        if task_framed and name in _TASK_FRAMING_EXEMPT_PATTERNS:
            continue

        for match in compiled.finditer(text):

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
