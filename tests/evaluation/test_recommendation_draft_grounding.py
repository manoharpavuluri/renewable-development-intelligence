"""
Layer 2 (regression) — scans the actual, already-produced draft
recommendation artifact for overclaiming language, using the same
field-aware scanner the recommendation-stability eval uses. This
checks real LLM output, not synthetic examples.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renewable_intelligence.evaluation.grounding_checks import (
    scan_draft_fields_for_overclaiming,
    scan_text_for_overclaiming,
)


# The frozen, committed example (data/examples/) rather than the
# gitignored data/spikes/ tree, so this check actually runs on a
# fresh clone and in CI instead of silently skipping.
DRAFT_PATH = Path(
    "data/examples/rdi-wok-250-001"
    "/screening/project_assessment_draft.json"
)


def _load_draft() -> dict | None:

    if not DRAFT_PATH.exists():
        return None

    data = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))

    return data["recommendation_draft"]


@pytest.mark.skipif(
    not DRAFT_PATH.exists(),
    reason="No draft recommendation artifact has been produced yet.",
)
def test_draft_recommendation_has_no_overclaiming_language():

    draft = _load_draft()

    violations = scan_draft_fields_for_overclaiming(
        rationale=draft["rationale"],
        critical_conditions=draft["critical_conditions"],
        unresolved_risks=draft["unresolved_risks"],
        next_diligence=draft["next_diligence"],
    )

    assert not violations, (
        "Overclaiming language found in draft recommendation: "
        + "; ".join(
            f"{item!r} -> {[f.pattern_name for f in findings]}"
            for item, findings in violations.items()
        )
    )


def test_gen_tie_target_naming_in_action_field_is_not_flagged():

    # Real drafts from the stability eval used verbs outside any
    # fixed whitelist ("Define a constructible gen-tie route...")
    # and named the target mid-sentence ("...and map a
    # constructible gen-tie route..."). Field identity, not
    # sentence grammar, is what makes both of these fine.
    violations = scan_draft_fields_for_overclaiming(
        rationale="",
        critical_conditions=[
            "Define a constructible gen-tie route and confirm "
            "ROW availability",
        ],
        unresolved_risks=[],
        next_diligence=[
            "Start candidate-specific SPP interconnection study "
            "work and map a constructible gen-tie route with "
            "ROW screening.",
        ],
    )

    assert not violations


def test_declarative_constructible_gen_tie_claim_is_still_flagged():

    findings = scan_text_for_overclaiming(
        "The gen-tie route is a constructible gen-tie route."
    )

    categories = {f.category for f in findings}

    assert "UNSUPPORTED_CERTAINTY" in categories


def test_gen_tie_claim_in_rationale_field_is_still_flagged():

    # The same phrase that's fine as a to-do item is a real
    # overclaim if it shows up in the descriptive rationale.
    violations = scan_draft_fields_for_overclaiming(
        rationale=(
            "A constructible gen-tie route has been identified "
            "for this candidate."
        ),
        critical_conditions=[],
        unresolved_risks=[],
        next_diligence=[],
    )

    assert violations


def test_non_exempt_pattern_is_flagged_even_in_action_fields():

    # Action-field exemption only covers the two target-naming
    # patterns; a real guardrail violation (bankable, guarantees,
    # cost figures, ...) is flagged everywhere.
    violations = scan_draft_fields_for_overclaiming(
        rationale="",
        critical_conditions=[
            "Confirm the bankable wind resource before proceeding",
        ],
        unresolved_risks=[],
        next_diligence=[],
    )

    assert violations
