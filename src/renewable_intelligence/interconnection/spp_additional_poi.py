from __future__ import annotations

from pathlib import Path
from typing import Any

from renewable_intelligence.interconnection.hct_screening import (
    rank_pois,
    screening_preferred_poi as choose_screening_preferred_poi,
    summarize_hct_artifact,
)


CAPABILITY_NAME = (
    "spp.evaluate_additional_poi"
)


def _resolve_evidence(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get(
            "additional_poi_evidence"
        )
        or (
            state.get(
                "recommended_follow_up"
            )
            or {}
        ).get(
            "additional_poi_evidence"
        )
        or state.get(
            "spp_additional_poi_evidence"
        )
    )

    if not evidence:

        raise RuntimeError(
            "spp.evaluate_additional_poi "
            "requires governed additional-POI "
            "evidence references."
        )

    return evidence


def evaluate_additional_poi(
    *,
    state,
    task,
) -> dict[str, Any]:

    evidence = _resolve_evidence(
        state=state,
        task=task,
    )

    model_cases = evidence.get(
        "model_cases"
    )

    if not model_cases:

        raise RuntimeError(
            "Additional-POI evidence has no "
            "model_cases."
        )


    model_results: dict[
        str,
        dict[str, Any],
    ] = {}

    expected_pois: set[str] | None = None


    for case_id, case in (
        model_cases.items()
    ):

        model_name = case.get(
            "model"
        )

        poi_artifacts = case.get(
            "pois"
        )

        if not model_name:

            raise RuntimeError(
                f"Model case {case_id!r} "
                "has no model name."
            )

        if not poi_artifacts:

            raise RuntimeError(
                f"Model case {case_id!r} "
                "has no POI artifacts."
            )


        current_pois = set(
            poi_artifacts.keys()
        )

        if expected_pois is None:

            expected_pois = (
                current_pois
            )

        elif (
            current_pois
            != expected_pois
        ):

            raise RuntimeError(
                "All model cases must evaluate "
                "the same expanded POI set."
            )


        summaries = {
            poi_name: (
                summarize_hct_artifact(
                    Path(
                        artifact
                    )
                )
            )
            for poi_name, artifact
            in poi_artifacts.items()
        }


        ranking = rank_pois(
            summaries
        )


        model_results[
            case_id
        ] = {
            "model": (
                model_name
            ),

            "poi_results": (
                summaries
            ),

            "screening_ranking": (
                ranking
            ),

            "screening_preferred_poi": (
                choose_screening_preferred_poi(
                    summaries
                )
            ),
        }


    preferred_by_case = {
        case_id: result.get(
            "screening_preferred_poi"
        )
        for case_id, result
        in model_results.items()
    }


    preferred_values = list(
        preferred_by_case.values()
    )


    if (
        preferred_values
        and all(
            value is not None
            for value
            in preferred_values
        )
        and len(
            set(
                preferred_values
            )
        )
        == 1
    ):

        expanded_set_status = (
            "PREFERENCE_ROBUST_ACROSS_TESTED_CASES"
        )

        screening_preferred_poi = (
            preferred_values[0]
        )

    elif (
        len(
            {
                value
                for value
                in preferred_values
                if value is not None
            }
        )
        > 1
    ):

        expanded_set_status = (
            "MODEL_SENSITIVE"
        )

        screening_preferred_poi = (
            None
        )

    else:

        expanded_set_status = (
            "INCONCLUSIVE"
        )

        screening_preferred_poi = (
            None
        )


    additional_pois = list(
        evidence.get(
            "additional_pois",
            []
        )
    )


    displaced_existing_preference = (
        screening_preferred_poi
        in additional_pois
        if screening_preferred_poi
        else False
    )


    return {
        "task_id": (
            task.get(
                "task_id"
            )
            or task.get(
                "action_id"
            )
        ),

        "capability": (
            CAPABILITY_NAME
        ),

        "executed": True,

        "relationship": (
            "CANDIDATE_SCREENING"
        ),

        "finding": {
            "expanded_set_status": (
                expanded_set_status
            ),

            "screening_preferred_poi": (
                screening_preferred_poi
            ),

            "preferred_poi_by_model_case": (
                preferred_by_case
            ),

            "tested_model_count": len(
                model_results
            ),

            "tested_poi_count": len(
                expected_pois
                or []
            ),

            "additional_pois_tested": (
                additional_pois
            ),

            "additional_poi_displaced_existing_preference": (
                displaced_existing_preference
            ),
        },

        "model_cases": (
            model_results
        ),

        "evidence_quality": (
            "HIGH"
        ),

        "candidate_applicability": (
            "MEDIUM"
        ),

        "interpretation_limits": [
            (
                "The result applies only to the "
                "SPP HCT model cases and POIs "
                "explicitly supplied."
            ),
            (
                "An additional screened POI does "
                "not establish that all plausible "
                "POIs have been evaluated."
            ),
            (
                "HCT screening does not establish "
                "generator-interconnection feasibility."
            ),
            (
                "The result does not establish "
                "candidate-specific network-upgrade "
                "cost."
            ),
            (
                "The result does not establish a "
                "constructible gen-tie route or ROW "
                "availability."
            ),
            (
                "A screening-preferred POI is not "
                "necessarily the globally optimal "
                "or ultimately feasible POI."
            ),
            (
                "availableCapacity is retained as "
                "a raw HCT field and is not "
                "interpreted as hosting capacity."
            ),
        ],
    }
