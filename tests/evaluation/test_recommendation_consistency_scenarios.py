"""
Layer 3 — recommendation-consistency evals.

These test whether the recommendation policy keeps the drafting
agent inside the correct decision envelope under synthetic
evidence variations, not whether it reproduces the same wording.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from renewable_intelligence.synthesis.recommendation_policy import (
    determine_allowed_categories,
)


DRAFT_PATH = Path(
    "data/spikes/public_sources_20260815T173207Z"
    "/screening/project_assessment_draft.json"
)


SUFFICIENT = {
    "status": "MINIMUM_COVERAGE_FOR_SCREENING_RECOMMENDATION"
}

INSUFFICIENT = {
    "status": "BELOW_MINIMUM_COVERAGE_MORE_DILIGENCE_REQUIRED"
}


def _gate(gate_id, *, status, confidence, risks):

    return {
        "gate_id": gate_id,
        "status": status,
        "materiality": "HIGH",
        "confidence": confidence,
        "material_risks": risks,
    }


def test_case_a_unresolved_gate_with_high_species_risk():

    gates = [
        _gate(
            "G3",
            status="UNRESOLVED",
            confidence="MEDIUM",
            risks=[
                {
                    "severity": "HIGH",
                    "description": (
                        "Critical habitat overlaps candidate."
                    ),
                }
            ],
        )
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    assert set(result["allowed_categories"]) == {
        "ADVANCE_WITH_CONDITIONS",
        "HOLD",
    }


def test_case_b_all_gates_conditionally_satisfied_no_high_risk():

    gates = [
        _gate(
            "G1",
            status="SCREENED_WITH_CONDITIONS",
            confidence="HIGH",
            risks=[],
        ),
        _gate(
            "G2",
            status="SCREENED_WITH_CONDITIONS",
            confidence="HIGH",
            risks=[],
        ),
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    assert "ADVANCE_WITH_CONDITIONS" in result["allowed_categories"]
    assert "DO_NOT_ADVANCE" not in result["allowed_categories"]


def test_case_c_authoritative_exclusion_admits_do_not_advance():

    gates = [
        _gate(
            "G3",
            status="UNSATISFIED",
            confidence="HIGH",
            risks=[
                {
                    "severity": "CRITICAL",
                    "description": (
                        "Authoritative agency confirmed the "
                        "site is legally prohibited from "
                        "development."
                    ),
                    "disqualifying_finding": True,
                }
            ],
        )
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    assert "DO_NOT_ADVANCE" in result["allowed_categories"]
    assert "ADVANCE" not in result["allowed_categories"]
    assert (
        "ADVANCE_WITH_CONDITIONS"
        not in result["allowed_categories"]
    )


def test_case_d_evidence_insufficient_blocks_any_advance_flavor():

    gates = [
        _gate(
            "G1",
            status="SCREENED_WITH_CONDITIONS",
            confidence="HIGH",
            risks=[],
        ),
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=INSUFFICIENT,
        gate_syntheses=gates,
    )

    assert result["allowed_categories"] == ["HOLD"]
    assert "ADVANCE" not in result["allowed_categories"]
    assert (
        "ADVANCE_WITH_CONDITIONS"
        not in result["allowed_categories"]
    )
    assert "DO_NOT_ADVANCE" not in result["allowed_categories"]


def test_case_e_flood_risk_present_alongside_low_materiality_elsewhere():

    gates = [
        _gate(
            "G3",
            status="UNRESOLVED",
            confidence="MEDIUM",
            risks=[
                {
                    "severity": "MEDIUM",
                    "description": (
                        "FEMA NFHL has zero digital coverage; "
                        "flood-hazard status is genuinely "
                        "UNKNOWN."
                    ),
                }
            ],
        ),
        _gate(
            "G4",
            status="SCREENED_WITH_CONDITIONS",
            confidence="MEDIUM",
            risks=[],
        ),
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    # G3 remaining UNRESOLVED (due to the flood evidence gap)
    # must still rule out an unconditional ADVANCE even though
    # every other gate is clean.
    assert "ADVANCE" not in result["allowed_categories"]


@pytest.mark.skipif(
    not DRAFT_PATH.exists(),
    reason="No draft recommendation artifact has been produced yet.",
)
def test_real_draft_retains_flood_condition():

    data = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))

    draft = data["recommendation_draft"]

    combined_text = " ".join(
        [draft["rationale"]]
        + draft["critical_conditions"]
        + draft["unresolved_risks"]
    ).lower()

    assert "flood" in combined_text, (
        "The real draft recommendation dropped the flood "
        "evidence-gap condition that was actually identified "
        "during screening."
    )


@pytest.mark.skipif(
    not DRAFT_PATH.exists(),
    reason="No draft recommendation artifact has been produced yet.",
)
def test_real_draft_recommendation_matches_case_a_envelope():

    # The real project state matches case A (G3 UNRESOLVED with a
    # HIGH species risk), so the actual drafted recommendation
    # must fall inside that envelope.
    data = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))

    recommendation = data["recommendation_draft"][
        "recommendation"
    ]

    assert recommendation in {
        "ADVANCE_WITH_CONDITIONS",
        "HOLD",
    }
