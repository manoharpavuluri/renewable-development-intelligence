from __future__ import annotations

from langgraph.types import interrupt

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from renewable_intelligence.graph.state import (
    InvestigationState,
)
from renewable_intelligence.graph.result_assessment import (
    assess_investigation_result,
)
from renewable_intelligence.agents.foundry_planner import (
    plan_follow_up,
    plan_project_investigation,
)
from renewable_intelligence.tools.registry import (
    get_capability,
)


PRIORITY_ORDER = {
    "BLOCKING": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


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


# ============================================================
# Node: validate initial state
# ============================================================

def validate_state(
    state: InvestigationState,
) -> dict[str, Any]:

    errors: list[str] = []

    if not state.get(
        "screening"
    ):
        errors.append(
            "screening state missing"
        )

    if not state.get(
        "gate_assessment"
    ):
        errors.append(
            "gate assessment missing"
        )

    project_id = state.get(
        "project_id"
    )

    screening_id = (
        state.get(
            "screening",
            {},
        ).get(
            "project_id"
        )
    )

    gate_id = (
        state.get(
            "gate_assessment",
            {},
        ).get(
            "project_id"
        )
    )

    if (
        project_id
        and screening_id
        and project_id != screening_id
    ):
        errors.append(
            "project_id does not match "
            "screening project"
        )

    if (
        project_id
        and gate_id
        and project_id != gate_id
    ):
        errors.append(
            "project_id does not match "
            "gate assessment"
        )

    if errors:

        return {
            "investigation_status": (
                "INVALID_STATE"
            ),

            "errors": errors,

            "route_reason": (
                "Initial graph state "
                "validation failed."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "STATE_VALIDATION_FAILED",
                        errors=errors,
                    )
                ]
            ),
        }

    return {
        "investigation_status": (
            "STATE_VALID"
        ),

        # START represents a new graph invocation.
        # Reset only the invocation-level safety counter;
        # preserve lifetime iteration history.
        "run_iteration": 0,

        "errors": [],

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "STATE_VALIDATED",
                    project_id=project_id,
                )
            ]
        ),
    }


# ============================================================
# Routing after validation
# ============================================================

def route_after_validation(
    state: InvestigationState,
) -> str:

    if state.get(
        "investigation_status"
    ) == "INVALID_STATE":

        return "end"

    return "select"


# ============================================================
# Node: select next investigation
#
# Deterministic for v0:
#   BLOCKING > HIGH > MEDIUM > LOW
#
# Later the agent can reason among tasks of the same
# admissible priority, but it cannot invent tasks that
# are not grounded in the gate assessment.
# ============================================================

def select_next_investigation(
    state: InvestigationState,
) -> dict[str, Any]:

    queue = (
        state[
            "gate_assessment"
        ].get(
            "investigation_queue",
            []
        )
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


    domain_outcomes = (
        state.get(
            "project_domain_outcomes",
            {}
        )
        or {}
    )


    exhausted_domains = {
        domain
        for domain, outcome
        in domain_outcomes.items()
        if outcome.get(
            "screening_status"
        )
        in {
            "HUMAN_DILIGENCE_REQUIRED",
            "SCREENING_COMPLETE",
            "SUFFICIENT_FOR_SCREENING",
        }
    }


    pending_tasks = [
        task
        for task in queue
        if (
            task.get(
                "status",
                "PENDING",
            )
            == "PENDING"
        )
        and (
            task.get(
                "task_id"
            )
            not in completed_task_ids
        )
        and (
            task.get(
                "domain"
            )
            not in exhausted_domains
        )
    ]


    if not pending_tasks:

        return {
            "project_candidate_actions": [],

            "current_investigation": None,

            "selected_task_id": None,

            "selected_capability": None,

            "investigation_status": (
                "NO_PENDING_INVESTIGATIONS"
            ),

            "route_reason": (
                "No admissible pending project "
                "investigations remain after excluding "
                "completed tasks and exhausted domains."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    audit_event(
                        "NO_INVESTIGATION_SELECTED",
                        completed_task_ids=sorted(
                            completed_task_ids
                        ),
                        exhausted_domains=sorted(
                            exhausted_domains
                        ),
                    )
                ]
            ),
        }


    project_actions = []


    for task in pending_tasks:

        action = dict(
            task
        )

        action[
            "action_id"
        ] = task.get(
            "task_id"
        )

        action[
            "capability"
        ] = task.get(
            "preferred_capability"
        )

        action[
            "relationship"
        ] = (
            action.get(
                "relationship"
            )
            or "PROJECT_SCREENING"
        )

        project_actions.append(
            action
        )


    return {
        "project_candidate_actions": (
            project_actions
        ),

        "current_investigation": (
            None
        ),

        "selected_task_id": (
            None
        ),

        "selected_capability": (
            None
        ),

        "investigation_status": (
            "PROJECT_PLANNING_REQUIRED"
        ),

        "route_reason": (
            "Prepared governed project-level "
            f"candidate set containing "
            f"{len(project_actions)} investigations."
        ),

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "PROJECT_CANDIDATES_PREPARED",
                    candidate_action_ids=[
                        action[
                            "action_id"
                        ]
                        for action
                        in project_actions
                    ],
                    exhausted_domains=sorted(
                        exhausted_domains
                    ),
                )
            ]
        ),
    }


