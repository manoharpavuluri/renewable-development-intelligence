from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "environment.screen_cultural_resources"


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("cultural_resources_evidence")
        or state.get("cultural_resources_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "environment.screen_cultural_resources requires "
            "cultural_resources_evidence."
        )

    artifact_path = evidence.get(
        "nrhp_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "cultural_resources_evidence must supply "
            "nrhp_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def screen_cultural_resources(
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
    direct_intersections = summary.get(
        "direct_intersections", []
    )
    nearby_sites = summary.get(
        "nearby_sites_within_radius", []
    )

    nhl_flagged = any(
        item.get("Is_NHL")
        for item in direct_intersections
    ) or any(
        item.get("is_national_historic_landmark")
        for item in nearby_sites
    )

    finding = {
        "source_authority": source.get("authority"),
        "source_dataset": source.get("dataset"),
        "source_retrieved_utc": source.get("retrieved_utc"),
        "screening_radius_miles": summary.get(
            "screening_radius_miles"
        ),
        "direct_intersection_count": summary.get(
            "direct_intersection_count",
            0,
        ),
        "nearby_site_count_within_radius": summary.get(
            "nearby_site_count_within_radius",
            0,
        ),
        "national_historic_landmark_flagged": nhl_flagged,
        "direct_intersection_resource_names": [
            item.get("RESNAME")
            for item in direct_intersections
        ],
        "section_106_review_completed": False,
        "shpo_consultation_completed": False,
        "tribal_thpo_consultation_completed": False,
        "archaeological_survey_completed": False,
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

        "direct_intersections": direct_intersections,

        "nearby_sites_within_radius": nearby_sites,

        "evidence_quality": "MEDIUM",

        "evidence_quality_reason": (
            "NRHP is authoritative NPS-maintained listing data "
            "with real site names and locations, but it covers "
            "only formally listed properties and is not a "
            "substitute for a Section 106 cultural-resources "
            "survey."
        ),

        "candidate_applicability": "HIGH",

        "interpretation_limits": [
            (
                "NRHP listing status does not by itself "
                "establish a development prohibition or "
                "required mitigation; it establishes that "
                "Section 106 review is likely warranted where "
                "there is a federal nexus."
            ),
            (
                "This dataset covers only formally NRHP-listed "
                "properties; unlisted but potentially eligible "
                "historic or archaeological resources (including "
                "unrecorded tribal cultural sites) are not "
                "captured here."
            ),
            (
                "Point locations are representative, not parcel-"
                "accurate; exact building/structure footprints "
                "relative to any turbine layout have not been "
                "verified."
            ),
            (
                "This is not a substitute for SHPO or Tribal "
                "Historic Preservation Office consultation."
            ),
        ],
    }
