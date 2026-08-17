"""
Layer 2 — grounding / unsupported-claim evals.

The BAD/GOOD pairs below are the exact examples used to design
this project's guardrails: every BAD sentence must trigger at
least one finding, and every GOOD sentence (the appropriately
hedged version of the same underlying fact) must trigger none.
"""

from __future__ import annotations

import pytest

from renewable_intelligence.evaluation.grounding_checks import (
    scan_text_for_overclaiming,
)


BAD_EXAMPLES = [
    "Tatonga is feasible.",
    "FAA has cleared the project.",
    "The site has no flood risk.",
    "The tribal area is reservation land.",
    "The project will complete GI in 18 months.",
    "The project has 7.88 m/s bankable wind resource.",
]

GOOD_EXAMPLES = [
    "Tatonga is screening-preferred among tested POIs.",
    "No SUA intersection was identified in the screening.",
    (
        "Flood exposure remains unresolved because digital "
        "mapping is unavailable."
    ),
    (
        "PAD-US statistical geography does not establish "
        "legal land status."
    ),
    "GI duration remains unresolved.",
    (
        "One year / one modeled point provides screening-"
        "level resource evidence."
    ),
]


@pytest.mark.parametrize("text", BAD_EXAMPLES)
def test_bad_example_triggers_a_finding(text):

    findings = scan_text_for_overclaiming(text)

    assert findings, f"expected a finding for: {text!r}"


@pytest.mark.parametrize("text", GOOD_EXAMPLES)
def test_good_example_triggers_no_finding(text):

    findings = scan_text_for_overclaiming(text)

    assert not findings, (
        f"unexpected finding(s) for hedged statement "
        f"{text!r}: {findings!r}"
    )


def test_dollar_figure_is_flagged_as_invented_cost():

    findings = scan_text_for_overclaiming(
        "The network upgrade will cost $4.2 million."
    )

    categories = {f.category for f in findings}

    assert "INVENTED_COST" in categories


def test_guarantee_language_is_flagged_as_causal_dependency():

    findings = scan_text_for_overclaiming(
        "Completing the survey guarantees FAA approval."
    )

    categories = {f.category for f in findings}

    assert "INVENTED_CAUSAL_DEPENDENCY" in categories


NEGATED_GOOD_EXAMPLES = [
    (
        "While G1, G2, G4, and G5 are conditionally satisfied "
        "at screening level, each still carries evidence gaps "
        "and HUMAN_DILIGENCE_REQUIRED flags, and no domain has "
        "received regulatory or environmental clearance."
    ),
    "The project has not received FAA clearance.",
    "The candidate area is not reservation land.",
    "This screening does not guarantee interconnection approval.",
    "Tatonga is not feasible at this screening stage.",
]


@pytest.mark.parametrize("text", NEGATED_GOOD_EXAMPLES)
def test_negated_claim_triggers_no_finding(text):

    findings = scan_text_for_overclaiming(text)

    assert not findings, (
        f"unexpected finding(s) for negated statement "
        f"{text!r}: {findings!r}"
    )


def test_unhedged_environmental_clearance_claim_still_flagged():

    findings = scan_text_for_overclaiming(
        "The project has received environmental clearance."
    )

    pattern_names = {f.pattern_name for f in findings}

    assert "environmental_clearance_claim" in pattern_names


def test_negated_duration_and_cost_claims_still_flagged():

    duration_findings = scan_text_for_overclaiming(
        "It is not true that GI takes 18 months to approve."
    )

    cost_findings = scan_text_for_overclaiming(
        "It is not accurate that the upgrade cost is "
        "$4.2 million."
    )

    assert duration_findings, (
        "invented duration figures must stay flagged even when "
        "negated, since the specific figure is still invented"
    )

    assert cost_findings, (
        "invented cost figures must stay flagged even when "
        "negated, since the specific figure is still invented"
    )
