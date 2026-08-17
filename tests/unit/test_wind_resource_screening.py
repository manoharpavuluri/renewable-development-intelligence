"""
Layer 1 — deterministic unit tests for HRRR wind-resource summary
calculations (monthly range, missing-data handling).
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.resource.wind_resource_screening import (
    analyze_candidate_resource,
)


def _write_artifact(tmp_path, *, monthly=None):

    artifact = {
        "source": {
            "dataset": "HRRR",
            "returned_grid_point": [35.5, -99.1],
        },
        "wind_speed": {
            "120m": {
                "mean_mps": 7.5,
                "median_mps": 7.4,
                "p10_mps": 4.0,
                "p90_mps": 11.0,
                "max_mps": 20.0,
            }
        },
        "wind_shear_100m_160m": {"mean_alpha": 0.15},
        "wind_direction_100m": {
            "circular_mean_degrees": 200.0,
            "sector_counts": {},
        },
        "monthly_mean_wind_speed_120m": monthly or {},
        "time_series_quality": {
            "rows": 8760,
            "missing_hourly_slot_count": 12,
        },
    }

    path = tmp_path / "hrrr.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    return path


def _run(tmp_path, **kwargs):

    path = _write_artifact(tmp_path, **kwargs)

    return analyze_candidate_resource(
        state={
            "wind_resource_evidence": {
                "hrrr_met_summary_artifact": str(path)
            }
        },
        task={},
    )


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        analyze_candidate_resource(state={}, task={})


def test_missing_artifact_file_raises_file_not_found(tmp_path):

    with pytest.raises(FileNotFoundError):
        analyze_candidate_resource(
            state={
                "wind_resource_evidence": {
                    "hrrr_met_summary_artifact": str(
                        tmp_path / "missing.json"
                    )
                }
            },
            task={},
        )


def test_monthly_range_computed_from_monthly_values(tmp_path):

    result = _run(
        tmp_path,
        monthly={
            "2025-01": 8.5,
            "2025-02": 6.1,
            "2025-03": 9.9,
        },
    )

    assert result["finding"][
        "monthly_wind_speed_range_120m_mps"
    ] == [6.1, 9.9]


def test_monthly_range_is_none_when_no_monthly_data(tmp_path):

    result = _run(tmp_path, monthly={})

    assert (
        result["finding"]["monthly_wind_speed_range_120m_mps"]
        is None
    )


def test_single_month_range_collapses_to_equal_bounds(tmp_path):

    result = _run(tmp_path, monthly={"2025-06": 7.0})

    assert result["finding"][
        "monthly_wind_speed_range_120m_mps"
    ] == [7.0, 7.0]


def test_summary_statistics_mapped_through(tmp_path):

    result = _run(tmp_path)

    finding = result["finding"]

    assert finding["mean_wind_speed_120m_mps"] == 7.5
    assert finding["p10_wind_speed_120m_mps"] == 4.0
    assert finding["p90_wind_speed_120m_mps"] == 11.0
    assert finding["mean_wind_shear_alpha"] == 0.15
    assert (
        finding["prevailing_wind_direction_degrees"] == 200.0
    )
    assert finding["hourly_observation_count"] == 8760
    assert finding["missing_hourly_slot_count"] == 12
    # This project screens a single modeled calendar year -
    # always exactly 1, not derived from the artifact.
    assert finding["years_covered"] == 1
