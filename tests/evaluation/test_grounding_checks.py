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
