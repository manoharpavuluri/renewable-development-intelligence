"""
Layer 1 — deterministic unit tests for NLCD land-cover artifact
field mapping, dominant-class selection, and failure modes.
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.gis.land_cover_screening import (
    analyze_land_cover,
)


def _write_artifact(tmp_path, *, classes=None, class_groups=None):

    artifact = {
        "source": {
            "authority": "USGS/MRLC",
            "dataset": "NLCD",
            "sample_resolution_m": 30,
        },
        "candidate_area_acres": 1000,
        "sampled_area_acres": 995,
        "classes": classes or [],
        "class_group_summary": class_groups or {},
    }

    path = tmp_path / "land_cover.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    return path


def _run(tmp_path, **kwargs):

    path = _write_artifact(tmp_path, **kwargs)

    return analyze_land_cover(
        state={
            "land_cover_evidence": {
                "land_cover_summary_artifact": str(path)
            }
        },
        task={},
    )


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        analyze_land_cover(state={}, task={})


def test_missing_artifact_file_raises_file_not_found(tmp_path):

    with pytest.raises(FileNotFoundError):
        analyze_land_cover(
            state={
                "land_cover_evidence": {
                    "land_cover_summary_artifact": str(
                        tmp_path / "missing.json"
                    )
                }
            },
            task={},
        )


def test_dominant_class_is_first_in_list(tmp_path):

    result = _run(
        tmp_path,
        classes=[
            {
                "class_name": "Herbaceous",
                "percent_of_sampled_area": 61.4,
            },
            {
                "class_name": "Cultivated Crops",
                "percent_of_sampled_area": 30.1,
            },
        ],
    )

    finding = result["finding"]

    assert finding["dominant_class_name"] == "Herbaceous"
    assert finding["dominant_class_percent"] == 61.4
    assert finding["class_count"] == 2


def test_empty_classes_list_dominant_class_is_none(tmp_path):

    result = _run(tmp_path, classes=[])

    finding = result["finding"]

    assert finding["dominant_class_name"] is None
    assert finding["dominant_class_percent"] is None
    assert finding["class_count"] == 0


def test_class_group_acreages_mapped_through(tmp_path):

    result = _run(
        tmp_path,
        class_groups={
            "developed_acres": 12.0,
            "developed_percent_of_candidate": 1.2,
            "wetland_acres": 5.0,
            "cultivated_pasture_acres": 400.0,
            "grass_shrub_acres": 583.0,
        },
    )

    finding = result["finding"]

    assert finding["developed_acres"] == 12.0
    assert finding["wetland_acres"] == 5.0
    assert finding["cultivated_pasture_acres"] == 400.0
    assert finding["grass_shrub_acres"] == 583.0


def test_no_land_cover_class_treated_as_exclusion(tmp_path):

    result = _run(tmp_path)

    finding = result["finding"]

    assert finding["developable_acreage_established"] is False
    assert (
        finding["layout_compatibility_established"] is False
    )
