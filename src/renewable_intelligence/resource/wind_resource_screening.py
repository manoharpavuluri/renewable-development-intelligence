from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "wind.analyze_candidate_resource"


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("wind_resource_evidence")
        or state.get("wind_resource_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "wind.analyze_candidate_resource requires "
            "wind_resource_evidence."
        )

    artifact_path = evidence.get(
        "hrrr_met_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "wind_resource_evidence must supply "
            "hrrr_met_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def analyze_candidate_resource(
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
    wind_speed = summary.get("wind_speed", {})
    speed_120m = wind_speed.get("120m", {})
    shear = summary.get("wind_shear_100m_160m", {})
    direction = summary.get("wind_direction_100m", {})
    monthly = summary.get(
        "monthly_mean_wind_speed_120m", {}
    )
    quality = summary.get("time_series_quality", {})

    monthly_values = list(monthly.values())

    finding = {
        "source_dataset": source.get("dataset"),
        "modeled_grid_point": source.get(
            "returned_grid_point"
        ),
        "years_covered": 1,
        "hourly_observation_count": quality.get(
            "rows"
        ),
        "missing_hourly_slot_count": quality.get(
            "missing_hourly_slot_count"
        ),
        "mean_wind_speed_120m_mps": speed_120m.get(
            "mean_mps"
        ),
        "median_wind_speed_120m_mps": speed_120m.get(
            "median_mps"
        ),
        "p10_wind_speed_120m_mps": speed_120m.get(
            "p10_mps"
        ),
        "p90_wind_speed_120m_mps": speed_120m.get(
            "p90_mps"
        ),
        "max_wind_speed_120m_mps": speed_120m.get(
            "max_mps"
        ),
        "mean_wind_shear_alpha": shear.get(
            "mean_alpha"
        ),
        "prevailing_wind_direction_degrees": (
            direction.get("circular_mean_degrees")
        ),
        "monthly_wind_speed_range_120m_mps": (
            [
                min(monthly_values),
                max(monthly_values),
            ]
            if monthly_values
            else None
        ),
        "candidate_wide_resource_established": (
            False
        ),
        "multi_year_resource_established": (
            False
        ),
        "met_tower_data_available": (
            False
        ),
        "aep_or_capacity_factor_established": (
            False
        ),
        "p50_p90_established": (
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

        "monthly_mean_wind_speed_120m": monthly,

        "wind_direction_sector_counts": (
            direction.get("sector_counts", {})
        ),

        "evidence_quality": "LOW",

        "evidence_quality_reason": (
            "HRRR is authoritative modeled meteorological data "
            "with a full year of hourly observations at one "
            "grid point, but it is a single modeled point (not "
            "the full candidate polygon), covers only one "
            "calendar year, and is not met-tower measured data."
        ),

        "candidate_applicability": "LOW",

        "interpretation_limits": [
            (
                "This represents one modeled HRRR grid point, "
                "not the full candidate polygon; spatial "
                "variability across the site has not been "
                "characterized."
            ),
            (
                "Only one calendar year (2025) is included; "
                "multi-year resource variability has not been "
                "established."
            ),
            (
                "HRRR values are modeled meteorological data, "
                "not on-site met-tower measurements."
            ),
            (
                "No turbine power curve has been applied; this "
                "does not represent AEP, capacity factor, P50, "
                "or P90."
            ),
        ],
    }
