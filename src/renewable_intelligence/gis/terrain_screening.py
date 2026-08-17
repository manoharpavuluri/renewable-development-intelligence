from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "gis.analyze_terrain"


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("terrain_evidence")
        or state.get("terrain_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "gis.analyze_terrain requires "
            "terrain_evidence."
        )

    artifact_path = evidence.get(
        "terrain_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "terrain_evidence must supply "
            "terrain_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def analyze_terrain(
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
    elevation = summary.get("elevation_m", {})
    slope = summary.get("slope_percent", {})
    slope_thresholds = summary.get(
        "slope_threshold_area",
        {},
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
        "elevation_min_m": elevation.get("min"),
        "elevation_max_m": elevation.get("max"),
        "elevation_mean_m": elevation.get("mean"),
        "relief_m": elevation.get("relief"),
        "slope_mean_percent": slope.get("mean"),
        "slope_p50_percent": slope.get("p50"),
        "slope_p90_percent": slope.get("p90"),
        "slope_max_percent": slope.get("max"),
        "acres_over_15pct_slope": (
            slope_thresholds.get("gt_15pct", {}).get(
                "acres"
            )
        ),
        "percent_of_area_over_15pct_slope": (
            slope_thresholds.get("gt_15pct", {}).get(
                "percent_of_sampled_area"
            )
        ),
        "acres_over_20pct_slope": (
            slope_thresholds.get("gt_20pct", {}).get(
                "acres"
            )
        ),
        "percent_of_area_over_20pct_slope": (
            slope_thresholds.get("gt_20pct", {}).get(
                "percent_of_sampled_area"
            )
        ),
        "wind_development_slope_threshold_established": (
            False
        ),
        "constructability_exclusion_established": (
            False
        ),
        "turbine_micrositing_established": (
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

        "slope_threshold_area": slope_thresholds,

        "evidence_quality": "MEDIUM",

        "evidence_quality_reason": (
            "USGS 3DEP bare-earth DEM is authoritative federal "
            "elevation data resampled to a 10 m screening grid; "
            "slope is a central-difference estimate suitable for "
            "early-stage screening, not survey-grade micro-siting."
        ),

        "candidate_applicability": "HIGH",

        "interpretation_limits": [
            (
                "Slope statistics are computed on a 10 m resampled "
                "grid and are screening-grade, not survey-grade."
            ),
            (
                "No wind-development slope-suitability threshold "
                "is applied or endorsed by this screening; "
                "constructability and micro-siting thresholds are "
                "project- and vendor-specific."
            ),
            (
                "This does not account for land cover, access "
                "roads, geotechnical conditions, or other "
                "constructability factors beyond elevation/slope."
            ),
            (
                "Relief and slope statistics describe the full "
                "candidate polygon, not a specific turbine layout "
                "or usable/developable acreage."
            ),
        ],
    }