# ============================================================
# Routing after selection
# ============================================================

def route_after_selection(
    state: InvestigationState,
) -> str:

    status = state.get(
        "investigation_status"
    )


    if (
        status
        == "NO_PENDING_INVESTIGATIONS"
    ):

        return "end"


    if (
        status
        == "PROJECT_PLANNING_REQUIRED"
    ):

        return "plan"


    if (
        status
        == "INVESTIGATION_SELECTED"
    ):

        return "capability"


    return "end"


def route_after_project_planning(
    state: InvestigationState,
) -> str:

    if (
        state.get(
            "investigation_status"
        )
        == "INVESTIGATION_SELECTED"
    ):

        return "capability"


    return "end"


# ============================================================
# Node: check capability registry
# ============================================================

def check_capability(
    state: InvestigationState,
) -> dict[str, Any]:

    capability_name = (
        state.get(
            "selected_capability"
        )
    )

    capability = (
        get_capability(
            capability_name
        )
        if capability_name
        else None
    )

    available = bool(
        capability
        and capability.available
        and capability.handler
    )

    if not capability:

        reason = (
            f"Capability {capability_name!r} "
            f"is not registered."
        )

    elif not available:

        reason = (
            f"Capability {capability_name!r} "
            f"is registered but has no "
            f"available implementation."
        )

    else:

        reason = (
            f"Capability {capability_name!r} "
            f"is available."
        )

    return {
        "capability_available": (
            available
        ),

        "route_reason": reason,

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "CAPABILITY_CHECKED",
                    capability=(
                        capability_name
                    ),
                    available=available,
                )
            ]
        ),
    }


# ============================================================
# Route capability
# ============================================================

def route_capability(
    state: InvestigationState,
) -> str:

    if state.get(
        "capability_available"
    ):
        return "execute"

    return "blocked"


# ============================================================
# Node: blocked capability
# ============================================================

def capability_blocked(
    state: InvestigationState,
) -> dict[str, Any]:

    task_id = state.get(
        "selected_task_id"
    )

    capability = state.get(
        "selected_capability"
    )

    return {
        "investigation_status": (
            "BLOCKED_FOR_CAPABILITY"
        ),

        "investigation_result": {
            "task_id": task_id,
            "capability": capability,
            "executed": False,
            "reason": (
                "Required deterministic "
                "capability is not implemented."
            ),
        },

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "INVESTIGATION_BLOCKED",
                    task_id=task_id,
                    capability=capability,
                )
            ]
        ),
    }


# ============================================================
# Node: execute capability
#
# We implement the generic executor now even though our
# first selected capability is intentionally unavailable.
# ============================================================

