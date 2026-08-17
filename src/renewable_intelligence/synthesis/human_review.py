from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

ALLOWED_RECOMMENDATIONS = {
    "ADVANCE",
    "ADVANCE_WITH_CONDITIONS",
    "HOLD",
    "DO_NOT_ADVANCE",
}

Decision = Literal["approve", "modify", "reject"]


def finalize_recommendation(
    *,
    draft_document: dict[str, Any],
    decision: Decision,
    reviewer: str,
    comment: str | None = None,
    override_recommendation: str | None = None,
    override_justification: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:

    """
    Apply a human review decision to a draft recommendation.

    This is the ONLY function in the codebase that may set
    human_approved: true. No LLM-facing schema (see
    recommendation_drafter.RecommendationDraft) exposes a
    human_approved field at all, so an agent has no code path
    that can set it; only an explicit call to this function,
    made by whatever caller is standing in for the human
    reviewer, can.
    """

    if not reviewer or not reviewer.strip():

        raise ValueError(
            "A named human reviewer is required to finalize "
            "a recommendation."
        )

    draft = draft_document["recommendation_draft"]

    allowed_categories = (
        draft_document.get("recommendation_policy", {}).get(
            "allowed_categories"
        )
        or []
    )

    reviewed_at = (
        now or datetime.now(timezone.utc)
    ).isoformat()

    review_record: dict[str, Any] = {
        "decision": decision,
        "reviewed_by": reviewer,
        "reviewed_at": reviewed_at,
        "comment": comment,
    }

    if decision == "approve":

        final_recommendation = draft["recommendation"]
        human_approved = True
        status = "FINAL"

    elif decision == "modify":

        if not override_recommendation:

            raise ValueError(
                "override_recommendation is required when "
                "decision is 'modify'."
            )

        if (
            override_recommendation
            not in ALLOWED_RECOMMENDATIONS
        ):

            raise ValueError(
                "override_recommendation must be one of "
                f"{sorted(ALLOWED_RECOMMENDATIONS)}, got "
                f"{override_recommendation!r}."
            )

        if (
            allowed_categories
            and override_recommendation
            not in allowed_categories
            and not override_justification
        ):

            raise ValueError(
                f"override_recommendation "
                f"{override_recommendation!r} falls outside "
                "the deterministic admissible set "
                f"{allowed_categories!r} computed for this "
                "screening; override_justification is required "
                "to record why the human reviewer is going "
                "beyond it."
            )

        final_recommendation = override_recommendation
        human_approved = True
        status = "FINAL"

        review_record["override_recommendation"] = (
            override_recommendation
        )

        if override_justification:

            review_record["override_justification"] = (
                override_justification
            )

    elif decision == "reject":

        if not comment:

            raise ValueError(
                "comment is required when decision is "
                "'reject'."
            )

        final_recommendation = None
        human_approved = False
        status = "REJECTED"

    else:

        raise ValueError(f"Unknown decision: {decision!r}")

    return {
        "project_id": draft_document.get("project_id"),
        "original_draft": draft_document,
        "human_review": review_record,
        "final_recommendation": final_recommendation,
        "human_approved": human_approved,
        "status": status,
    }
