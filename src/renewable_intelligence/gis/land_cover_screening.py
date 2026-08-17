from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "gis.analyze_land_cover"


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("land_cover_evidence")
        or state.get("land_cover_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "gis.analyze_land_cover requires "
            "land_cover_evidence."
        )

    artifact_path = evidence.get(
        "land_cover_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "land_cover_evidence must supply "
            "land_cover_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def analyze_land_cover(
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
    class_groups = summary.get(
        "class_group_summary",
        {},
    )
    classes = summary.get("classes", [])

    dominant_class = (
        classes[0]
        if classes
        else None
    )

    finding = {
        "source_authority": source.get("authority"),
        "source_dataset": source.get("dataset"),
        "source_retrieved_utc": source.get("retrieved_utc"),
        "sample_resolution_m": source.get(
            "sample_resolution_m"
        ),
        "candidate_area_acres": summary.get(
            "candidate_area_acres"
        ),
        "sampled_area_acres": summary.get(
            "sampled_area_acres"
        ),
        "class_count": len(classes),
        "dominant_class_name": (
            dominant_class.get("class_name")
            if dominant_class
            else None
        ),
        "dominant_class_percent": (
            dominant_class.get(
                "percent_of_sampled_area"
            )
            if dominant_class
            else None
        ),
        "developed_acres": class_groups.get(
            "developed_acres"
        ),
        "developed_percent_of_candidate": (
            class_groups.get(
                "developed_percent_of_candidate"
            )
        ),
        "wetland_acres": class_groups.get(
            "wetland_acres"
        ),
        "cultivated_pasture_acres": (
            class_groups.get(
                "cultivated_pasture_acres"
            )
        ),
        "grass_shrub_acres": class_groups.get(
            "grass_shrub_acres"
        ),
        "developable_acreage_established": (
            False
        ),
        "layout_compatibility_established": (
            False
        ),
        "access_road_screening_established": (
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

        "classes": classes,

        "class_group_summary": class_groups,

        "evidence_quality": "MEDIUM",

        "evidence_quality_reason": (
            "NLCD is an authoritative, nationally consistent 30 m "
            "land-cover product with real class-composition "
            "statistics for the candidate area, but it is "
            "screening-grade and does not substitute for a "
            "site-specific land-cover or wetland survey."
        ),

        "candidate_applicability": "HIGH",

        "interpretation_limits": [
            (
                "NLCD classification is nationally consistent "
                "30 m screening-grade data, not a site-specific "
                "survey."
            ),
            (
                "No land-cover class is treated as a development "
                "exclusion in this screening; layout, access, and "
                "turbine-siting compatibility must be assessed "
                "separately."
            ),
            (
                "This does not establish jurisdictional wetland "
                "status; the governed NWI wetlands evidence "
                "already collected for this candidate is the "
                "more relevant wetlands source."
            ),
            (
                "Developable/usable acreage after exclusions, "
                "setbacks, and layout constraints has not been "
                "established."
            ),
        ],
    }