def execute_capability(
    state: InvestigationState,
) -> dict[str, Any]:

    capability_name = (
        state[
            "selected_capability"
        ]
    )

    capability = get_capability(
        capability_name
    )

    if (
        capability is None
        or not capability.available
        or capability.handler is None
    ):
        raise RuntimeError(
            f"Capability became unavailable: "
            f"{capability_name}"
        )

    task = state[
        "current_investigation"
    ]

    result = capability.handler(
        state=state,
        task=task,
    )

    return {
        "investigation_status": (
            "INVESTIGATION_EXECUTED"
        ),

        "investigation_result": (
            result
        ),

        "investigation_history": (
            state.get(
                "investigation_history",
                []
            )
            + [
                {
                    "task_id": (
                        state.get(
                            "selected_task_id"
                        )
                    ),

                    "capability": (
                        capability_name
                    ),

                    "domain": (
                        task.get(
                            "domain"
                        )
                    ),

                    "relationship": (
                        task.get(
                            "relationship"
                        )
                    ),

                    "result": (
                        result
                    ),
                }
            ]
        ),

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "INVESTIGATION_EXECUTED",
                    task_id=state.get(
                        "selected_task_id"
                    ),
                    capability=(
                        capability_name
                    ),
                )
            ]
        ),
    }


# ============================================================
# Node: assess result and persist evidence assessment
#
# Business assessment remains inside result_assessment.py.
# This graph-layer wrapper owns persistence of assessment
# history so follow-up preparation can safely clear the
# current-iteration evidence_sufficiency value.
# ============================================================

def assess_and_record_evidence(
    state: InvestigationState,
) -> dict[str, Any]:

    update = assess_investigation_result(
        state
    )

    assessment = update.get(
        "evidence_sufficiency"
    )

    # No assessment was produced.
    # Preserve the assessor's normal behavior.
    if assessment is None:
        return update


    task_id = state.get(
        "selected_task_id"
    )

    capability = state.get(
        "selected_capability"
    )


    ledger_entry = {
        "task_id": (
            task_id
        ),

        "capability": (
            capability
        ),

        "domain": (
            assessment.get(
                "domain"
            )
        ),

        "gate_id": (
            assessment.get(
                "gate_id"
            )
        ),

        "status": (
            assessment.get(
                "status"
            )
        ),

        "gate_status": (
            assessment.get(
                "gate_status"
            )
        ),

        "decision_confidence": (
            assessment.get(
                "decision_confidence"
            )
        ),

        # Preserve the complete deterministic assessment.
        "assessment": (
            assessment
        ),
    }


    existing_ledger = list(
        state.get(
            "evidence_ledger",
            []
        )
    )


    # Make the ledger idempotent for eventual checkpoint /
    # resume. Re-assessing the same task + capability updates
    # its ledger entry instead of silently duplicating it.
    ledger = [
        item
        for item in existing_ledger
        if not (
            item.get(
                "task_id"
            )
            == task_id
            and
            item.get(
                "capability"
            )
            == capability
        )
    ]

    ledger.append(
        ledger_entry
    )


    update[
        "evidence_ledger"
    ] = ledger

    update[
        "latest_evidence_assessment"
    ] = assessment


    current_audit = (
        update.get(
            "audit_events"
        )
        or state.get(
            "audit_events",
            []
        )
    )

    update[
        "audit_events"
    ] = (
        current_audit
        + [
            audit_event(
                "EVIDENCE_LEDGER_RECORDED",
                task_id=task_id,
                capability=capability,
                gate_id=assessment.get(
                    "gate_id"
                ),
                gate_status=assessment.get(
                    "gate_status"
                ),
                decision_confidence=(
                    assessment.get(
                        "decision_confidence"
                    )
                ),
            )
        ]
    )


    return update


# ============================================================
# Node: record project-domain screening outcome
# ============================================================

