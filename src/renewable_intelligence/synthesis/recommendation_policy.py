from __future__ import annotations

from typing import Any


ALL_CATEGORIES = [
    "ADVANCE",
    "ADVANCE_WITH_CONDITIONS",
    "HOLD",
    "DO_NOT_ADVANCE",
]


def determine_allowed_categories(
    *,
    evidence_sufficiency: dict[str, Any],
    gate_syntheses: list[dict[str, Any]],
) -> dict[str, Any]:

    """
    Deterministically bound which recommendation categories the
    drafting agent may choose from. This mirrors the investigation
    planner's admissible-action policy: the agent can synthesize
    and explain, but it cannot select a more optimistic category
    than the evidence supports, and it cannot invent a category
    outside this enumerated set.
    """

    if (
        evidence_sufficiency.get("status")
        == "INSUFFICIENT_MORE_DILIGENCE_REQUIRED"
    ):

        return {
            "allowed_categories": ["HOLD"],
            "reason": (
                "At least one gate has no investigated domain "
                "evidence at all; only HOLD is admissible."
            ),
        }

    all_risks = [
        risk
        for gate in gate_syntheses
        for risk in gate.get("material_risks", [])
    ]

    critical_risk_count = sum(
        1
        for risk in all_risks
        if risk["severity"] == "CRITICAL"
    )

    high_risk_count = sum(
        1
        for risk in all_risks
        if risk["severity"] == "HIGH"
    )

    unresolved_gate_ids = [
        gate["gate_id"]
        for gate in gate_syntheses
        if gate["status"] == "UNRESOLVED"
    ]

    low_confidence_gate_ids = [
        gate["gate_id"]
        for gate in gate_syntheses
        if gate.get("confidence") == "LOW"
    ]


    if critical_risk_count > 0:

        return {
            "allowed_categories": [
                "HOLD",
                "DO_NOT_ADVANCE",
            ],
            "reason": (
                f"{critical_risk_count} CRITICAL-severity "
                "material risk(s) remain unresolved; ADVANCE "
                "and ADVANCE_WITH_CONDITIONS are not admissible "
                "until those are addressed or downgraded by new "
                "evidence."
            ),
        }


    if (
        high_risk_count > 0
        or unresolved_gate_ids
        or low_confidence_gate_ids
    ):

        return {
            "allowed_categories": [
                "ADVANCE_WITH_CONDITIONS",
                "HOLD",
            ],
            "reason": (
                f"{high_risk_count} HIGH-severity material "
                f"risk(s), {len(unresolved_gate_ids)} unresolved "
                f"gate(s) ({', '.join(unresolved_gate_ids) or 'none'}), "
                f"and {len(low_confidence_gate_ids)} LOW-"
                f"confidence gate(s) "
                f"({', '.join(low_confidence_gate_ids) or 'none'}) "
                "rule out an unconditional ADVANCE and rule out "
                "DO_NOT_ADVANCE (no disqualifying finding has "
                "been established); the choice between advancing "
                "with explicit conditions and holding for further "
                "diligence is a genuine judgment call."
            ),
        }


    return {
        "allowed_categories": [
            "ADVANCE",
            "ADVANCE_WITH_CONDITIONS",
        ],
        "reason": (
            "No HIGH/CRITICAL material risks and no unresolved "
            "or LOW-confidence gates were found."
        ),
    }
