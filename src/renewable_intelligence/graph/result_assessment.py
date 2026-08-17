from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from renewable_intelligence.graph.state import (
    InvestigationState,
)


def audit_event(
    event_type: str,
    **details: Any,
) -> dict[str, Any]:

    return {
        "timestamp_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "event_type": event_type,
        **details,
    }


def assess_investigation_result(
    state: InvestigationState,
) -> dict[str, Any]:

    capability = state.get(
        "selected_capability"
    )

    result = (
        state.get(
            "investigation_result"
        )
        or {}
    )


    # ========================================================
    # 1. Initial SPP transmission-context investigation
    # ========================================================

    if capability == "spp.transmission_context":

        hct = result.get(
            "hct",
            {},
        )

        preferred = hct.get(
            "preferred_among_tested"
        )

        pois = hct.get(
            "pois",
            [],
        )

        study = result.get(
            "study_precedent",
            {},
        )

        unresolved = result.get(
            "unresolved",
            [],
        )


        sufficiency = {
            "domain": (
                "interconnection"
            ),

            "gate_id": "G2",

            "status": (
                "FOLLOW_UP_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "checks": {
                "candidate_poi_comparison_available": (
                    bool(preferred)
                ),

                "at_least_two_pois_compared": (
                    len(pois) >= 2
                ),

                "precedent_study_available": (
                    bool(
                        study.get(
                            "artifact_available"
                        )
                    )
                ),

                "multiple_hct_models_evaluated": (
                    False
                ),

                "gen_tie_context_established": (
                    False
                ),

                "upgrade_cost_established": (
                    False
                ),

                "interconnection_feasibility_established": (
                    False
                ),
            },

            "reason": (
                "Candidate-specific HCT screening and "
                "queue context exist, but the evidence "
                "does not yet establish final POI, "
                "interconnection feasibility, gen-tie "
                "context, or likely upgrade implications."
            ),

            "unresolved": (
                unresolved
            ),
        }


        if study.get(
            "artifact_available"
        ):

            follow_up = {
                "action_id": (
                    "INT-FU-001"
                ),

                "domain": (
                    "interconnection"
                ),

                "question": (
                    "What does the existing Tatonga "
                    "GEN-2026-PR2 SPP study reveal "
                    "about constraints, upgrades, "
                    "allocated costs, contingent "
                    "dependencies, and study limitations "
                    "relevant to our candidate?"
                ),

                "preferred_capability": (
                    "spp.analyze_precedent_study"
                ),

                "priority": (
                    "HIGH"
                ),

                "reason": (
                    "A relevant authoritative Tatonga "
                    "study artifact is already available. "
                    "Consume existing evidence before "
                    "requesting additional source data."
                ),

                "source_artifact": (
                    study.get(
                        "artifact_path"
                    )
                ),

                "relationship": (
                    "PRECEDENT_ONLY"
                ),

                "important_limit": (
                    "GEN-2026-PR2 is not our 250-MW "
                    "project and its costs or findings "
                    "must not be attributed directly "
                    "to RDI-WOK-250-001."
                ),
            }

        else:

            follow_up = {
                "action_id": (
                    "INT-FU-002"
                ),

                "domain": (
                    "interconnection"
                ),

                "question": (
                    "Does the candidate POI comparison "
                    "remain consistent under another "
                    "relevant SPP HCT model case?"
                ),

                "preferred_capability": (
                    "spp.compare_model_cases"
                ),

                "priority": (
                    "HIGH"
                ),

                "reason": (
                    "Only one HCT model case "
                    "has been evaluated."
                ),
            }


        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                follow_up
            ),

            "candidate_actions": [
                {
                    **follow_up,
                    "capability": (
                        follow_up[
                            "preferred_capability"
                        ]
                    ),
                    "continues_blocking_investigation": True,
                }
            ],

            "route_reason": (
                "Interconnection evidence is useful "
                "but insufficient; follow-up required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G2",
                        status=(
                            "FOLLOW_UP_REQUIRED"
                        ),
                        recommended_action=(
                            follow_up[
                                "action_id"
                            ]
                        ),
                    )
                ]
            ),
        }


    # ========================================================
    # 2. Tatonga precedent-study investigation
    # ========================================================

    if capability == "spp.analyze_precedent_study":

        study = result.get(
            "study",
            {},
        )

        cost = result.get(
            "cost_context",
            {},
        )

        thermal = result.get(
            "thermal",
            {},
        )

        short_circuit = result.get(
            "short_circuit",
            {},
        )

        scrcct = result.get(
            "scrcct",
            {},
        )


        checks = {
            "precedent_study_parsed": (
                bool(
                    study.get(
                        "study_id"
                    )
                )
            ),

            "same_poi_context": (
                "Tatonga"
                in str(
                    study.get(
                        "poi",
                        ""
                    )
                )
            ),

            "cost_semantics_distinguished": (
                (
                    "known_allocated_upgrade_cost_total"
                    in cost
                )
                and (
                    "known_total_upgrade_cost_represented"
                    in cost
                )
            ),

            "thermal_context_available": (
                thermal.get(
                    "result_count"
                )
                is not None
            ),

            "short_circuit_context_available": (
                short_circuit.get(
                    "buses_analyzed"
                )
                is not None
            ),

            "scrcct_context_available": (
                scrcct.get(
                    "cases_analyzed"
                )
                is not None
            ),

            "candidate_specific_study": (
                False
            ),

            "candidate_upgrade_cost_established": (
                False
            ),

            "interconnection_feasibility_established": (
                False
            ),
        }


        sufficiency = {
            "domain": (
                "interconnection"
            ),

            "gate_id": (
                "G2"
            ),

            "status": (
                "FOLLOW_UP_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "checks": checks,

            "reason": (
                "The Tatonga precedent adds useful "
                "constraint, upgrade, stability, and "
                "cost-context evidence, but it is a "
                "41.89-MW precedent rather than the "
                "250-MW candidate project. It therefore "
                "cannot establish candidate feasibility "
                "or candidate upgrade cost."
            ),

            "precedent_evidence_confidence": (
                result.get(
                    "precedent_evidence_confidence"
                )
            ),

            "candidate_applicability_confidence": (
                result.get(
                    "candidate_applicability_confidence"
                )
            ),
        }


        # ----------------------------------------------------
        # Next deterministic investigation:
        #
        # We now know one HCT model case and one precedent
        # study. Test whether the POI conclusion is robust
        # across another relevant HCT model before relying
        # more heavily on the Tatonga preference.
        # ----------------------------------------------------

        candidate_actions = [
            {
                "action_id": (
                    "INT-FU-002"
                ),

                "domain": (
                    "interconnection"
                ),

                "question": (
                    "Does TATONGA7 remain the "
                    "screening-preferred POI when the "
                    "same 250-MW candidate is evaluated "
                    "under another relevant SPP HCT "
                    "model case?"
                ),

                "preferred_capability": (
                    "spp.compare_model_cases"
                ),

                "capability": (
                    "spp.compare_model_cases"
                ),

                "priority": (
                    "HIGH"
                ),

                "reason": (
                    "Only one HCT model case has been "
                    "evaluated, so the current POI "
                    "preference may be model-sensitive."
                ),

                "relationship": (
                    "CANDIDATE_SCREENING"
                ),

                "continues_blocking_investigation": (
                    True
                ),
            },

            {
                "action_id": (
                    "INT-FU-003"
                ),

                "domain": (
                    "interconnection"
                ),

                "question": (
                    "Should another plausible 345-kV "
                    "POI be screened before relying "
                    "more heavily on the Tatonga versus "
                    "Woodward comparison?"
                ),

                "preferred_capability": (
                    "spp.evaluate_additional_poi"
                ),

                "capability": (
                    "spp.evaluate_additional_poi"
                ),

                "priority": (
                    "HIGH"
                ),

                "reason": (
                    "Only two candidate POIs have been "
                    "tested, so POI-selection uncertainty "
                    "remains material."
                ),

                "relationship": (
                    "CANDIDATE_SCREENING"
                ),

                "continues_blocking_investigation": (
                    True
                ),
            },

            {
                "action_id": (
                    "INT-FU-004"
                ),

                "domain": (
                    "interconnection"
                ),

                "question": (
                    "What gen-tie and physical "
                    "transmission-access context must "
                    "be resolved before Tatonga can "
                    "be treated as a practical "
                    "candidate POI?"
                ),

                "preferred_capability": (
                    "transmission.assess_gen_tie_context"
                ),

                "capability": (
                    "transmission.assess_gen_tie_context"
                ),

                "priority": (
                    "HIGH"
                ),

                "reason": (
                    "HCT electrical screening alone "
                    "does not establish whether the "
                    "candidate site can practically "
                    "reach the preferred POI."
                ),

                "relationship": (
                    "CANDIDATE_SCREENING"
                ),

                "continues_blocking_investigation": (
                    True
                ),
            },
        ]


        # Compatibility value. The governed planner will
        # replace this with its selected action.
        follow_up = candidate_actions[0]


        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                follow_up
            ),

            "candidate_actions": (
                candidate_actions
            ),

            "route_reason": (
                "Precedent evidence was consumed, "
                "but G2 remains unresolved and "
                "multiple governed follow-up "
                "investigations are available."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G2",
                        status=(
                            "FOLLOW_UP_REQUIRED"
                        ),
                        recommended_action=(
                            follow_up[
                                "action_id"
                            ]
                        ),
                    )
                ]
            ),
        }


    # ========================================================
    # 3. SPP HCT cross-model comparison
    # ========================================================

    if capability == "spp.compare_model_cases":

        finding = result.get(
            "finding",
            {},
        )

        sensitivity_status = finding.get(
            "sensitivity_status"
        )

        screening_preferred_poi = finding.get(
            "screening_preferred_poi"
        )

        tested_model_count = finding.get(
            "tested_model_count",
            0,
        )

        tested_poi_count = finding.get(
            "tested_poi_count",
            0,
        )


        robust_across_tested_cases = (
            sensitivity_status
            ==
            "ROBUST_ACROSS_TESTED_CASES"
        )


        checks = {
            "model_case_comparison_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "multiple_hct_models_tested": (
                tested_model_count
                >= 2
            ),

            "multiple_pois_tested": (
                tested_poi_count
                >= 2
            ),

            "poi_preference_robust_across_tested_cases": (
                robust_across_tested_cases
            ),

            "candidate_specific_gi_study": (
                False
            ),

            "candidate_upgrade_cost_established": (
                False
            ),

            "interconnection_feasibility_established": (
                False
            ),

            "additional_poi_coverage_complete": (
                False
            ),

            "gen_tie_context_established": (
                False
            ),
        }


        sufficiency = {
            "domain": (
                "interconnection"
            ),

            "gate_id": (
                "G2"
            ),

            "status": (
                "FOLLOW_UP_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": {
                "sensitivity_status": (
                    sensitivity_status
                ),

                "screening_preferred_poi": (
                    screening_preferred_poi
                ),

                "tested_model_count": (
                    tested_model_count
                ),

                "tested_poi_count": (
                    tested_poi_count
                ),
            },

            "resolved_uncertainty": [
                (
                    "The Tatonga-versus-Woodward "
                    "screening preference was tested "
                    "across more than one supplied "
                    "SPP HCT model case."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "Only the explicitly supplied "
                    "candidate POIs have been screened."
                ),

                (
                    "Candidate-to-POI gen-tie "
                    "practicality remains unresolved."
                ),

                (
                    "Candidate-specific generator "
                    "interconnection feasibility has "
                    "not been established."
                ),

                (
                    "Candidate-specific upgrade cost "
                    "has not been established."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "The cross-model HCT comparison "
                f"returned {sensitivity_status!r}. "
                "This improves confidence in the "
                "screening comparison among the "
                "tested POIs and model cases, but "
                "does not establish candidate "
                "interconnection feasibility, final "
                "POI selection, gen-tie practicality, "
                "or candidate-specific upgrade cost."
            ),
        }


        # ----------------------------------------------------
        # Build remaining actions from actual execution
        # history rather than assuming a fixed sequence.
        # ----------------------------------------------------

        completed_task_ids = {
            item.get(
                "task_id"
            )
            for item in state.get(
                "investigation_history",
                []
            )
            if item.get(
                "task_id"
            )
        }

        current_task_id = result.get(
            "task_id"
        )

        if current_task_id:
            completed_task_ids.add(
                current_task_id
            )


        candidate_actions = []


        if (
            "INT-FU-003"
            not in completed_task_ids
        ):

            candidate_actions.append(
                {
                    "action_id": (
                        "INT-FU-003"
                    ),

                    "domain": (
                        "interconnection"
                    ),

                    "question": (
                        "Should another plausible 345-kV "
                        "POI be screened before relying "
                        "more heavily on the Tatonga versus "
                        "Woodward comparison?"
                    ),

                    "preferred_capability": (
                        "spp.evaluate_additional_poi"
                    ),

                    "capability": (
                        "spp.evaluate_additional_poi"
                    ),

                    "priority": (
                        "HIGH"
                    ),

                    "reason": (
                        "Only two candidate POIs have "
                        "been screened, so broader POI "
                        "coverage remains unresolved."
                    ),

                    "relationship": (
                        "CANDIDATE_SCREENING"
                    ),

                    "continues_blocking_investigation": (
                        True
                    ),
                }
            )


        if (
            "INT-FU-004"
            not in completed_task_ids
        ):

            candidate_actions.append(
                {
                    "action_id": (
                        "INT-FU-004"
                    ),

                    "domain": (
                        "interconnection"
                    ),

                    "question": (
                        "What gen-tie and physical "
                        "transmission-access context must "
                        "be resolved before Tatonga can "
                        "be treated as a practical "
                        "candidate POI?"
                    ),

                    "preferred_capability": (
                        "transmission.assess_gen_tie_context"
                    ),

                    "capability": (
                        "transmission.assess_gen_tie_context"
                    ),

                    "priority": (
                        "HIGH"
                    ),

                    "reason": (
                        "HCT model sensitivity has been "
                        "screened, but physical candidate-"
                        "to-transmission access context "
                        "must also be investigated."
                    ),

                    "relationship": (
                        "CANDIDATE_SCREENING"
                    ),

                    "continues_blocking_investigation": (
                        True
                    ),
                }
            )


        follow_up = (
            candidate_actions[0]
            if candidate_actions
            else None
        )


        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                follow_up
            ),

            "candidate_actions": (
                candidate_actions
            ),

            "route_reason": (
                "Cross-model HCT evidence was "
                "consumed. G2 remains unresolved; "
                "remaining governed investigations "
                "were derived from execution history."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G2",
                        status=(
                            "FOLLOW_UP_REQUIRED"
                        ),
                        finding_status=(
                            sensitivity_status
                        ),
                        tested_model_count=(
                            tested_model_count
                        ),
                        tested_poi_count=(
                            tested_poi_count
                        ),
                        candidate_action_ids=[
                            action["action_id"]
                            for action in candidate_actions
                        ],
                    )
                ]
            ),
        }


    # ========================================================
    # 4. Public gen-tie / transmission-access context
    # ========================================================

    if (
        capability
        ==
        "transmission.assess_gen_tie_context"
    ):

        finding = result.get(
            "finding",
            {},
        )

        public_context = finding.get(
            "public_line_context_status"
        )

        target_context = finding.get(
            "target_name_context_status"
        )

        nearest_target_line = finding.get(
            "nearest_target_named_line_miles"
        )


        checks = {
            "public_high_voltage_context_available": (
                public_context
                == "AVAILABLE"
            ),

            "tatonga_named_line_context_found": (
                target_context
                == "FOUND"
            ),

            "nearby_target_named_line_observed": (
                nearest_target_line
                is not None
            ),

            "exact_target_bus_geometry_established": (
                finding.get(
                    "exact_target_bus_geometry_established",
                    False,
                )
            ),

            "constructible_gen_tie_route_established": (
                finding.get(
                    "constructible_gen_tie_route_established",
                    False,
                )
            ),

            "row_availability_established": (
                finding.get(
                    "row_availability_established",
                    False,
                )
            ),

            "gen_tie_cost_established": (
                finding.get(
                    "gen_tie_cost_established",
                    False,
                )
            ),

            "interconnection_feasibility_established": (
                finding.get(
                    "interconnection_feasibility_established",
                    False,
                )
            ),
        }


        completed_before_assessment = {
            item.get("task_id")
            for item in state.get(
                "investigation_history",
                []
            )
            if item.get("task_id")
        }

        model_case_sensitivity_resolved = (
            "INT-FU-002"
            in completed_before_assessment
        )


        sufficiency = {
            "domain": (
                "interconnection"
            ),

            "gate_id": (
                "G2"
            ),

            "status": (
                "FOLLOW_UP_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "resolved_uncertainty": [
                (
                    "Public evidence establishes nearby "
                    "high-voltage transmission context."
                ),

                (
                    "Public line records contain Tatonga "
                    "endpoint-name context near the "
                    "candidate polygon."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "The exact SPP TATONGA7 bus geometry "
                    "has not been established."
                ),

                (
                    "A constructible candidate-to-POI "
                    "gen-tie route has not been established."
                ),

                (
                    "ROW availability has not been "
                    "established."
                ),

                (
                    "Gen-tie cost has not been established."
                ),

                (
                    "Candidate-specific interconnection "
                    "feasibility has not been established."
                ),

                (
                    "Only two candidate POIs have been "
                    "screened so far."
                ),
            ],

            "finding": {
                "public_line_context_status": (
                    public_context
                ),

                "target_name_context_status": (
                    target_context
                ),

                "nearest_target_named_line_miles": (
                    nearest_target_line
                ),

                "target_voltage_line_count": (
                    finding.get(
                        "target_voltage_line_count"
                    )
                ),

                "target_named_line_count": (
                    finding.get(
                        "target_named_line_count"
                    )
                ),
            },

            "checks": (
                checks
            ),

            "reason": (
                "Public transmission geometry provides "
                "screening-positive physical context for "
                "Tatonga, but it does not establish exact "
                "SPP bus geometry, a constructible gen-tie "
                "route, ROW, cost, or interconnection "
                "feasibility."
            ),
        }


        # ----------------------------------------------------
        # Build remaining actions from actual execution
        # history rather than assuming INT-FU-002 has
        # already executed.
        # ----------------------------------------------------

        completed_task_ids = {
            item.get(
                "task_id"
            )
            for item in state.get(
                "investigation_history",
                []
            )
            if item.get(
                "task_id"
            )
        }

        current_task_id = result.get(
            "task_id"
        )

        if current_task_id:
            completed_task_ids.add(
                current_task_id
            )


        candidate_actions = []


        if (
            "INT-FU-002"
            not in completed_task_ids
        ):

            candidate_actions.append(
                {
                    "action_id": (
                        "INT-FU-002"
                    ),

                    "domain": (
                        "interconnection"
                    ),

                    "question": (
                        "Does TATONGA7 remain the "
                        "screening-preferred POI when the "
                        "same 250-MW candidate is evaluated "
                        "under another relevant SPP HCT "
                        "model case?"
                    ),

                    "preferred_capability": (
                        "spp.compare_model_cases"
                    ),

                    "capability": (
                        "spp.compare_model_cases"
                    ),

                    "priority": (
                        "HIGH"
                    ),

                    "reason": (
                        "Gen-tie context has been screened, "
                        "but the Tatonga-versus-Woodward "
                        "HCT preference has not yet been "
                        "tested across multiple model cases."
                    ),

                    "relationship": (
                        "CANDIDATE_SCREENING"
                    ),

                    "continues_blocking_investigation": (
                        True
                    ),
                }
            )


        if (
            "INT-FU-003"
            not in completed_task_ids
        ):

            candidate_actions.append(
                {
                    "action_id": (
                        "INT-FU-003"
                    ),

                    "domain": (
                        "interconnection"
                    ),

                    "question": (
                        "Should another plausible 345-kV "
                        "POI be screened before relying "
                        "more heavily on the Tatonga versus "
                        "Woodward comparison?"
                    ),

                    "preferred_capability": (
                        "spp.evaluate_additional_poi"
                    ),

                    "capability": (
                        "spp.evaluate_additional_poi"
                    ),

                    "priority": (
                        "HIGH"
                    ),

                    "reason": (
                        "Only two candidate POIs have "
                        "been screened, so broader POI "
                        "coverage remains unresolved."
                    ),

                    "relationship": (
                        "CANDIDATE_SCREENING"
                    ),

                    "continues_blocking_investigation": (
                        True
                    ),
                }
            )


        follow_up = (
            candidate_actions[0]
            if candidate_actions
            else None
        )


        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                follow_up
            ),

            "candidate_actions": (
                candidate_actions
            ),

            "route_reason": (
                "Public gen-tie context was consumed. "
                "G2 remains unresolved; remaining "
                "governed investigations were derived "
                "from execution history."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G2",
                        status=(
                            "FOLLOW_UP_REQUIRED"
                        ),
                        public_line_context=(
                            public_context
                        ),
                        target_name_context=(
                            target_context
                        ),
                        nearest_target_named_line_miles=(
                            nearest_target_line
                        ),
                        candidate_action_ids=[
                            action["action_id"]
                            for action in candidate_actions
                        ],
                    )
                ]
            ),
        }


    # ========================================================
    # 5. Expanded SPP HCT POI screening
    # ========================================================

    if (
        capability
        ==
        "spp.evaluate_additional_poi"
    ):

        finding = result.get(
            "finding",
            {},
        )


        expanded_set_status = finding.get(
            "expanded_set_status"
        )

        screening_preferred_poi = finding.get(
            "screening_preferred_poi"
        )

        tested_model_count = finding.get(
            "tested_model_count",
            0,
        )

        tested_poi_count = finding.get(
            "tested_poi_count",
            0,
        )

        additional_pois_tested = finding.get(
            "additional_pois_tested",
            [],
        )

        displaced_existing_preference = (
            finding.get(
                "additional_poi_displaced_existing_preference"
            )
        )


        cross_model_question_resolved = (
            tested_model_count >= 2
        )

        expanded_poi_question_resolved = (
            tested_poi_count >= 3
        )

        preference_robust = (
            expanded_set_status
            ==
            "PREFERENCE_ROBUST_ACROSS_TESTED_CASES"
        )


        completed_task_ids = {
            item.get(
                "task_id"
            )
            for item in state.get(
                "investigation_history",
                []
            )
            if item.get(
                "task_id"
            )
        }


        current_task_id = result.get(
            "task_id"
        )

        if current_task_id:

            completed_task_ids.add(
                current_task_id
            )


        gen_tie_context_assessed = (
            "INT-FU-004"
            in completed_task_ids
        )


        candidate_actions = []


        # INT-FU-003 itself may satisfy the business
        # uncertainty behind INT-FU-002 if the expanded
        # POI set was already evaluated across multiple
        # HCT model cases.
        if (
            not cross_model_question_resolved
            and
            "INT-FU-002"
            not in completed_task_ids
        ):

            candidate_actions.append(
                {
                    "action_id": (
                        "INT-FU-002"
                    ),

                    "domain": (
                        "interconnection"
                    ),

                    "question": (
                        "Does TATONGA7 remain the "
                        "screening-preferred POI when "
                        "evaluated under another relevant "
                        "SPP HCT model case?"
                    ),

                    "preferred_capability": (
                        "spp.compare_model_cases"
                    ),

                    "capability": (
                        "spp.compare_model_cases"
                    ),

                    "priority": (
                        "HIGH"
                    ),

                    "reason": (
                        "The expanded POI evidence did "
                        "not evaluate enough HCT model "
                        "cases to resolve model sensitivity."
                    ),

                    "relationship": (
                        "CANDIDATE_SCREENING"
                    ),

                    "continues_blocking_investigation": (
                        True
                    ),
                }
            )


        if not gen_tie_context_assessed:

            candidate_actions.append(
                {
                    "action_id": (
                        "INT-FU-004"
                    ),

                    "domain": (
                        "interconnection"
                    ),

                    "question": (
                        "What gen-tie and physical "
                        "transmission-access context must "
                        "be resolved before Tatonga can "
                        "be treated as a practical "
                        "candidate POI?"
                    ),

                    "preferred_capability": (
                        "transmission.assess_gen_tie_context"
                    ),

                    "capability": (
                        "transmission.assess_gen_tie_context"
                    ),

                    "priority": (
                        "HIGH"
                    ),

                    "reason": (
                        "Expanded HCT electrical screening "
                        "does not establish physical "
                        "candidate-to-transmission access."
                    ),

                    "relationship": (
                        "CANDIDATE_SCREENING"
                    ),

                    "continues_blocking_investigation": (
                        True
                    ),
                }
            )


        follow_up = (
            candidate_actions[0]
            if candidate_actions
            else None
        )


        assessment_status = (
            "FOLLOW_UP_REQUIRED"
            if candidate_actions
            else "HUMAN_DILIGENCE_REQUIRED"
        )


        resolved_uncertainty = [
            (
                "The candidate HCT screen was expanded "
                f"to {tested_poi_count} supplied POIs."
            ),
        ]


        if cross_model_question_resolved:

            resolved_uncertainty.append(
                (
                    "The expanded POI set was evaluated "
                    f"across {tested_model_count} supplied "
                    "SPP HCT model cases, so the business "
                    "uncertainty behind INT-FU-002 is "
                    "already covered by this evidence."
                )
            )


        if preference_robust:

            resolved_uncertainty.append(
                (
                    f"{screening_preferred_poi} remained "
                    "screening-preferred across the "
                    "tested expanded POI/model-case set."
                )
            )


        sufficiency = {
            "domain": (
                "interconnection"
            ),

            "gate_id": (
                "G2"
            ),

            "status": (
                assessment_status
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": {
                "expanded_set_status": (
                    expanded_set_status
                ),

                "screening_preferred_poi": (
                    screening_preferred_poi
                ),

                "tested_model_count": (
                    tested_model_count
                ),

                "tested_poi_count": (
                    tested_poi_count
                ),

                "additional_pois_tested": (
                    additional_pois_tested
                ),

                "additional_poi_displaced_existing_preference": (
                    displaced_existing_preference
                ),
            },

            "resolved_uncertainty": (
                resolved_uncertainty
            ),

            "remaining_uncertainty": [
                (
                    "Candidate-specific generator "
                    "interconnection feasibility has "
                    "not been established."
                ),

                (
                    "Candidate-specific network-upgrade "
                    "cost has not been established."
                ),

                (
                    "The exact SPP TATONGA7 bus geometry "
                    "has not been established."
                ),

                (
                    "A constructible candidate-to-POI "
                    "gen-tie route has not been established."
                ),

                (
                    "ROW availability has not been "
                    "established."
                ),
            ],

            "checks": {
                "additional_poi_screening_executed": (
                    bool(
                        result.get(
                            "executed"
                        )
                    )
                ),

                "expanded_poi_set_tested": (
                    expanded_poi_question_resolved
                ),

                "multiple_hct_models_tested": (
                    cross_model_question_resolved
                ),

                "preference_robust_across_tested_cases": (
                    preference_robust
                ),

                "gen_tie_context_previously_assessed": (
                    gen_tie_context_assessed
                ),

                "candidate_specific_gi_study": (
                    False
                ),

                "candidate_upgrade_cost_established": (
                    False
                ),

                "interconnection_feasibility_established": (
                    False
                ),
            },

            "reason": (
                "Expanded HCT screening improves the "
                "POI-selection evidence and, because "
                "multiple supplied model cases were "
                "included, also resolves the narrower "
                "cross-model screening question. G2 "
                "remains unresolved because HCT "
                "screening does not establish final "
                "interconnection feasibility, upgrade "
                "cost, gen-tie constructability, or ROW."
            ),
        }


        route_reason = (
            (
                "Expanded POI evidence was consumed. "
                "Remaining automated G2 investigations "
                "were derived from unresolved evidence "
                "questions."
            )
            if candidate_actions
            else (
                "Expanded POI and cross-model HCT "
                "screening were consumed. No remaining "
                "implemented automated G2 screening "
                "action is required; authoritative "
                "human/project diligence is still "
                "required before G2 can be resolved."
            )
        )


        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                follow_up
            ),

            "candidate_actions": (
                candidate_actions
            ),

            "route_reason": (
                route_reason
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G2",
                        status=(
                            assessment_status
                        ),
                        finding_status=(
                            expanded_set_status
                        ),
                        tested_model_count=(
                            tested_model_count
                        ),
                        tested_poi_count=(
                            tested_poi_count
                        ),
                        cross_model_question_resolved=(
                            cross_model_question_resolved
                        ),
                        candidate_action_ids=[
                            action["action_id"]
                            for action in candidate_actions
                        ],
                    )
                ]
            ),
        }


    # ========================================================
    # 6. PAD-US land-status screening
    # ========================================================

    if capability == "land.resolve_status":

        finding = result.get(
            "finding",
            {},
        )

        unit_count = finding.get(
            "unit_count",
            0,
        )

        overlap_acres = finding.get(
            "padus_overlap_acres",
        )

        overlap_percent = finding.get(
            "padus_overlap_percent",
        )

        checks = {
            "padus_screening_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "tribal_interest_flagged": (
                bool(
                    finding.get(
                        "tribal_interest_flagged"
                    )
                )
            ),

            "state_managed_land_flagged": (
                bool(
                    finding.get(
                        "state_managed_land_flagged"
                    )
                )
            ),

            "conservation_area_flagged": (
                bool(
                    finding.get(
                        "conservation_area_flagged"
                    )
                )
            ),

            "authoritative_legal_status_established": (
                False
            ),

            "authoritative_tribal_trust_status_established": (
                False
            ),

            "authoritative_state_land_control_established": (
                False
            ),
        }

        overlap_acres_text = (
            f"{overlap_acres:,.1f}"
            if isinstance(
                overlap_acres,
                (int, float),
            )
            else "an unknown number of"
        )

        overlap_percent_text = (
            f"{overlap_percent:.2f}%"
            if isinstance(
                overlap_percent,
                (int, float),
            )
            else "an unknown percentage"
        )

        sufficiency = {
            "domain": (
                "land_status"
            ),

            "gate_id": (
                "G3"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": [
                (
                    "PAD-US mapped-unit screening identified "
                    f"{unit_count} intersecting land-management "
                    f"unit(s) covering {overlap_acres_text} acres "
                    f"({overlap_percent_text} of the candidate "
                    "area), with real manager, designation, and "
                    "GAP-status attributes for each unit."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "Authoritative tribal legal/trust status has "
                    "not been established (PAD-US 'Tribal "
                    "Statistical Area' is Census-derived "
                    "statistical geography, not a legal boundary)."
                ),

                (
                    "Authoritative Oklahoma Commissioners of Land "
                    "Office / State Land Board lease, sale, or "
                    "development-restriction status has not been "
                    "established."
                ),

                (
                    "Wildlife Management Area access/use "
                    "restrictions have not been established from "
                    "an authoritative source."
                ),

                (
                    "Actual land ownership, lease, and easement "
                    "status remain unresolved."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "PAD-US screening confirms real, mapped "
                "land-management-unit overlap (a tribal "
                "statistical area, State Land Board lands, and a "
                "state wildlife management area), but this "
                "dataset alone cannot resolve legal land status, "
                "tribal trust status, or development-control "
                "rights. No further automated screening "
                "capability is currently implemented for this "
                "domain, so authoritative human/project diligence "
                "is required before G3 land-status uncertainty "
                "can be resolved."
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "PAD-US land-status screening was consumed. G3 "
                "remains unresolved; no further automated "
                "land-status screening capability is implemented, "
                "so authoritative human diligence is required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G3",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        unit_count=unit_count,
                    )
                ]
            ),
        }


    # ========================================================
    # 7. USFWS critical-habitat species screening
    # ========================================================

    if capability == "environment.screen_species":

        finding = result.get(
            "finding",
            {},
        )

        species_count = finding.get(
            "species_count",
            0,
        )

        overlap_acres = finding.get(
            "critical_habitat_overlap_acres",
        )

        overlap_percent = finding.get(
            "critical_habitat_overlap_percent",
        )

        checks = {
            "critical_habitat_screening_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "endangered_species_flagged": (
                bool(
                    finding.get(
                        "endangered_species_flagged"
                    )
                )
            ),

            "threatened_species_flagged": (
                bool(
                    finding.get(
                        "threatened_species_flagged"
                    )
                )
            ),

            "final_critical_habitat_flagged": (
                bool(
                    finding.get(
                        "final_critical_habitat_flagged"
                    )
                )
            ),

            "official_ipac_species_list_obtained": (
                False
            ),

            "migratory_bird_screening_completed": (
                False
            ),

            "section_7_consultation_completed": (
                False
            ),
        }

        overlap_acres_text = (
            f"{overlap_acres:,.2f}"
            if isinstance(
                overlap_acres,
                (int, float),
            )
            else "an unknown number of"
        )

        overlap_percent_text = (
            f"{overlap_percent:.4f}%"
            if isinstance(
                overlap_percent,
                (int, float),
            )
            else "an unknown percentage"
        )

        species_names = ", ".join(
            f"{item.get('common_name')} "
            f"({item.get('scientific_name')}, "
            f"{item.get('listing_status')})"
            for item in result.get(
                "species",
                [],
            )
        ) or "none"

        sufficiency = {
            "domain": (
                "species"
            ),

            "gate_id": (
                "G3"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": [
                (
                    f"USFWS Final/Proposed critical-habitat "
                    f"screening identified {species_count} "
                    f"species record(s) with designated critical "
                    f"habitat overlapping the candidate area "
                    f"({overlap_acres_text} acres, "
                    f"{overlap_percent_text} of the candidate): "
                    f"{species_names}."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "A full USFWS IPaC official species list has "
                    "not been obtained, so ESA-listed species "
                    "without designated critical habitat have not "
                    "been screened."
                ),

                (
                    "Migratory-bird and bald/golden eagle "
                    "screening has not been performed."
                ),

                (
                    "ESA Section 7 consultation has not been "
                    "initiated or completed."
                ),

                (
                    "The practical siting/layout impact of the "
                    "identified critical habitat overlap has not "
                    "been assessed."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "USFWS Critical Habitat screening confirms real, "
                "Federal-Register-published critical habitat "
                "overlap for at least one federally listed "
                "species, but critical habitat is only one part "
                "of a full ESA screening. No further automated "
                "screening capability is currently implemented "
                "for this domain, so authoritative human/project "
                "diligence (a full IPaC official species list and "
                "Section 7 consultation) is required before G3 "
                "species uncertainty can be resolved."
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "USFWS critical-habitat species screening was "
                "consumed. G3 remains unresolved; no further "
                "automated species-screening capability is "
                "implemented, so authoritative human diligence "
                "is required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G3",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        species_count=species_count,
                    )
                ]
            ),
        }


    # ========================================================
    # 8. USGS 3DEP terrain (elevation/slope) screening
    # ========================================================

    if capability == "gis.analyze_terrain":

        finding = result.get(
            "finding",
            {},
        )

        relief_m = finding.get(
            "relief_m",
        )

        slope_mean = finding.get(
            "slope_mean_percent",
        )

        slope_p90 = finding.get(
            "slope_p90_percent",
        )

        acres_over_15pct = finding.get(
            "acres_over_15pct_slope",
        )

        percent_over_15pct = finding.get(
            "percent_of_area_over_15pct_slope",
        )

        checks = {
            "terrain_screening_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "elevation_relief_established": (
                relief_m is not None
            ),

            "slope_distribution_established": (
                slope_mean is not None
            ),

            "wind_development_slope_threshold_established": (
                False
            ),

            "constructability_exclusion_established": (
                False
            ),

            "turbine_micrositing_established": (
                False
            ),
        }

        relief_text = (
            f"{relief_m:.1f}"
            if isinstance(
                relief_m,
                (int, float),
            )
            else "an unknown"
        )

        slope_mean_text = (
            f"{slope_mean:.2f}%"
            if isinstance(
                slope_mean,
                (int, float),
            )
            else "an unknown"
        )

        slope_p90_text = (
            f"{slope_p90:.2f}%"
            if isinstance(
                slope_p90,
                (int, float),
            )
            else "an unknown"
        )

        acres_over_15pct_text = (
            f"{acres_over_15pct:,.1f}"
            if isinstance(
                acres_over_15pct,
                (int, float),
            )
            else "an unknown number of"
        )

        percent_over_15pct_text = (
            f"{percent_over_15pct:.1f}%"
            if isinstance(
                percent_over_15pct,
                (int, float),
            )
            else "an unknown percentage"
        )

        sufficiency = {
            "domain": (
                "terrain"
            ),

            "gate_id": (
                "G1"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": [
                (
                    f"USGS 3DEP 10 m screening-grade elevation "
                    f"and slope statistics were computed across "
                    f"the full candidate polygon: {relief_text} m "
                    f"of relief, {slope_mean_text} mean slope, "
                    f"{slope_p90_text} 90th-percentile slope, and "
                    f"{acres_over_15pct_text} acres "
                    f"({percent_over_15pct_text} of sampled area) "
                    "exceeding 15% slope."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "No wind-development slope-suitability "
                    "threshold has been applied or established; "
                    "constructability and turbine micro-siting "
                    "thresholds are project- and vendor-specific."
                ),

                (
                    "Slope was computed on a 10 m resampled grid "
                    "and is screening-grade, not survey-grade."
                ),

                (
                    "Land cover, access roads, and geotechnical "
                    "conditions have not been assessed alongside "
                    "terrain."
                ),

                (
                    "Developable/usable acreage after slope, "
                    "setback, and layout constraints has not been "
                    "established."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "USGS 3DEP screening establishes real, "
                "authoritative elevation and slope statistics "
                "for the full candidate polygon, but no "
                "constructability threshold, exclusion, or "
                "turbine micro-siting analysis has been applied. "
                "No further automated screening capability is "
                "currently implemented for this domain, so "
                "project-specific engineering/siting diligence is "
                "required before G1 terrain uncertainty can be "
                "resolved."
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "USGS 3DEP terrain screening was consumed. G1 "
                "remains unresolved; no further automated terrain "
                "screening capability is implemented, so "
                "project-specific siting diligence is required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G1",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        relief_m=relief_m,
                        slope_mean_percent=slope_mean,
                    )
                ]
            ),
        }


    # ========================================================
    # 9. NLCD land-cover screening
    # ========================================================

    if capability == "gis.analyze_land_cover":

        finding = result.get(
            "finding",
            {},
        )

        dominant_class_name = finding.get(
            "dominant_class_name",
        )

        dominant_class_percent = finding.get(
            "dominant_class_percent",
        )

        developed_acres = finding.get(
            "developed_acres",
        )

        developed_percent = finding.get(
            "developed_percent_of_candidate",
        )

        checks = {
            "land_cover_screening_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "class_composition_established": (
                bool(
                    finding.get(
                        "class_count"
                    )
                )
            ),

            "developable_acreage_established": (
                False
            ),

            "layout_compatibility_established": (
                False
            ),

            "access_road_screening_established": (
                False
            ),
        }

        dominant_class_text = (
            dominant_class_name
            or "an unknown class"
        )

        dominant_percent_text = (
            f"{dominant_class_percent:.1f}%"
            if isinstance(
                dominant_class_percent,
                (int, float),
            )
            else "an unknown percentage"
        )

        developed_acres_text = (
            f"{developed_acres:,.1f}"
            if isinstance(
                developed_acres,
                (int, float),
            )
            else "an unknown number of"
        )

        developed_percent_text = (
            f"{developed_percent:.2f}%"
            if isinstance(
                developed_percent,
                (int, float),
            )
            else "an unknown percentage"
        )

        sufficiency = {
            "domain": (
                "land_cover"
            ),

            "gate_id": (
                "G1"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": [
                (
                    f"NLCD 30 m land-cover classification was "
                    f"computed across the candidate polygon. The "
                    f"dominant class is {dominant_class_text} "
                    f"({dominant_percent_text} of sampled area), "
                    f"with {developed_acres_text} acres "
                    f"({developed_percent_text} of the candidate) "
                    "already developed."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "Developable/usable acreage after layout, "
                    "setback, and exclusion constraints has not "
                    "been established."
                ),

                (
                    "Land-cover compatibility with turbine "
                    "siting, access roads, and construction "
                    "staging has not been assessed."
                ),

                (
                    "NLCD land-cover classification does not "
                    "establish jurisdictional wetland status; "
                    "the governed NWI wetlands evidence remains "
                    "the more relevant wetlands source."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "NLCD screening establishes real, authoritative "
                "30 m land-cover class composition for the "
                "candidate polygon, but does not establish "
                "developable acreage, layout compatibility, or "
                "access-road feasibility. No further automated "
                "screening capability is currently implemented "
                "for this domain, so project-specific siting "
                "diligence is required before G1 land-cover "
                "uncertainty can be resolved."
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "NLCD land-cover screening was consumed. G1 "
                "remains unresolved; no further automated "
                "land-cover screening capability is implemented, "
                "so project-specific siting diligence is "
                "required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G1",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        dominant_class=dominant_class_name,
                    )
                ]
            ),
        }


    # ========================================================
    # 10. FEMA NFHL flood-coverage screening
    # ========================================================

    if capability == "gis.resolve_flood_evidence":

        finding = result.get(
            "finding",
            {},
        )

        coverage_status = finding.get(
            "nfhl_coverage_status",
        )

        mapped_percent = finding.get(
            "nfhl_mapped_coverage_percent",
        )

        unmapped_percent = finding.get(
            "nfhl_unmapped_or_unknown_percent",
        )

        sfha_percent = finding.get(
            "special_flood_hazard_area_percent",
        )

        checks = {
            "fema_nfhl_coverage_checked": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "digital_nfhl_coverage_present": (
                coverage_status
                != "NO_DIGITAL_COVERAGE"
            ),

            "alternate_authoritative_flood_source_obtained": (
                False
            ),

            "site_specific_hydrologic_review_completed": (
                False
            ),
        }

        if (
            coverage_status
            == "NO_DIGITAL_COVERAGE"
        ):

            resolved_uncertainty = [
                (
                    "FEMA NFHL was queried directly against the "
                    "candidate polygon and confirmed to have no "
                    "digital Flood Hazard Zone or FIRM panel "
                    "coverage for this area (0% mapped)."
                ),
            ]

            remaining_uncertainty = [
                (
                    "Flood-hazard status for the candidate area "
                    "remains genuinely UNKNOWN because no digital "
                    "FEMA mapping exists here; this is not "
                    "evidence of no flood hazard."
                ),

                (
                    "No alternate authoritative flood-risk source "
                    "(e.g. county floodplain study, USGS "
                    "StreamStats, or a site-specific hydrologic "
                    "study) has been consulted."
                ),
            ]

            reason = (
                "FEMA NFHL coverage was directly checked and "
                "confirmed absent for this candidate area (0% "
                "mapped, 100% unmapped/unknown). No further "
                "automated flood-screening capability is "
                "currently implemented, so an alternate "
                "authoritative flood-risk source or site-specific "
                "hydrologic review is required before G3 "
                "flood-hazard uncertainty can be resolved. "
                "Absence of mapping must not be treated as "
                "absence of flood hazard."
            )

        else:

            unmapped_percent_text = (
                f"{unmapped_percent:.2f}%"
                if isinstance(
                    unmapped_percent,
                    (int, float),
                )
                else "an unknown percentage"
            )

            sfha_percent_text = (
                f"{sfha_percent:.2f}%"
                if isinstance(
                    sfha_percent,
                    (int, float),
                )
                else "an unknown percentage"
            )

            resolved_uncertainty = [
                (
                    f"FEMA NFHL mapped coverage was retrieved for "
                    f"the candidate area; "
                    f"{sfha_percent_text} of the candidate falls "
                    f"within a mapped Special Flood Hazard Area, "
                    f"with {unmapped_percent_text} of the area "
                    "still unmapped/unknown."
                ),
            ]

            remaining_uncertainty = [
                (
                    "Any unmapped portion of the candidate "
                    "remains genuinely UNKNOWN, not confirmed "
                    "free of flood hazard."
                ),

                (
                    "Mapped Special Flood Hazard Area overlap is "
                    "a screening fact, not an automatic project "
                    "exclusion, and has not been translated into "
                    "layout or siting constraints."
                ),
            ]

            reason = (
                "FEMA NFHL mapped coverage was retrieved and "
                "partially/fully covers the candidate area, but "
                "any remaining unmapped area stays UNKNOWN and "
                "mapped SFHA overlap has not been assessed for "
                "siting impact. Authoritative human/project "
                "diligence is required before G3 flood-hazard "
                "uncertainty can be resolved."
            )


        sufficiency = {
            "domain": (
                "flood"
            ),

            "gate_id": (
                "G3"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": (
                resolved_uncertainty
            ),

            "remaining_uncertainty": (
                remaining_uncertainty
            ),

            "checks": (
                checks
            ),

            "reason": (
                reason
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "FEMA NFHL flood-coverage screening was "
                "consumed. G3 remains unresolved; no further "
                "automated flood-screening capability is "
                "implemented, so authoritative human diligence "
                "is required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G3",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        nfhl_coverage_status=(
                            coverage_status
                        ),
                    )
                ]
            ),
        }


    # ========================================================
    # 11. Screening-level regulatory/permit matrix
    # ========================================================

    if capability == "regulatory.build_permit_matrix":

        finding = result.get(
            "finding",
            {},
        )

        established_count = finding.get(
            "established_requirement_count",
            0,
        )

        failed_legislation_count = finding.get(
            "failed_legislation_count",
            0,
        )

        conditional_count = finding.get(
            "conditional_trigger_count",
            0,
        )

        county = finding.get(
            "jurisdiction_county",
        )

        state_name = finding.get(
            "jurisdiction_state",
        )

        checks = {
            "permit_matrix_screening_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "jurisdiction_identified": (
                bool(county)
                and bool(state_name)
            ),

            "complete_permit_matrix_established": (
                False
            ),

            "specific_fees_or_timelines_established": (
                False
            ),

            "legal_review_completed": (
                False
            ),
        }

        sufficiency = {
            "domain": (
                "regulatory"
            ),

            "gate_id": (
                "G4"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "LOW"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": [
                (
                    f"Project jurisdiction was confirmed as "
                    f"{county}, {state_name} via authoritative "
                    "Census boundaries."
                ),

                (
                    f"{established_count} well-established, "
                    "citable federal/state requirement "
                    "categories (FAA Part 77 notice, Oklahoma "
                    "Wind Energy Development Act registration, "
                    "SPP/FERC interconnection) were identified "
                    f"as applicable; {failed_legislation_count} "
                    "tracked wind-setback bill(s) (SB2, HB2751) "
                    "were verified FAILED in the 2025-2026 "
                    "session and do not currently change any "
                    f"setback requirement; {conditional_count} "
                    "additional federal consultation trigger(s) "
                    "were derived directly from this project's "
                    "own prior species and land-status screening "
                    "evidence."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "This is a screening-level list of "
                    "requirement categories, not a complete "
                    "permit matrix; county/local ordinance text "
                    "has not been retrieved."
                ),

                (
                    "No permit fees, approval timelines, or "
                    "approval likelihood have been established."
                ),

                (
                    "SB2 and HB2751 both failed in the "
                    "2025-2026 session; that status was "
                    "manually verified (not API-fetched) and "
                    "must be re-checked once a new legislative "
                    "session convenes."
                ),

                (
                    "This screening has not been reviewed by "
                    "permitting counsel and is not legal advice."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "Real jurisdiction identification and a "
                "citation-backed list of well-established "
                "federal/state requirement categories were "
                "assembled, including conditional federal "
                "consultation triggers derived from this "
                "project's own species and land-status "
                "findings. This does not constitute a complete "
                "permit matrix or legal advice. No further "
                "automated screening capability is currently "
                "implemented for this domain, so authoritative "
                "legal/permitting-consultant diligence is "
                "required before G4 regulatory uncertainty can "
                "be resolved."
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "Screening-level regulatory/permit-category "
                "matrix was consumed. G4 remains unresolved; "
                "authoritative legal/permitting-consultant "
                "diligence is required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G4",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        jurisdiction_county=county,
                    )
                ]
            ),
        }


    # ========================================================
    # 12. FAA aviation / military-compatibility screening
    # ========================================================

    if capability == "aviation.screen_candidate":

        finding = result.get(
            "finding",
            {},
        )

        nearest_name = finding.get(
            "nearest_public_use_airport_name",
        )

        nearest_distance_nm = finding.get(
            "nearest_public_use_airport_distance_nm",
        )

        setback_violated = finding.get(
            "statutory_setback_appears_violated",
        )

        sua_count = finding.get(
            "military_special_use_airspace_intersection_count",
            0,
        )

        checks = {
            "aviation_screening_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "nearest_public_use_airport_identified": (
                nearest_name is not None
            ),

            "statutory_airport_setback_appears_satisfied": (
                setback_violated is False
            ),

            "military_sua_intersection_flagged": (
                sua_count > 0
            ),

            "faa_part77_notice_filed": (
                False
            ),

            "faa_airspace_determination_obtained": (
                False
            ),

            "military_mission_compatibility_reviewed": (
                False
            ),
        }

        nearest_text = (
            f"{nearest_name} ({nearest_distance_nm:.2f} nm)"
            if nearest_name
            and isinstance(
                nearest_distance_nm,
                (int, float),
            )
            else "no public-use airport within the "
            "screening radius"
        )

        sufficiency = {
            "domain": (
                "aviation"
            ),

            "gate_id": (
                "G5"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": [
                (
                    f"FAA airport data confirms the nearest "
                    f"public-use airport is {nearest_text}, "
                    f"which does not appear to violate "
                    "Oklahoma's statutory 1.5 nm public-use-"
                    "airport setback."
                ),

                (
                    f"{sua_count} Military Special Use Airspace "
                    "polygon(s) intersect the candidate boundary."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "No FAA Form 7460-1 has been filed and no "
                    "FAA airspace determination has been "
                    "obtained; this screening does not "
                    "substitute for the OE/AAA process."
                ),

                (
                    "Military Training Route (low-level "
                    "corridor) screening was not performed."
                ),

                (
                    "DoD mission-compatibility, radar, and "
                    "weather-surveillance impacts have not been "
                    "reviewed."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "FAA-sourced airport-distance and Special Use "
                "Airspace screening establishes real, "
                "authoritative context, but does not perform or "
                "substitute for the FAA OE/AAA obstruction-"
                "evaluation process. No further automated "
                "screening capability is currently implemented "
                "for this domain, so filing FAA Form 7460-1 and "
                "obtaining an airspace determination is required "
                "before G5 aviation uncertainty can be resolved."
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "FAA aviation/military-compatibility screening "
                "was consumed. G5 remains unresolved; filing FAA "
                "Form 7460-1 and obtaining an airspace "
                "determination is required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G5",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        nearest_public_use_airport=(
                            nearest_name
                        ),
                    )
                ]
            ),
        }


    # ========================================================
    # 13. HRRR MET single-point wind-resource screening
    # ========================================================

    if capability == "wind.analyze_candidate_resource":

        finding = result.get(
            "finding",
            {},
        )

        mean_speed = finding.get(
            "mean_wind_speed_120m_mps",
        )

        shear = finding.get(
            "mean_wind_shear_alpha",
        )

        monthly_range = finding.get(
            "monthly_wind_speed_range_120m_mps",
        )

        checks = {
            "wind_resource_screening_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "single_point_mean_speed_established": (
                mean_speed is not None
            ),

            "candidate_wide_resource_established": (
                False
            ),

            "multi_year_resource_established": (
                False
            ),

            "met_tower_data_available": (
                False
            ),

            "aep_or_capacity_factor_established": (
                False
            ),
        }

        mean_speed_text = (
            f"{mean_speed:.2f}"
            if isinstance(
                mean_speed,
                (int, float),
            )
            else "an unknown"
        )

        shear_text = (
            f"{shear:.3f}"
            if isinstance(
                shear,
                (int, float),
            )
            else "an unknown"
        )

        sufficiency = {
            "domain": (
                "wind_resource"
            ),

            "gate_id": (
                "G1"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "LOW"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": [
                (
                    f"A full year (8,760 hourly observations) of "
                    f"modeled HRRR wind data at one candidate-"
                    f"area grid point shows a {mean_speed_text} "
                    "m/s mean wind speed at 120 m with a "
                    f"{shear_text} mean 100m-160m shear "
                    "exponent."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "This represents one modeled grid point, not "
                    "the full candidate polygon; spatial "
                    "variability across the site is unresolved."
                ),

                (
                    "Only one calendar year is included; multi-"
                    "year resource variability is unresolved."
                ),

                (
                    "No met-tower measured data, turbine power "
                    "curve, AEP, capacity factor, P50, or P90 "
                    "has been established."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "HRRR single-point screening establishes real, "
                "authoritative modeled wind-resource context, "
                "but it is a single grid point over a single "
                "year and does not establish candidate-wide "
                "resource, bankable AEP, or capacity factor. No "
                "further automated wind-resource screening "
                "capability is currently implemented, so multi-"
                "year, multi-point (or met-tower) resource "
                "assessment is required before G1 wind-resource "
                "uncertainty can be resolved."
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "HRRR single-point wind-resource screening was "
                "consumed. G1 remains unresolved; multi-year, "
                "multi-point (or met-tower) resource assessment "
                "is required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G1",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        mean_wind_speed_120m_mps=mean_speed,
                    )
                ]
            ),
        }


    # ========================================================
    # 14. NRHP cultural-resources screening
    # ========================================================

    if capability == "environment.screen_cultural_resources":

        finding = result.get(
            "finding",
            {},
        )

        direct_count = finding.get(
            "direct_intersection_count",
            0,
        )

        nearby_count = finding.get(
            "nearby_site_count_within_radius",
            0,
        )

        resource_names = finding.get(
            "direct_intersection_resource_names",
            [],
        )

        nhl_flagged = finding.get(
            "national_historic_landmark_flagged",
        )

        checks = {
            "nrhp_screening_executed": (
                bool(
                    result.get(
                        "executed"
                    )
                )
            ),

            "direct_intersection_flagged": (
                direct_count > 0
            ),

            "national_historic_landmark_flagged": (
                bool(nhl_flagged)
            ),

            "section_106_review_completed": (
                False
            ),

            "shpo_consultation_completed": (
                False
            ),

            "tribal_thpo_consultation_completed": (
                False
            ),
        }

        resource_names_text = (
            ", ".join(resource_names)
            if resource_names
            else "none"
        )

        sufficiency = {
            "domain": (
                "cultural"
            ),

            "gate_id": (
                "G3"
            ),

            "status": (
                "HUMAN_DILIGENCE_REQUIRED"
            ),

            "gate_status": (
                "UNRESOLVED"
            ),

            "decision_confidence": (
                "MEDIUM"
            ),

            "finding": (
                finding
            ),

            "resolved_uncertainty": [
                (
                    f"NRHP screening found {direct_count} "
                    "listed historic resource(s) directly "
                    f"intersecting the candidate polygon "
                    f"({resource_names_text}) and "
                    f"{nearby_count} additional listed site(s) "
                    "within the screening radius."
                ),
            ],

            "remaining_uncertainty": [
                (
                    "No Section 106 review, SHPO consultation, "
                    "or Tribal Historic Preservation Office "
                    "consultation has been completed."
                ),

                (
                    "No archaeological survey has been "
                    "performed; unlisted but potentially "
                    "eligible resources are not captured by "
                    "this screening."
                ),

                (
                    "The practical siting/layout impact of the "
                    "directly intersecting listed resource has "
                    "not been assessed."
                ),
            ],

            "checks": (
                checks
            ),

            "reason": (
                "NRHP screening confirms a real, listed historic "
                "resource directly within the candidate boundary "
                "and additional nearby listed sites, but this "
                "does not constitute Section 106 review or SHPO/"
                "THPO consultation. No further automated "
                "screening capability is currently implemented "
                "for this domain, so authoritative human/project "
                "diligence is required before G3 cultural-"
                "resources uncertainty can be resolved."
            ),
        }

        return {
            "evidence_sufficiency": (
                sufficiency
            ),

            "recommended_follow_up": (
                None
            ),

            "candidate_actions": [],

            "route_reason": (
                "NRHP cultural-resources screening was consumed. "
                "G3 remains unresolved; Section 106 / SHPO "
                "consultation is required."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "EVIDENCE_ASSESSED",
                        capability=capability,
                        gate_id="G3",
                        status=(
                            "HUMAN_DILIGENCE_REQUIRED"
                        ),
                        direct_intersection_count=direct_count,
                    )
                ]
            ),
        }


    # ========================================================
    # Generic fallback
    # ========================================================

    return {
        "evidence_sufficiency": {
            "status": (
                "NOT_ASSESSED"
            ),

            "reason": (
                "No deterministic evidence-assessment "
                f"policy exists yet for {capability!r}."
            ),
        },

        "recommended_follow_up": (
            None
        ),

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "EVIDENCE_ASSESSMENT_UNAVAILABLE",
                    capability=capability,
                )
            ]
        ),
    }
