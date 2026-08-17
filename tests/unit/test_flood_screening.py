"""
Layer 1 — deterministic unit tests for FEMA NFHL coverage-status
classification (NO_DIGITAL_COVERAGE / PARTIAL_COVERAGE /
FULL_COVERAGE) and the evidence-quality/candidate-applicability
labels derived from it.
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.gis.flood_screening import (
    resolve_flood_evidence,
)


def _write_artifact(tmp_path, *, mapped_percent, unmapped_percent):

    artifact = {
        "source": {"authority": "FEMA"},
        "candidate_area_acres": 1000,
        "nfhl_mapped_coverage": {
            "acres": 1000 * (mapped_percent or 0) / 100,
            "percent": mapped_percent,
        },
        "nfhl_unmapped_or_unknown": {
            "acres": 1000 * (unmapped_percent or 0) / 100,
            "percent": unmapped_percent,
        },
        "special_flood_hazard_area": {},
        "zones": {},
    }

    path = tmp_path / "fema.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    return path


def _run(tmp_path, *, mapped_percent, unmapped_percent):

    path = _write_artifact(
        tmp_path,
        mapped_percent=mapped_percent,
        unmapped_percent=unmapped_percent,
    )

    return resolve_flood_evidence(
        state={
            "flood_evidence": {
                "fema_nfhl_summary_artifact": str(path)
            }
        },
        task={},
    )


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        resolve_flood_evidence(state={}, task={})


def test_missing_artifact_file_raises_file_not_found(tmp_path):

    with pytest.raises(FileNotFoundError):
        resolve_flood_evidence(
            state={
                "flood_evidence": {
                    "fema_nfhl_summary_artifact": str(
                        tmp_path / "missing.json"
                    )
                }
            },
            task={},
        )


def test_zero_mapped_coverage_is_no_digital_coverage(tmp_path):

    result = _run(
        tmp_path, mapped_percent=0.0, unmapped_percent=100.0
    )

    finding = result["finding"]

    assert (
        finding["nfhl_coverage_status"] == "NO_DIGITAL_COVERAGE"
    )
    assert result["evidence_quality"] == "LOW"
    assert result["candidate_applicability"] == "LOW"


def test_full_mapped_coverage_is_full_coverage(tmp_path):

    result = _run(
        tmp_path, mapped_percent=100.0, unmapped_percent=0.0
    )

    finding = result["finding"]

    assert finding["nfhl_coverage_status"] == "FULL_COVERAGE"
    assert result["evidence_quality"] == "MEDIUM"
    assert result["candidate_applicability"] == "HIGH"


def test_partial_mapped_coverage_is_partial_coverage(tmp_path):

    result = _run(
        tmp_path, mapped_percent=60.0, unmapped_percent=40.0
    )

    finding = result["finding"]

    assert finding["nfhl_coverage_status"] == "PARTIAL_COVERAGE"
    assert result["evidence_quality"] == "MEDIUM"
    assert result["candidate_applicability"] == "HIGH"


def test_missing_percent_values_do_not_crash_and_default_full(
    tmp_path,
):

    # Neither branch condition is satisfiable when the percent
    # fields are missing/None (isinstance checks fail both), so
    # this falls through to FULL_COVERAGE - a real edge case
    # worth pinning down explicitly rather than leaving implicit.
    artifact = {
        "source": {"authority": "FEMA"},
        "candidate_area_acres": 1000,
        "nfhl_mapped_coverage": {},
        "nfhl_unmapped_or_unknown": {},
        "special_flood_hazard_area": {},
        "zones": {},
    }

    path = tmp_path / "fema.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    result = resolve_flood_evidence(
        state={
            "flood_evidence": {
                "fema_nfhl_summary_artifact": str(path)
            }
        },
        task={},
    )

    assert (
        result["finding"]["nfhl_coverage_status"]
        == "FULL_COVERAGE"
    )