def record_domain_outcome(
    state: InvestigationState,
) -> dict[str, Any]:

    assessment = (
        state.get(
            "evidence_sufficiency"
        )
        or {}
    )

    task = (
        state.get(
            "current_investigation"
        )
        or {}
    )


    domain = task.get(
        "domain"
    )

    if not domain:

        raise RuntimeError(
            "Cannot record domain outcome without "
            "a current investigation domain."
        )


    status = assessment.get(
        "status"
    )

    gate_id = assessment.get(
        "gate_id"
    )


    completed_task_ids = [
        item.get(
            "task_id"
        )
        for item in state.get(
            "investigation_history",
            []
        )
        if (
            item.get(
                "task_id"
            )
            and item.get(
                "domain"
            )
            == domain
        )
    ]


    existing = dict(
        state.get(
            "project_domain_outcomes",
            {}
        )
        or {}
    )


    existing[
        domain
    ] = {
        "domain": (
            domain
        ),

        "gate_id": (
            gate_id
        ),

        "screening_status": (
            status
        ),

        "gate_status": (
            assessment.get(
                "gate_status"
            )
        ),

        "decision_confidence": (
            assessment.get(
                "decision_confidence"
            )
        ),

        "resolved_uncertainty": (
            assessment.get(
                "resolved_uncertainty",
                []
            )
        ),

        "remaining_uncertainty": (
            assessment.get(
                "remaining_uncertainty",
                []
            )
        ),

        "latest_task_id": (
            state.get(
                "selected_task_id"
            )
        ),

        "latest_capability": (
            state.get(
                "selected_capability"
            )
        ),

        "completed_task_ids": (
            completed_task_ids
        ),
    }


    return {
        "project_domain_outcomes": (
            existing
        ),

        "investigation_status": (
            "DOMAIN_SCREENING_RECORDED"
        ),

        "current_investigation": (
            None
        ),

        "selected_task_id": (
            None
        ),

        "selected_capability": (
            None
        ),

        "capability_available": (
            None
        ),

        "investigation_result": (
            None
        ),

        "candidate_actions": [],

        "admissible_actions": [],

        "recommended_follow_up": (
            None
        ),

        "route_reason": (
            f"Recorded {domain} screening outcome "
            f"{status!r}; project screening may "
            "continue in another domain."
        ),

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "DOMAIN_SCREENING_RECORDED",
                    domain=domain,
                    gate_id=gate_id,
                    screening_status=status,
                )
            ]
        ),
    }


# ============================================================
# Route after evidence assessment
# ============================================================

def route_after_assessment(
    state: InvestigationState,
) -> str:

    sufficiency = (
        state.get(
            "evidence_sufficiency"
        )
        or {}
    )

    follow_up = state.get(
        "recommended_follow_up"
    )


    run_iteration = state.get(
        "run_iteration",
        0,
    )

    max_iterations = state.get(
        "max_iterations",
        25,
    )


    if (
        run_iteration
        >= max_iterations
    ):

        return "end"


    if (
        sufficiency.get(
            "status"
        )
        == "FOLLOW_UP_REQUIRED"
        and follow_up
    ):

        return "follow_up"


    # The domain has reached the boundary of the current
    # automated/public screening effort. Record that outcome
    # and return control to the project-level investigation
    # lifecycle rather than terminating the whole project.
    if sufficiency.get(
        "status"
    ) in {
        "HUMAN_DILIGENCE_REQUIRED",
        "SCREENING_COMPLETE",
        "SUFFICIENT_FOR_SCREENING",
    }:

        return "domain_complete"


    return "end"


# ============================================================
# Convert recommended follow-up to executable investigation
# ============================================================

def prepare_follow_up(
    state: InvestigationState,
) -> dict[str, Any]:

    follow_up = (
        state.get(
            "recommended_follow_up"
        )
        or {}
    )

    action_id = (
        follow_up.get(
            "action_id"
        )
    )

    capability = (
        follow_up.get(
            "preferred_capability"
        )
    )


    task = {
        "task_id": (
            action_id
        ),

        "action_id": (
            action_id
        ),

        "domain": (
            follow_up.get(
                "domain"
            )
        ),

        "question": (
            follow_up.get(
                "question"
            )
        ),

        "priority": (
            follow_up.get(
                "priority",
                "MEDIUM",
            )
        ),

        "preferred_capability": (
            capability
        ),

        "source_artifact": (
            follow_up.get(
                "source_artifact"
            )
        ),

        "relationship": (
            follow_up.get(
                "relationship"
            )
        ),

        "status": (
            "PENDING"
        ),
    }


    return {
        "current_investigation": (
            task
        ),

        "selected_task_id": (
            action_id
        ),

        "selected_capability": (
            capability
        ),

        "capability_available": (
            None
        ),

        "investigation_status": (
            "FOLLOW_UP_PREPARED"
        ),

        "investigation_result": (
            None
        ),

        "evidence_sufficiency": (
            None
        ),

        "recommended_follow_up": (
            None
        ),

        "iteration": (
            state.get(
                "iteration",
                0,
            )
            + 1
        ),

        "run_iteration": (
            state.get(
                "run_iteration",
                0,
            )
            + 1
        ),

        "route_reason": (
            f"Prepared follow-up "
            f"{action_id} using "
            f"{capability}."
        ),

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "FOLLOW_UP_PREPARED",
                    task_id=action_id,
                    capability=capability,
                )
            ]
        ),
    }


