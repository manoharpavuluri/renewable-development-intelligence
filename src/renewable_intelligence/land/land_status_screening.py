from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "land.resolve_status"


# GAP status is a biodiversity-protection *screening* classification
# from PAD-US. It is not a legal or development-control determination.
GAP_STATUS_SCREENING_MEANING = {
    "1": (
        "Permanent protection with a biodiversity-focused "
        "management mandate (screening signal only)."
    ),
    "2": (
        "Permanent protection with a biodiversity-focused "
        "management mandate, though management may permit "
        "more use than GAP 1 (screening signal only)."
    ),
    "3": (
        "Multiple-use conservation lands; extractive or other "
        "uses may occur depending on the managing authority."
    ),
    "4": (
        "No known biodiversity-protection mandate in PAD-US; "
        "still material for ownership, jurisdiction, and "
        "permitting context."
    ),
}


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("land_status_evidence")
        or state.get("land_status_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "land.resolve_status requires "
            "land_status_evidence."
        )

    artifact_path = evidence.get(
        "padus_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "land_status_evidence must supply "
            "padus_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def _unit_screening_flags(
    unit: dict[str, Any],
) -> list[str]:

    unit_name = str(unit.get("unit_name") or "")
    designation = str(unit.get("designation") or "")
    manager_type = str(unit.get("manager_type") or "")

    flags = []

    if (
        "Tribal" in unit_name
        or "Native American" in designation
        or "American Indian" in manager_type
    ):
        flags.append("POSSIBLE_TRIBAL_LAND_INTEREST")

    if manager_type == "State":
        flags.append("STATE_MANAGED_LAND")

    if (
        "Wildlife" in unit_name
        or "Conservation" in designation
    ):
        flags.append("CONSERVATION_MANAGEMENT_AREA")

    return flags


def resolve_land_status(
    *,
    state,
    task,
) -> dict[str, Any]:

    inputs = _resolve_inputs(
        state=state,
        task=task,
    )

    artifact_path = inputs["artifact_path"]

    if not artifact_path.exists():

        raise FileNotFoundError(artifact_path)

    summary = json.loads(
        artifact_path.read_text(encoding="utf-8")
    )

    source = summary.get("source", {})
    overlap = summary.get("padus_unique_overlap", {})
    raw_units = summary.get("units", [])

    flagged_units = []

    for unit in raw_units:

        flags = _unit_screening_flags(unit)

        flagged_units.append(
            {
                **unit,
                "screening_flags": flags,
                "gap_status_screening_meaning": (
                    GAP_STATUS_SCREENING_MEANING.get(
                        str(unit.get("gap_status")),
                        "Unknown GAP status.",
                    )
                ),
            }
        )

    flagged_units.sort(
        key=lambda item: item["candidate_overlap_acres"],
        reverse=True,
    )

    tribal_interest_flagged = any(
        "POSSIBLE_TRIBAL_LAND_INTEREST" in unit["screening_flags"]
        for unit in flagged_units
    )

    state_managed_land_flagged = any(
        "STATE_MANAGED_LAND" in unit["screening_flags"]
        for unit in flagged_units
    )

    conservation_area_flagged = any(
        "CONSERVATION_MANAGEMENT_AREA" in unit["screening_flags"]
        for unit in flagged_units
    )

    finding = {
        "padus_source_authority": source.get("authority"),
        "padus_source_dataset": source.get("dataset"),
        "padus_source_layer_url": source.get("layer_url"),
        "padus_source_retrieved_utc": source.get("retrieved_utc"),
        "candidate_area_acres": summary.get("candidate_area_acres"),
        "padus_overlap_acres": overlap.get("acres"),
        "padus_overlap_percent": overlap.get("percent_of_candidate"),
        "unit_count": len(flagged_units),
        "tribal_interest_flagged": tribal_interest_flagged,
        "state_managed_land_flagged": state_managed_land_flagged,
        "conservation_area_flagged": conservation_area_flagged,
        "authoritative_legal_status_established": False,
        "authoritative_tribal_trust_status_established": False,
        "authoritative_state_land_control_established": False,
    }

    return {
        "task_id": (
            task.get("task_id")
            or task.get("action_id")
        ),

        "capability": CAPABILITY_NAME,

        "executed": True,

        "relationship": (
            task.get("relationship")
            or "CANDIDATE_SCREENING"
        ),

        "finding": finding,

        "units": flagged_units,

        "managers": summary.get("managers", {}),

        "gap_status": summary.get("gap_status", {}),

        "evidence_quality": "MEDIUM",

        "evidence_quality_reason": (
            "PAD-US provides authoritative federal mapped-unit "
            "screening evidence with real acreage, manager, and "
            "designation attributes for the candidate area, but "
            "PAD-US classification is not itself a legal "
            "land-status or land-control determination."
        ),

        "candidate_applicability": "HIGH",

        "interpretation_limits": [
            (
                "PAD-US 'Tribal Statistical Area' designation is "
                "Census-derived statistical geography, not a "
                "legal trust or reservation boundary."
            ),
            (
                "PAD-US 'State Land Board' / CLO Lands mapping "
                "does not establish lease availability, sale "
                "eligibility, or development restrictions."
            ),
            (
                "PAD-US GAP status is a biodiversity-protection "
                "screening classification, not a wind-development "
                "legal exclusion."
            ),
            (
                "Where PAD-US polygons overlap spatially (e.g. a "
                "tribal statistical area and CLO lands covering "
                "nearly the same footprint here), separate "
                "authoritative confirmation is required to "
                "determine which designation, if any, actually "
                "governs land control."
            ),
            (
                "This screening does not establish ownership, "
                "lease status, easements, or actual legal "
                "development restrictions."
            ),
        ],
    }
