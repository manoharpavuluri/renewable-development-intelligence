"""
Layer 2 (regression) — scans the actual, already-produced draft
recommendation artifact for overclaiming language. This checks
real LLM output, not synthetic examples.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renewable_intelligence.evaluation.grounding_checks import (
    scan_text_for_overclaiming,
)


DRAFT_PATH = Path(
    "data/spikes/public_sources_20260815T173207Z"
    "/screening/project_assessment_draft.json"
)


def _load_draft_texts() -> list[tuple[str, str]]:

    if not DRAFT_PATH.exists():
        return []

    data = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))

    draft = data["recommendation_draft"]

    texts: list[tuple[str, str]] = [
        ("rationale", draft["rationale"]),
    ]

    for field_name in (
        "critical_conditions",
        "unresolved_risks",
        "next_diligence",
    ):

        for item in draft[field_name]:
            texts.append((field_name, item))

    return texts


@pytest.mark.skipif(
    not DRAFT_PATH.exists(),
    reason="No draft recommendation artifact has been produced yet.",
)
def test_draft_recommendation_has_no_overclaiming_language():

    texts = _load_draft_texts()

    violations = []

    for field_name, text in texts:

        findings = scan_text_for_overclaiming(text)

        if findings:
            violations.append((field_name, text, findings))

    assert not violations, (
        "Overclaiming language found in draft recommendation: "
        + "; ".join(
            f"[{field}] {text!r} -> "
            f"{[f.pattern_name for f in findings]}"
            for field, text, findings in violations
        )
    )


def test_diligence_action_item_naming_gen_tie_is_not_flagged():

    findings = scan_text_for_overclaiming(
        "Identify a constructible gen-tie route and confirm "
        "ROW availability"
    )

    assert not findings


def test_declarative_constructible_gen_tie_claim_is_still_flagged():

    findings = scan_text_for_overclaiming(
        "The gen-tie route is a constructible gen-tie route."
    )

    categories = {f.category for f in findings}

    assert "UNSUPPORTED_CERTAINTY" in categories
