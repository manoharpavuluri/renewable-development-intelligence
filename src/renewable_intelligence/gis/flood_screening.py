from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "gis.resolve_flood_evidence"


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("flood_evidence")
        or state.get("flood_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "gis.resolve_flood_evidence requires "
            "flood_evidence."
        )

    artifact_path = evidence.get(
        "fema_nfhl_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "flood_evidence must supply "
            "fema_nfhl_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def resolve_flood_evidence(
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
    mapped = summary.get("nfhl_mapped_coverage", {})
    unmapped = summary.get("nfhl_unmapped_or_unknown", {})
    sfha = summary.get("special_flood_hazard_area", {})
    zones = summary.get("zones", {})

    mapped_percent = mapped.get("percent")
    unmapped_percent = unmapped.get("percent")

    nfhl_coverage_status = (
        "NO_DIGITAL_COVERAGE"
        if (
            isinstance(mapped_percent, (int, float))
            and mapped_percent == 0.0
        )
        else (
            "PARTIAL_COVERAGE"
            if (
                isinstance(unmapped_percent, (int, float))
                and unmapped_percent > 0.0
            )
            else "FULL_COVERAGE"
        )
    )

    finding = {
        "source_authority": source.get("authority"),
        "source_dataset": source.get("dataset"),
        "source_layer": source.get("layer"),
        "source_retrieved_utc": source.get("retrieved_utc"),
        "candidate_area_acres": summary.get(
            "candidate_area_acres"
        ),
        "nfhl_mapped_coverage_acres": mapped.get("acres"),
        "nfhl_mapped_coverage_percent": mapped_percent,
        "nfhl_unmapped_or_unknown_acres": unmapped.get(
            "acres"
        ),
        "nfhl_unmapped_or_unknown_percent": (
            unmapped_percent
        ),
        "special_flood_hazard_area_acres": sfha.get(
            "acres"
        ),
        "special_flood_hazard_area_percent": (
            sfha.get("percent_of_candidate")
        ),
        "zone_count": len(zones),
        "nfhl_coverage_status": nfhl_coverage_status,
        "alternate_authoritative_flood_source_obtained": (
            False
        ),
        "site_specific_hydrologic_review_completed": (
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

        "zones": zones,

        "evidence_quality": (
            "LOW"
            if nfhl_coverage_status
            == "NO_DIGITAL_COVERAGE"
            else "MEDIUM"
        ),

        "evidence_quality_reason": (
            "FEMA NFHL is authoritative federal flood-hazard "
            "data, but this candidate area currently has no "
            "digital Flood Hazard Zone or FIRM panel coverage, "
            "so NFHL cannot establish flood-hazard status here "
            "either way."
        ),

        "candidate_applicability": (
            "LOW"
            if nfhl_coverage_status
            == "NO_DIGITAL_COVERAGE"
            else "HIGH"
        ),

        "interpretation_limits": [
            (
                "Absence of digital NFHL/FIRM coverage must not "
                "be interpreted as evidence of no flood hazard; "
                "it means the area is unmapped."
            ),
            (
                "No alternate authoritative flood-risk source "
                "(e.g. county floodplain study, USGS StreamStats, "
                "or a site-specific hydrologic study) has been "
                "consulted yet."
            ),
            (
                "Special Flood Hazard Area (SFHA) overlap, where "
                "present, is a screening fact and not an "
                "automatic project exclusion."
            ),
        ],
    }
