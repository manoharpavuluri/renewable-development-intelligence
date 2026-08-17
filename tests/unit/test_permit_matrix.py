"""
Layer 1 — deterministic unit tests for the regulatory permit
matrix: legislative-status entry construction, requirement-status
counting, and evidence-driven conditional triggers.
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.regulatory.permit_matrix import (
    _build_legislative_requirement_entries,
    build_permit_matrix,
)


def _write_jurisdiction_artifact(tmp_path):

    path = tmp_path / "jurisdiction.json"
    path.write_text(
        json.dumps(
            {
                "county_name": "Dewey",
                "state_name": "Oklahoma",
            }
        ),
        encoding="utf-8",
    )

    return path


def _write_legislative_artifact(tmp_path, bills):

    path = tmp_path / "legislative_status.json"
    path.write_text(
        json.dumps(
            {
                "source": {"verified_utc": "2026-08-15T00:00:00Z"},
                "bills": bills,
            }
        ),
        encoding="utf-8",
    )

    return path


def _bill(
    bill_id,
    *,
    status,
    session="2025-2026",
    subject="Wind setback",
    last_action="Failed to pass",
    last_action_date="2026-05-01",
):

    return {
        "bill": bill_id,
        "legislative_session": session,
        "subject": subject,
        "status": status,
        "last_action": last_action,
        "last_action_date": last_action_date,
        "source_urls": ["https://example.gov/bill"],
    }


def _run(
    tmp_path,
    *,
    bills,
    state_overrides=None,
):

    jurisdiction_path = _write_jurisdiction_artifact(tmp_path)
    legislative_path = _write_legislative_artifact(
        tmp_path, bills
    )

    state = {
        "project_domain_outcomes": {},
        **(state_overrides or {}),
    }

    return build_permit_matrix(
        state=state,
        task={
            "regulatory_evidence": {
                "jurisdiction_summary_artifact": str(
                    jurisdiction_path
                ),
                "legislative_status_artifact": str(
                    legislative_path
                ),
            }
        },
    )


# --- evidence resolution failure modes --------------------------


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        build_permit_matrix(state={}, task={})


def test_missing_jurisdiction_artifact_raises_runtime_error():

    with pytest.raises(RuntimeError):
        build_permit_matrix(
            state={},
            task={"regulatory_evidence": {}},
        )


def test_missing_legislative_status_artifact_raises_runtime_error(
    tmp_path,
):

    jurisdiction_path = _write_jurisdiction_artifact(tmp_path)

    with pytest.raises(RuntimeError):
        build_permit_matrix(
            state={},
            task={
                "regulatory_evidence": {
                    "jurisdiction_summary_artifact": str(
                        jurisdiction_path
                    )
                }
            },
        )


def test_missing_legislative_status_file_raises_file_not_found(
    tmp_path,
):

    jurisdiction_path = _write_jurisdiction_artifact(tmp_path)

    with pytest.raises(FileNotFoundError):
        build_permit_matrix(
            state={},
            task={
                "regulatory_evidence": {
                    "jurisdiction_summary_artifact": str(
                        jurisdiction_path
                    ),
                    "legislative_status_artifact": str(
                        tmp_path / "missing.json"
                    ),
                }
            },
        )


# --- _build_legislative_requirement_entries ----------------------


def test_legislative_entry_built_per_bill():

    entries = _build_legislative_requirement_entries(
        {
            "source": {"verified_utc": "2026-08-15T00:00:00Z"},
            "bills": [
                _bill("SB2", status="FAILED"),
                _bill("HB2751", status="FAILED"),
            ],
        }
    )

    assert len(entries) == 2
    assert entries[0]["requirement_id"] == "OK_LEGISLATION_SB2"
    assert entries[0]["status"] == "FAILED"
    assert (
        entries[0]["verified_utc"] == "2026-08-15T00:00:00Z"
    )


def test_legislative_entries_empty_when_no_bills():

    entries = _build_legislative_requirement_entries(
        {"source": {}, "bills": []}
    )

    assert entries == []


# --- requirement-status counting ---------------------------------


def test_counts_established_and_failed_legislation(tmp_path):

    result = _run(
        tmp_path,
        bills=[
            _bill("SB2", status="FAILED"),
            _bill("HB2751", status="FAILED"),
        ],
    )

    finding = result["finding"]

    # 4 always-present KNOWN_REQUIREMENT_CATEGORIES entries are
    # ESTABLISHED_REQUIREMENT (FAA, state registration, setback,
    # SPP), 1 is NOT_YET_VERIFIED (county zoning).
    assert finding["established_requirement_count"] == 4
    assert finding["not_yet_verified_count"] == 1
    assert finding["failed_legislation_count"] == 2
    assert finding["pending_not_enacted_count"] == 0


def test_counts_pending_legislation(tmp_path):

    result = _run(
        tmp_path,
        bills=[_bill("SB99", status="PENDING_NOT_ENACTED")],
    )

    assert result["finding"]["pending_not_enacted_count"] == 1
    assert result["finding"]["failed_legislation_count"] == 0


def test_no_bills_tracked_produces_zero_legislation_counts(
    tmp_path,
):

    result = _run(tmp_path, bills=[])

    assert result["finding"]["failed_legislation_count"] == 0
    assert result["finding"]["pending_not_enacted_count"] == 0


# --- conditional triggers driven by prior domain evidence --------


def test_no_conditional_triggers_without_prior_domain_outcomes(
    tmp_path,
):

    result = _run(tmp_path, bills=[])

    assert result["conditional_triggers"] == []
    assert result["finding"]["conditional_trigger_count"] == 0


def test_esa_trigger_flagged_when_species_domain_present(
    tmp_path,
):

    result = _run(
        tmp_path,
        bills=[],
        state_overrides={
            "project_domain_outcomes": {
                "species": {"resolved_uncertainty": ["x"]}
            }
        },
    )

    trigger_ids = {
        t["requirement_id"] for t in result["conditional_triggers"]
    }

    assert "ESA_SECTION_7_CONSULTATION_FLAGGED" in trigger_ids
    assert result["finding"]["conditional_trigger_count"] == 1


def test_nhpa_trigger_flagged_when_land_status_domain_present(
    tmp_path,
):

    result = _run(
        tmp_path,
        bills=[],
        state_overrides={
            "project_domain_outcomes": {
                "land_status": {"resolved_uncertainty": ["x"]}
            }
        },
    )

    trigger_ids = {
        t["requirement_id"] for t in result["conditional_triggers"]
    }

    assert "TRIBAL_NHPA_CONSULTATION_FLAGGED" in trigger_ids


def test_both_triggers_flagged_when_both_domains_present(
    tmp_path,
):

    result = _run(
        tmp_path,
        bills=[],
        state_overrides={
            "project_domain_outcomes": {
                "species": {"resolved_uncertainty": []},
                "land_status": {"resolved_uncertainty": []},
            }
        },
    )

    assert result["finding"]["conditional_trigger_count"] == 2
