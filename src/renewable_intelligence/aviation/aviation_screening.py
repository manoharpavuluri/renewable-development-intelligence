from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "aviation.screen_candidate"


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("aviation_evidence")
        or state.get("aviation_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "aviation.screen_candidate requires "
            "aviation_evidence."
        )

    artifact_path = evidence.get(
        "aviation_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "aviation_evidence must supply "
            "aviation_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def screen_candidate(
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

    nearest_public_use = summary.get(
        "nearest_public_use_airport"
    )

    sua_count = summary.get(
        "military_special_use_airspace_intersection_count",
        0,
    )

    finding = {
        "source_authority": source.get("authority"),
        "source_retrieved_utc": source.get("retrieved_utc"),
        "screening_radius_miles": summary.get(
            "screening_radius_miles"
        ),
        "statutory_airport_setback_nm": summary.get(
            "statutory_airport_setback_nm"
        ),
        "airports_within_screening_radius_count": (
            summary.get(
                "airports_within_screening_radius_count"
            )
        ),
        "public_use_airports_within_screening_radius_count": (
            summary.get(
                "public_use_airports_within_screening_radius_count"
            )
        ),
        "nearest_public_use_airport_name": (
            nearest_public_use.get("name")
            if nearest_public_use
            else None
        ),
        "nearest_public_use_airport_distance_nm": (
            nearest_public_use.get(
                "distance_to_candidate_nm"
            )
            if nearest_public_use
            else None
        ),
        "statutory_setback_appears_violated": (
            summary.get(
                "statutory_setback_appears_violated"
            )
        ),
        "military_special_use_airspace_intersection_count": (
            sua_count
        ),
        "faa_part77_notice_filed": False,
        "faa_airspace_determination_obtained": False,
        "military_mission_compatibility_reviewed": False,
        "radar_weather_surveillance_compatibility_established": (
            False
        ),
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
            or "PROJECT_SCREENING"
        ),

        "finding": finding,

        "airports_within_screening_radius": summary.get(
            "airports_within_screening_radius",
            [],
        ),

        "military_special_use_airspace_intersections": (
            summary.get(
                "military_special_use_airspace_intersections",
                [],
            )
        ),

        "evidence_quality": "MEDIUM",

        "evidence_quality_reason": (
            "FAA-sourced airport locations and Special Use "
            "Airspace polygons provide real, authoritative "
            "screening evidence, but this is not an FAA "
            "obstruction evaluation or airspace determination."
        ),

        "candidate_applicability": "HIGH",

        "interpretation_limits": [
            (
                "This screening does not perform or substitute "
                "for the FAA's Obstruction Evaluation / Airport "
                "Airspace Analysis (OE/AAA) process; only filing "
                "FAA Form 7460-1 and obtaining an airspace "
                "determination establishes that."
            ),
            (
                "Airport distances are computed to point "
                "locations, not runway centerlines or approach "
                "surfaces."
            ),
            (
                "Military Training Routes (low-level corridors) "
                "were not screened, only Special Use Airspace "
                "polygons intersecting the candidate boundary."
            ),
            (
                "No DoD mission-compatibility, radar, or weather-"
                "surveillance review has been performed."
            ),
        ],
    }
