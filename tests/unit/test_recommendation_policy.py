"""
Layer 1 — deterministic-policy evals for the recommendation
admissible-set policy. No LLM calls; pure function tests.
"""

from __future__ import annotations

from renewable_intelligence.synthesis.recommendation_policy import (
    determine_allowed_categories,
)


def _gate(
    gate_id,
    *,
    status="CONDITIONALLY_SATISFIED",
    materiality="HIGH",
    confidence="MEDIUM",
    risks=None,
):

    return {
        "gate_id": gate_id,
        "status": status,
        "materiality": materiality,
        "confidence": confidence,
        "material_risks": risks or [],
    }


SUFFICIENT = {
    "status": "SUFFICIENT_FOR_SCREENING_RECOMMENDATION",
}

INSUFFICIENT = {
    "status": "INSUFFICIENT_MORE_DILIGENCE_REQUIRED",
}


def test_evidence_insufficient_only_hold_admissible():

    result = determine_allowed_categories(
        evidence_sufficiency=INSUFFICIENT,
        gate_syntheses=[_gate("G1")],
    )

    assert result["allowed_categories"] == ["HOLD"]


def test_critical_risk_blocks_advance_and_advance_with_conditions():

    gates = [
        _gate(
            "G3",
            status="UNRESOLVED",
            risks=[
                {
                    "severity": "CRITICAL",
                    "description": "disqualifying finding",
                }
            ],
        )
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    assert "ADVANCE" not in result["allowed_categories"]
    assert (
        "ADVANCE_WITH_CONDITIONS"
        not in result["allowed_categories"]
    )
    assert set(result["allowed_categories"]) == {
        "HOLD",
        "DO_NOT_ADVANCE",
    }


def test_high_risk_blocks_unconditional_advance_and_do_not_advance():

    gates = [
        _gate(
            "G2",
            risks=[
                {
                    "severity": "HIGH",
                    "description": "feasibility unresolved",
                }
            ],
        )
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    assert "ADVANCE" not in result["allowed_categories"]
    assert "DO_NOT_ADVANCE" not in result["allowed_categories"]
    assert set(result["allowed_categories"]) == {
        "ADVANCE_WITH_CONDITIONS",
        "HOLD",
    }


def test_unresolved_gate_blocks_unconditional_advance():

    gates = [
        _gate("G1", status="UNRESOLVED", risks=[]),
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    assert "ADVANCE" not in result["allowed_categories"]


def test_low_confidence_gate_blocks_unconditional_advance():

    gates = [
        _gate("G1", confidence="LOW", risks=[]),
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    assert "ADVANCE" not in result["allowed_categories"]


def test_clean_evidence_allows_advance():

    gates = [
        _gate("G1", confidence="HIGH", risks=[]),
        _gate("G2", confidence="HIGH", risks=[]),
    ]

    result = determine_allowed_categories(
        evidence_sufficiency=SUFFICIENT,
        gate_syntheses=gates,
    )

    assert set(result["allowed_categories"]) == {
        "ADVANCE",
        "ADVANCE_WITH_CONDITIONS",
    }

    assert "DO_NOT_ADVANCE" not in result["allowed_categories"]
    assert "HOLD" not in result["allowed_categories"]


def test_no_disqualifying_evidence_never_admits_do_not_advance_alone():

    # Across every non-critical scenario, DO_NOT_ADVANCE must
    # never appear without a CRITICAL risk backing it.
    scenarios = [
        [_gate("G1")],
        [_gate("G1", status="UNRESOLVED")],
        [_gate("G1", confidence="LOW")],
        [
            _gate(
                "G2",
                risks=[
                    {"severity": "HIGH", "description": "x"}
                ],
            )
        ],
    ]

    for gates in scenarios:

        result = determine_allowed_categories(
            evidence_sufficiency=SUFFICIENT,
            gate_syntheses=gates,
        )

        assert (
            "DO_NOT_ADVANCE"
            not in result["allowed_categories"]
        )
