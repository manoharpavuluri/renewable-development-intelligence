from __future__ import annotations

from enum import StrEnum
from typing import Any


CAPABILITY_NAME = "evidence.assess_sufficiency"


class SufficiencyStatus(StrEnum):
    SUFFICIENT_FOR_SCREENING_RECOMMENDATION = (
        "SUFFICIENT_FOR_SCREENING_RECOMMENDATION"
    )
    INSUFFICIENT_MORE_DILIGENCE_REQUIRED = (
        "INSUFFICIENT_MORE_DILIGENCE_REQUIRED"
    )


def assess_evidence_sufficiency(
    *,
    gate_syntheses: list[dict[str, Any]],
) -> dict[str, Any]:

    missing_domain_gates = [
        gate["gate_id"]
        for gate in gate_syntheses
        if len(gate.get("human_diligence_requirements", []))
        < len(gate.get("domains", []))
    ]

    low_confidence_gates = [
        gate["gate_id"]
        for gate in gate_syntheses
        if gate.get("confidence") == "LOW"
    ]

    unresolved_high_materiality_gates = [
        gate["gate_id"]
        for gate in gate_syntheses
        if gate["status"] == "UNRESOLVED"
        and gate["materiality"] in {"HIGH", "CRITICAL"}
    ]

    material_gaps = []

    for gate in gate_syntheses:

        if gate.get("confidence") == "LOW":

            material_gaps.append(
                {
                    "gate_id": gate["gate_id"],
                    "gap": (
                        f"{gate['name']} confidence is LOW "
                        "based on the underlying domain "
                        "evidence."
                    ),
                }
            )

        if gate["status"] == "UNRESOLVED":

            material_gaps.append(
                {
                    "gate_id": gate["gate_id"],
                    "gap": (
                        f"{gate['name']} remains UNRESOLVED "
                        "(missing domain evidence or a "
                        "confirmed evidence gap)."
                    ),
                }
            )


    # Every originally-queued domain has at least been screened
    # in this run (missing_domain_gates would only be non-empty
    # if a gate's domains were never investigated at all), so
    # the system has crossed the minimum bar for a bounded,
    # conditions-attached SCREENING-STAGE recommendation. It
    # does NOT mean the evidence is strong enough for an
    # unconditional ADVANCE; that constraint is enforced
    # separately by recommendation_policy.py.
    if missing_domain_gates:

        status = (
            SufficiencyStatus
            .INSUFFICIENT_MORE_DILIGENCE_REQUIRED
        )

        reason = (
            "The following gates have no investigated domain "
            f"evidence at all: {', '.join(missing_domain_gates)}. "
            "A screening-stage recommendation cannot responsibly "
            "be drafted until at least one investigation has run "
            "for every gate."
        )

    else:

        status = (
            SufficiencyStatus
            .SUFFICIENT_FOR_SCREENING_RECOMMENDATION
        )

        reason = (
            "All development gates have at least one completed, "
            "governed investigation. Evidence quality varies "
            f"(LOW confidence: {', '.join(low_confidence_gates) or 'none'}; "
            f"unresolved gates: "
            f"{', '.join(unresolved_high_materiality_gates) or 'none'}), "
            "so a screening-stage recommendation can be drafted, "
            "but it must be conditioned on the identified "
            "material gaps rather than presented as a final, "
            "unconditional investment decision."
        )

    return {
        "capability": CAPABILITY_NAME,
        "status": str(status),
        "reason": reason,
        "missing_domain_gates": missing_domain_gates,
        "low_confidence_gates": low_confidence_gates,
        "unresolved_high_materiality_gates": (
            unresolved_high_materiality_gates
        ),
        "material_gaps": material_gaps,
        "sufficient_for_unconditional_advance": False,
    }
