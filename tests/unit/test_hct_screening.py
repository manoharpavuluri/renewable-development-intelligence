"""
Layer 1 — deterministic unit tests for HCT artifact parsing and
screening-ranking logic. No LLM calls, no network calls.
"""

from __future__ import annotations

import csv

import pytest

from renewable_intelligence.interconnection.hct_screening import (
    hct_screening_ranking_key,
    rank_pois,
    read_hct_rows,
    screening_preferred_poi,
    summarize_hct_artifact,
    to_float,
)


def _write_csv(path, fieldnames, rows):

    with path.open("w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path


# --- to_float -----------------------------------------------


def test_to_float_none_is_none():
    assert to_float(None) is None


def test_to_float_empty_string_is_none():
    assert to_float("") is None


def test_to_float_whitespace_only_is_none():
    assert to_float("   ") is None


def test_to_float_valid_numeric_string():
    assert to_float("0.9999") == 0.9999


def test_to_float_malformed_value_raises():

    # A field this project reads as a number that instead
    # contains non-numeric text is a real data-integrity problem
    # and must fail loudly, not be silently coerced to 0/None.
    with pytest.raises(ValueError):
        to_float("N/A")


# --- read_hct_rows --------------------------------------------


def test_read_hct_rows_missing_file_raises(tmp_path):

    with pytest.raises(FileNotFoundError):
        read_hct_rows(tmp_path / "does_not_exist.csv")


def test_read_hct_rows_malformed_csv_missing_column(tmp_path):

    # A row with a missing trailing column still parses (csv
    # module leaves the value as None), so this must not crash
    # the row-reading step itself - only downstream numeric
    # parsing of a genuinely non-numeric value should raise.
    csv_path = tmp_path / "malformed.csv"

    csv_path.write_text(
        "preShiftLoading,postShiftLoading\n0.5\n",
        encoding="utf-8",
    )

    rows = read_hct_rows(csv_path)

    assert rows[0]["preShiftLoading"] == "0.5"
    assert rows[0].get("postShiftLoading") is None


# --- summarize_hct_artifact: threshold crossing ----------------


def test_below_threshold_not_counted_as_overload(tmp_path):

    csv_path = _write_csv(
        tmp_path / "hct.csv",
        [
            "preShiftLoading",
            "postShiftLoading",
            "availableCapacity",
            "shiftFactor",
            "impact",
        ],
        [
            {
                "preShiftLoading": "0.9",
                "postShiftLoading": "0.9999",
                "availableCapacity": "10",
                "shiftFactor": "0.1",
                "impact": "1",
            }
        ],
    )

    summary = summarize_hct_artifact(csv_path)

    assert summary["post_shift_overload_count"] == 0
    assert summary["new_overload_crossing_count"] == 0


def test_exactly_at_threshold_counts_as_overload(tmp_path):

    csv_path = _write_csv(
        tmp_path / "hct.csv",
        [
            "preShiftLoading",
            "postShiftLoading",
            "availableCapacity",
            "shiftFactor",
            "impact",
        ],
        [
            {
                "preShiftLoading": "0.9",
                "postShiftLoading": "1.0",
                "availableCapacity": "10",
                "shiftFactor": "0.1",
                "impact": "1",
            }
        ],
    )

    summary = summarize_hct_artifact(csv_path)

    assert summary["post_shift_overload_count"] == 1
    assert summary["new_overload_crossing_count"] == 1


def test_missing_pre_or_post_value_excluded_from_crossing_count(
    tmp_path,
):

    csv_path = _write_csv(
        tmp_path / "hct.csv",
        [
            "preShiftLoading",
            "postShiftLoading",
            "availableCapacity",
            "shiftFactor",
            "impact",
        ],
        [
            {
                "preShiftLoading": "",
                "postShiftLoading": "1.2",
                "availableCapacity": "10",
                "shiftFactor": "0.1",
                "impact": "1",
            }
        ],
    )

    summary = summarize_hct_artifact(csv_path)

    # postShiftLoading is still counted toward overload counts
    # (only the crossing/aggravation logic needs both values).
    assert summary["post_shift_overload_count"] == 1
    assert summary["new_overload_crossing_count"] == 0
    assert summary["existing_overload_aggravation_count"] == 0


def test_existing_overload_aggravated_when_post_exceeds_pre(
    tmp_path,
):

    csv_path = _write_csv(
        tmp_path / "hct.csv",
        [
            "preShiftLoading",
            "postShiftLoading",
            "availableCapacity",
            "shiftFactor",
            "impact",
        ],
        [
            {
                "preShiftLoading": "1.05",
                "postShiftLoading": "1.4",
                "availableCapacity": "10",
                "shiftFactor": "0.1",
                "impact": "1",
            }
        ],
    )

    summary = summarize_hct_artifact(csv_path)

    assert summary["existing_overload_aggravation_count"] == 1
    # Already overloaded pre-shift, so this is not a NEW crossing.
    assert summary["new_overload_crossing_count"] == 0


def test_existing_overload_not_aggravated_when_post_does_not_increase(
    tmp_path,
):

    csv_path = _write_csv(
        tmp_path / "hct.csv",
        [
            "preShiftLoading",
            "postShiftLoading",
            "availableCapacity",
            "shiftFactor",
            "impact",
        ],
        [
            {
                "preShiftLoading": "1.2",
                "postShiftLoading": "1.2",
                "availableCapacity": "10",
                "shiftFactor": "0.1",
                "impact": "1",
            }
        ],
    )

    summary = summarize_hct_artifact(csv_path)

    assert summary["existing_overload_aggravation_count"] == 0


def test_summary_sha256_and_row_count(tmp_path):

    csv_path = _write_csv(
        tmp_path / "hct.csv",
        [
            "preShiftLoading",
            "postShiftLoading",
            "availableCapacity",
            "shiftFactor",
            "impact",
        ],
        [
            {
                "preShiftLoading": "0.5",
                "postShiftLoading": "0.6",
                "availableCapacity": "10",
                "shiftFactor": "0.1",
                "impact": "1",
            },
            {
                "preShiftLoading": "0.6",
                "postShiftLoading": "0.7",
                "availableCapacity": "5",
                "shiftFactor": "0.2",
                "impact": "2",
            },
        ],
    )

    import hashlib

    expected_sha256 = hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()

    summary = summarize_hct_artifact(csv_path)

    assert summary["row_count"] == 2
    assert summary["sha256"] == expected_sha256


# --- ranking / screening_preferred_poi -------------------------


def _summary(
    *,
    post_overload=0,
    pre_overload=0,
    worst_post=None,
    row_count=1,
):

    return {
        "post_shift_overload_count": post_overload,
        "pre_shift_overload_count": pre_overload,
        "worst_post_shift_loading": worst_post,
        "row_count": row_count,
    }


def test_ranking_key_prefers_fewer_post_overloads():

    better = hct_screening_ranking_key(
        _summary(post_overload=0)
    )
    worse = hct_screening_ranking_key(
        _summary(post_overload=1)
    )

    assert better < worse


def test_ranking_key_missing_worst_post_sorts_last():

    with_value = hct_screening_ranking_key(
        _summary(worst_post=0.5)
    )
    missing_value = hct_screening_ranking_key(
        _summary(worst_post=None)
    )

    assert with_value < missing_value


def test_rank_pois_orders_best_first():

    summaries = {
        "poi_b": _summary(post_overload=1),
        "poi_a": _summary(post_overload=0),
    }

    assert rank_pois(summaries) == ["poi_a", "poi_b"]


def test_screening_preferred_poi_with_single_summary_is_none():

    assert (
        screening_preferred_poi({"poi_a": _summary()}) is None
    )


def test_screening_preferred_poi_tie_returns_none():

    summaries = {
        "poi_a": _summary(post_overload=0, worst_post=0.5),
        "poi_b": _summary(post_overload=0, worst_post=0.5),
    }

    assert screening_preferred_poi(summaries) is None


def test_screening_preferred_poi_clear_winner():

    summaries = {
        "poi_a": _summary(post_overload=1),
        "poi_b": _summary(post_overload=0),
    }

    assert screening_preferred_poi(summaries) == "poi_b"
