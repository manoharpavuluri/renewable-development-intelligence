"""
Layer 1 — deterministic unit tests for terrain/slope artifact
field mapping and failure modes.
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.gis.terrain_screening import (
    analyze_terrain,
)


def _write_artifact(tmp_path, *, slope_thresholds=None):

    artifact = {
        "source": {
            "authority": "USGS",
            "dataset": "3DEP",
            "sample_resolution_m": 10,
        },
        "candidate_area_acres": 1000,
        "elevation_m": {
            "min": 500,
            "max": 620,
            "mean": 555,
            "relief": 120,
        },
        "slope_percent": {
            "mean": 4.2,
            "p50": 3.1,
            "p90": 9.8,
            "max": 22.5,
        },
        "slope_threshold_area": slope_thresholds or {},
    }

    path = tmp_path / "terrain.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    return path


def _run(tmp_path, **kwargs):

    path = _write_artifact(tmp_path, **kwargs)

    return analyze_terrain(
        state={
            "terrain_evidence": {
                "terrain_summary_artifact": str(path)
            }
        },
        task={},
    )


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        analyze_terrain(state={}, task={})


def test_missing_artifact_file_raises_file_not_found(tmp_path):

    with pytest.raises(FileNotFoundError):
        analyze_terrain(
            state={
                "terrain_evidence": {
                    "terrain_summary_artifact": str(
                        tmp_path / "missing.json"
                    )
                }
            },
            task={},
        )


def test_elevation_and_slope_fields_mapped_through(tmp_path):

    result = _run(tmp_path)

    finding = result["finding"]

    assert finding["elevation_min_m"] == 500
    assert finding["elevation_max_m"] == 620
    assert finding["relief_m"] == 120
    assert finding["slope_mean_percent"] == 4.2
    assert finding["slope_p90_percent"] == 9.8


def test_slope_threshold_acreage_mapped_through(tmp_path):

    result = _run(
        tmp_path,
        slope_thresholds={
            "gt_15pct": {
                "acres": 42.0,
                "percent_of_sampled_area": 4.2,
            },
            "gt_20pct": {
                "acres": 10.0,
                "percent_of_sampled_area": 1.0,
            },
        },
    )

    finding = result["finding"]

    assert finding["acres_over_15pct_slope"] == 42.0
    assert finding["percent_of_area_over_15pct_slope"] == 4.2
    assert finding["acres_over_20pct_slope"] == 10.0


def test_missing_slope_thresholds_default_to_none(tmp_path):

    result = _run(tmp_path, slope_thresholds={})

    finding = result["finding"]

    assert finding["acres_over_15pct_slope"] is None
    assert finding["percent_of_area_over_15pct_slope"] is None


def test_no_wind_thresholds_are_claimed_established(tmp_path):

    # This screening deliberately never claims to have
    # established a wind-development slope-suitability
    # threshold or constructability exclusion.
    result = _run(tmp_path)

    finding = result["finding"]

    assert (
        finding[
            "wind_development_slope_threshold_established"
        ]
        is False
    )
    assert (
        finding["constructability_exclusion_established"]
        is False
    )
