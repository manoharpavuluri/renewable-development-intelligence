from __future__ import annotations

from pathlib import Path
from typing import Any

from renewable_intelligence.interconnection.hct_screening import (
    screening_preferred_poi as choose_screening_preferred_poi,
    summarize_hct_artifact,
)


CAPABILITY_NAME = (
    "spp.compare_model_cases"
)


def _resolve_model_cases(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    model_cases = (
        task.get(
            "model_cases"
        )
        or (
            state.get(
                "recommended_follow_up"
            )
            or {}
        ).get(
            "model_cases"
        )
        or state.get(
            "spp_hct_model_cases"
        )
    )

    if not model_cases:

        raise RuntimeError(
            "spp.compare_model_cases requires "
            "model_cases evidence references."
        )

    if len(model_cases) < 2:

        raise RuntimeError(
            "At least two HCT model cases "
            "are required for comparison."
        )

    return model_cases


def compare_model_cases(
    *,
    state,
    task,
) -> dict[str, Any]:

    """
    Compare the same candidate POIs across multiple
    SPP HCT model cases.

    The capability computes screening evidence only.
    It does not determine interconnection feasibility,
    final POI selection, or candidate upgrade cost.
    """

    model_cases = _resolve_model_cases(
        state=state,
        task=task,
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
                "the same POI set for a controlled "
                "cross-model comparison."
            )


        summaries = {}

        for poi_name, artifact in (
            poi_artifacts.items()
        ):

            summaries[
                poi_name
            ] = summarize_hct_artifact(
                Path(
                    artifact
                )
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

            "screening_preferred_poi": (
                choose_screening_preferred_poi(
                    summaries
                )
            ),
        }


    preferred_by_case = {
        case_id: result[
            "screening_preferred_poi"
        ]
        for case_id, result
        in model_results.items()
    }


    preferred_values = list(
        preferred_by_case.values()
    )


    if (
        all(
            value is not None
            for value in preferred_values
        )
        and
        len(
            set(
                preferred_values
            )
        )
        == 1
    ):

        sensitivity_status = (
            "ROBUST_ACROSS_TESTED_CASES"
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

        sensitivity_status = (
            "MODEL_SENSITIVE"
        )

        screening_preferred_poi = (
            None
        )

    else:

        sensitivity_status = (
            "INCONCLUSIVE"
        )

        screening_preferred_poi = (
            None
        )


    export_unchanged_by_poi = {}

    for poi_name in sorted(
        expected_pois
        or []
    ):

        hashes = {
            case[
                "poi_results"
            ][
                poi_name
            ][
                "sha256"
            ]
            for case in (
                model_results.values()
            )
        }

        export_unchanged_by_poi[
            poi_name
        ] = (
            len(hashes)
            == 1
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
            "sensitivity_status": (
                sensitivity_status
            ),

            "screening_preferred_poi": (
                screening_preferred_poi
            ),

            "preferred_poi_by_model_case": (
                preferred_by_case
            ),

            "export_unchanged_by_poi": (
                export_unchanged_by_poi
            ),

            "tested_model_count": (
                len(
                    model_results
                )
            ),

            "tested_poi_count": (
                len(
                    expected_pois
                    or []
                )
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
                "The result applies only to "
                "the HCT model cases and POIs "
                "explicitly supplied."
            ),

            (
                "Identical exported results do "
                "not establish that the underlying "
                "SPP network models are identical."
            ),

            (
                "HCT screening does not establish "
                "generator-interconnection feasibility."
            ),

            (
                "The result does not establish "
                "candidate-specific upgrade cost."
            ),

            (
                "A screening-preferred POI is not "
                "necessarily the globally optimal "
                "or ultimately feasible POI."
            ),

            (
                "availableCapacity is preserved "
                "as a raw HCT field and is not "
                "interpreted as POI hosting capacity."
            ),
        ],
    }
