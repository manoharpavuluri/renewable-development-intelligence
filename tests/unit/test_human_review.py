"""
Layer 5 — human finalization workflow tests.

These verify that finalize_recommendation() is the only path to
human_approved: true, that it structurally requires a named
reviewer, and that overriding outside the deterministic
admissible set requires an explicit justification.
"""

from __future__ import annotations

import pytest

from renewable_intelligence.synthesis.human_review import (
    finalize_recommendation,
)
from renewable_intelligence.synthesis.recommendation_drafter import (
    RecommendationDraft,
)


def _draft_document(
    recommendation="ADVANCE_WITH_CONDITIONS",
    allowed_categories=None,
):

    return {
        "project_id": "TEST-PROJECT",
        "recommendation_policy": {
            "allowed_categories": (
                allowed_categories
                if allowed_categories is not None
                else ["ADVANCE_WITH_CONDITIONS", "HOLD"]
            ),
        },
        "recommendation_draft": {
            "recommendation": recommendation,
            "rationale": "test rationale",
            "critical_conditions": ["condition A"],
            "unresolved_risks": ["risk A"],
            "next_diligence": ["step A"],
            "confidence": "MEDIUM",
            "evidence_quality": "MEDIUM",
            "status": "DRAFT_PENDING_HUMAN_REVIEW",
            "human_review_required": True,
            "human_approved": False,
        },
    }


def test_recommendation_draft_schema_has_no_human_approved_field():

    # Structural guarantee: the LLM-facing pydantic schema
    # cannot express human_approved at all, so no agent code
    # path can set it.
    assert (
        "human_approved"
        not in RecommendationDraft.model_fields
    )


def test_reviewer_name_is_required():

    with pytest.raises(ValueError):

        finalize_recommendation(
            draft_document=_draft_document(),
            decision="approve",
            reviewer="",
        )


def test_reviewer_whitespace_only_is_rejected():

    with pytest.raises(ValueError):

        finalize_recommendation(
            draft_document=_draft_document(),
            decision="approve",
            reviewer="   ",
        )


def test_approve_sets_human_approved_true_and_keeps_draft_recommendation():

    result = finalize_recommendation(
        draft_document=_draft_document(
            recommendation="HOLD"
        ),
        decision="approve",
        reviewer="Jane Reviewer",
    )

    assert result["human_approved"] is True
    assert result["status"] == "FINAL"
    assert result["final_recommendation"] == "HOLD"
    assert (
        result["human_review"]["reviewed_by"]
        == "Jane Reviewer"
    )


def test_modify_without_override_recommendation_is_rejected():

    with pytest.raises(ValueError):

        finalize_recommendation(
            draft_document=_draft_document(),
            decision="modify",
            reviewer="Jane Reviewer",
        )


def test_modify_within_allowed_set_does_not_require_justification():

    result = finalize_recommendation(
        draft_document=_draft_document(
            allowed_categories=[
                "ADVANCE_WITH_CONDITIONS",
                "HOLD",
            ]
        ),
        decision="modify",
        reviewer="Jane Reviewer",
        override_recommendation="HOLD",
        comment="Prefer HOLD.",
    )

    assert result["final_recommendation"] == "HOLD"
    assert result["human_approved"] is True


def test_modify_outside_allowed_set_requires_justification():

    with pytest.raises(ValueError):

        finalize_recommendation(
            draft_document=_draft_document(
                allowed_categories=[
                    "ADVANCE_WITH_CONDITIONS",
                    "HOLD",
                ]
            ),
            decision="modify",
            reviewer="Jane Reviewer",
            override_recommendation="ADVANCE",
        )


def test_modify_outside_allowed_set_with_justification_succeeds():

    result = finalize_recommendation(
        draft_document=_draft_document(
            allowed_categories=[
                "ADVANCE_WITH_CONDITIONS",
                "HOLD",
            ]
        ),
        decision="modify",
        reviewer="Jane Reviewer",
        override_recommendation="ADVANCE",
        override_justification=(
            "Additional off-system evidence resolves the "
            "flagged risks."
        ),
    )

    assert result["final_recommendation"] == "ADVANCE"
    assert result["human_approved"] is True
    assert (
        "override_justification" in result["human_review"]
    )


def test_reject_requires_comment():

    with pytest.raises(ValueError):

        finalize_recommendation(
            draft_document=_draft_document(),
            decision="reject",
            reviewer="Jane Reviewer",
        )


def test_reject_sets_human_approved_false_and_no_final_recommendation():

    result = finalize_recommendation(
        draft_document=_draft_document(),
        decision="reject",
        reviewer="Jane Reviewer",
        comment="Not ready.",
    )

    assert result["human_approved"] is False
    assert result["status"] == "REJECTED"
    assert result["final_recommendation"] is None


def test_original_draft_is_preserved_verbatim():

    draft_document = _draft_document()

    result = finalize_recommendation(
        draft_document=draft_document,
        decision="approve",
        reviewer="Jane Reviewer",
    )

    assert result["original_draft"] == draft_document