# ============================================================
# Node: pause for unavailable external capability / evidence
#
# Unlike the old terminal blocked node, this creates a durable
# HITL pause. When resumed, execution returns to
# check_capability so newly supplied evidence or a newly
# implemented capability can be discovered without replaying
# earlier investigations.
# ============================================================

def pause_for_capability(
    state: InvestigationState,
) -> dict[str, Any]:

    task_id = state.get(
        "selected_task_id"
    )

    capability = state.get(
        "selected_capability"
    )

    task = (
        state.get(
            "current_investigation"
        )
        or {}
    )


    # IMPORTANT:
    #
    # Do not perform side effects before interrupt().
    # LangGraph restarts this node from the beginning
    # when the thread is resumed.
    resume_payload = interrupt(
        {
            "type": (
                "CAPABILITY_OR_EVIDENCE_REQUIRED"
            ),

            "project_id": (
                state.get(
                    "project_id"
                )
            ),

            "task_id": (
                task_id
            ),

            "capability": (
                capability
            ),

            "domain": (
                task.get(
                    "domain"
                )
            ),

            "question": (
                task.get(
                    "question"
                )
            ),

            "reason": (
                "The required deterministic "
                "capability or governed evidence "
                "is not currently available."
            ),

            "resume_instruction": (
                "Supply or implement the required "
                "capability/evidence, then resume "
                "this same LangGraph thread."
            ),
        }
    )


    if not isinstance(
        resume_payload,
        dict,
    ):

        raise RuntimeError(
            "Capability resume payload must "
            "be a dictionary."
        )


    resume_action = resume_payload.get(
        "action"
    )

    if (
        resume_action
        != "RETRY_CAPABILITY"
    ):

        raise RuntimeError(
            "Unsupported capability resume "
            f"action: {resume_action!r}"
        )


    state_updates: dict[str, Any] = {}


    supplied_additional_poi_evidence = (
        resume_payload.get(
            "spp_additional_poi_evidence"
        )
    )


    if (
        capability
        == "spp.evaluate_additional_poi"
    ):

        evidence = (
            supplied_additional_poi_evidence
            or state.get(
                "spp_additional_poi_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming spp.evaluate_additional_poi "
                "requires governed additional-POI "
                "evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Additional-POI evidence must "
                "be a dictionary."
            )

        state_updates[
            "spp_additional_poi_evidence"
        ] = evidence


    elif (
        supplied_additional_poi_evidence
        is not None
    ):

        raise RuntimeError(
            "Additional-POI evidence was supplied "
            "for an unrelated capability."
        )


    supplied_land_status_evidence = (
        resume_payload.get(
            "land_status_evidence"
        )
    )


    if (
        capability
        == "land.resolve_status"
    ):

        evidence = (
            supplied_land_status_evidence
            or state.get(
                "land_status_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming land.resolve_status "
                "requires governed land_status_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Land-status evidence must "
                "be a dictionary."
            )

        state_updates[
            "land_status_evidence"
        ] = evidence


    elif (
        supplied_land_status_evidence
        is not None
    ):

        raise RuntimeError(
            "Land-status evidence was supplied "
            "for an unrelated capability."
        )


    supplied_species_evidence = (
        resume_payload.get(
            "species_evidence"
        )
    )


    if (
        capability
        == "environment.screen_species"
    ):

        evidence = (
            supplied_species_evidence
            or state.get(
                "species_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming environment.screen_species "
                "requires governed species_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Species evidence must "
                "be a dictionary."
            )

        state_updates[
            "species_evidence"
        ] = evidence


    elif (
        supplied_species_evidence
        is not None
    ):

        raise RuntimeError(
            "Species evidence was supplied "
            "for an unrelated capability."
        )


    supplied_terrain_evidence = (
        resume_payload.get(
            "terrain_evidence"
        )
    )


    if (
        capability
        == "gis.analyze_terrain"
    ):

        evidence = (
            supplied_terrain_evidence
            or state.get(
                "terrain_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming gis.analyze_terrain "
                "requires governed terrain_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Terrain evidence must "
                "be a dictionary."
            )

        state_updates[
            "terrain_evidence"
        ] = evidence


    elif (
        supplied_terrain_evidence
        is not None
    ):

        raise RuntimeError(
            "Terrain evidence was supplied "
            "for an unrelated capability."
        )


    supplied_land_cover_evidence = (
        resume_payload.get(
            "land_cover_evidence"
        )
    )


    if (
        capability
        == "gis.analyze_land_cover"
    ):

        evidence = (
            supplied_land_cover_evidence
            or state.get(
                "land_cover_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming gis.analyze_land_cover "
                "requires governed land_cover_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Land-cover evidence must "
                "be a dictionary."
            )

        state_updates[
            "land_cover_evidence"
        ] = evidence


    elif (
        supplied_land_cover_evidence
        is not None
    ):

        raise RuntimeError(
            "Land-cover evidence was supplied "
            "for an unrelated capability."
        )


    supplied_flood_evidence = (
        resume_payload.get(
            "flood_evidence"
        )
    )


    if (
        capability
        == "gis.resolve_flood_evidence"
    ):

        evidence = (
            supplied_flood_evidence
            or state.get(
                "flood_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming gis.resolve_flood_evidence "
                "requires governed flood_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Flood evidence must "
                "be a dictionary."
            )

        state_updates[
            "flood_evidence"
        ] = evidence


    elif (
        supplied_flood_evidence
        is not None
    ):

        raise RuntimeError(
            "Flood evidence was supplied "
            "for an unrelated capability."
        )


    supplied_regulatory_evidence = (
        resume_payload.get(
            "regulatory_evidence"
        )
    )


    if (
        capability
        == "regulatory.build_permit_matrix"
    ):

        evidence = (
            supplied_regulatory_evidence
            or state.get(
                "regulatory_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming regulatory.build_permit_matrix "
                "requires governed regulatory_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Regulatory evidence must "
                "be a dictionary."
            )

        state_updates[
            "regulatory_evidence"
        ] = evidence


    elif (
        supplied_regulatory_evidence
        is not None
    ):

        raise RuntimeError(
            "Regulatory evidence was supplied "
            "for an unrelated capability."
        )


    supplied_aviation_evidence = (
        resume_payload.get(
            "aviation_evidence"
        )
    )


    if (
        capability
        == "aviation.screen_candidate"
    ):

        evidence = (
            supplied_aviation_evidence
            or state.get(
                "aviation_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming aviation.screen_candidate "
                "requires governed aviation_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Aviation evidence must "
                "be a dictionary."
            )

        state_updates[
            "aviation_evidence"
        ] = evidence


    elif (
        supplied_aviation_evidence
        is not None
    ):

        raise RuntimeError(
            "Aviation evidence was supplied "
            "for an unrelated capability."
        )


    supplied_wind_resource_evidence = (
        resume_payload.get(
            "wind_resource_evidence"
        )
    )


    if (
        capability
        == "wind.analyze_candidate_resource"
    ):

        evidence = (
            supplied_wind_resource_evidence
            or state.get(
                "wind_resource_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming wind.analyze_candidate_resource "
                "requires governed wind_resource_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Wind-resource evidence must "
                "be a dictionary."
            )

        state_updates[
            "wind_resource_evidence"
        ] = evidence


    elif (
        supplied_wind_resource_evidence
        is not None
    ):

        raise RuntimeError(
            "Wind-resource evidence was supplied "
            "for an unrelated capability."
        )


    supplied_cultural_resources_evidence = (
        resume_payload.get(
            "cultural_resources_evidence"
        )
    )


    if (
        capability
        == "environment.screen_cultural_resources"
    ):

        evidence = (
            supplied_cultural_resources_evidence
            or state.get(
                "cultural_resources_evidence"
            )
        )

        if not evidence:

            raise RuntimeError(
                "Resuming "
                "environment.screen_cultural_resources "
                "requires governed "
                "cultural_resources_evidence."
            )

        if not isinstance(
            evidence,
            dict,
        ):

            raise RuntimeError(
                "Cultural-resources evidence must "
                "be a dictionary."
            )

        state_updates[
            "cultural_resources_evidence"
        ] = evidence


    elif (
        supplied_cultural_resources_evidence
        is not None
    ):

        raise RuntimeError(
            "Cultural-resources evidence was supplied "
            "for an unrelated capability."
        )



    return {
        **state_updates,
        "investigation_status": (
            "RESUMED_AFTER_CAPABILITY_WAIT"
        ),

        "route_reason": (
            f"Resumed investigation {task_id} "
            f"after external capability/evidence "
            f"work."
        ),

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                audit_event(
                    "CAPABILITY_WAIT_RESUMED",
                    task_id=task_id,
                    capability=capability,
                    resume_action=(
                        resume_action
                    ),
                    evidence_update_keys=(
                        sorted(
                            state_updates.keys()
                        )
                    ),
                )
            ]
        ),
    }


# ============================================================
# Build graph
# ============================================================

def build_investigation_graph(
    *,
    checkpointer=None,
):

    graph = StateGraph(
        InvestigationState
    )

    graph.add_node(
        "validate_state",
        validate_state,
    )

    graph.add_node(
        "select_next_investigation",
        select_next_investigation,
    )

    graph.add_node(
        "plan_project_investigation",
        plan_project_investigation,
    )

    graph.add_node(
        "check_capability",
        check_capability,
    )

    graph.add_node(
        "capability_blocked",
        pause_for_capability,
    )

    graph.add_node(
        "execute_capability",
        execute_capability,
    )

    graph.add_node(
        "assess_investigation_result",
        assess_and_record_evidence,
    )

    graph.add_node(
        "plan_follow_up",
        plan_follow_up,
    )

    graph.add_node(
        "prepare_follow_up",
        prepare_follow_up,
    )

    graph.add_node(
        "record_domain_outcome",
        record_domain_outcome,
    )


    graph.add_edge(
        START,
        "validate_state",
    )


    graph.add_conditional_edges(
        "validate_state",
        route_after_validation,
        {
            "select": (
                "select_next_investigation"
            ),
            "end": END,
        },
    )


    graph.add_conditional_edges(
        "select_next_investigation",
        route_after_selection,
        {
            "plan": (
                "plan_project_investigation"
            ),
            "capability": (
                "check_capability"
            ),
            "end": END,
        },
    )


    graph.add_conditional_edges(
        "plan_project_investigation",
        route_after_project_planning,
        {
            "capability": (
                "check_capability"
            ),
            "end": END,
        },
    )


    graph.add_conditional_edges(
        "check_capability",
        route_capability,
        {
            "execute": (
                "execute_capability"
            ),
            "blocked": (
                "capability_blocked"
            ),
        },
    )


    graph.add_edge(
        "execute_capability",
        "assess_investigation_result",
    )

    graph.add_conditional_edges(
        "assess_investigation_result",
        route_after_assessment,
        {
            "follow_up": (
                "plan_follow_up"
            ),
            "domain_complete": (
                "record_domain_outcome"
            ),
            "end": END,
        },
    )

    graph.add_edge(
        "plan_follow_up",
        "prepare_follow_up",
    )

    graph.add_edge(
        "prepare_follow_up",
        "check_capability",
    )

    graph.add_edge(
        "capability_blocked",
        "check_capability",
    )

    graph.add_edge(
        "record_domain_outcome",
        END,
    )


    return graph.compile(
        checkpointer=checkpointer
    )
