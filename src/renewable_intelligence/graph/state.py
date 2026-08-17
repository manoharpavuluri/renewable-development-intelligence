from __future__ import annotations

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    # --------------------------------------------------------
    # Project identity
    # --------------------------------------------------------

    project_id: str

    # --------------------------------------------------------
    # Deterministic application state
    # --------------------------------------------------------

    screening: dict[str, Any]

    gate_assessment: dict[str, Any]

    # Persistent project-level screening outcomes by domain.
    #
    # Example:
    # {
    #   "interconnection": {
    #       "gate_id": "G2",
    #       "screening_status": "HUMAN_DILIGENCE_REQUIRED",
    #       ...
    #   }
    # }
    project_domain_outcomes: dict[str, dict[str, Any]]

    # Decision produced when choosing among multiple
    # admissible root/project investigations.
    project_candidate_actions: list[dict[str, Any]]

    project_admissible_actions: list[dict[str, Any]]

    project_planner_decision: dict[str, Any] | None

    project_planner_selection_mode: str | None

    # --------------------------------------------------------
    # Governed evidence inputs
    # --------------------------------------------------------

    spp_hct_model_cases: dict[str, Any]

    spp_additional_poi_evidence: dict[str, Any]

    transmission_context_evidence: dict[str, Any]

    land_status_evidence: dict[str, Any]

    species_evidence: dict[str, Any]

    terrain_evidence: dict[str, Any]

    land_cover_evidence: dict[str, Any]

    flood_evidence: dict[str, Any]

    regulatory_evidence: dict[str, Any]

    aviation_evidence: dict[str, Any]

    wind_resource_evidence: dict[str, Any]

    cultural_resources_evidence: dict[str, Any]

    # --------------------------------------------------------
    # Investigation lifecycle
    # --------------------------------------------------------

    current_investigation: dict[str, Any] | None

    selected_task_id: str | None

    selected_capability: str | None

    capability_available: bool | None

    # Distinguishes WHY a capability isn't ready to execute:
    # "CAPABILITY_REQUIRED" (no handler implemented yet) vs
    # "EVIDENCE_REQUIRED" (handler exists, but its readiness
    # check found required governed evidence missing from state).
    # None when the capability is available and ready.
    capability_block_reason: str | None

    investigation_status: str

    investigation_result: dict[str, Any] | None

    # --------------------------------------------------------
    # Evidence sufficiency / follow-up
    # --------------------------------------------------------

    evidence_sufficiency: dict[str, Any] | None

    # Latest successfully produced evidence assessment.
    # Unlike evidence_sufficiency, this is not cleared when
    # the graph prepares the next investigation.
    latest_evidence_assessment: dict[str, Any] | None

    # Persistent assessment history for auditability,
    # evaluation, HITL, and eventual checkpoint/resume.
    evidence_ledger: list[dict[str, Any]]

    recommended_follow_up: dict[str, Any] | None

    investigation_history: list[dict[str, Any]]

    candidate_actions: list[dict[str, Any]]

    admissible_actions: list[dict[str, Any]]

    planner_decision: dict[str, Any] | None

    planner_selection_mode: str | None

    # --------------------------------------------------------
    # Graph control / audit
    # --------------------------------------------------------

    # Lifetime investigation/follow-up count retained for
    # observability across the persisted thread.
    iteration: int

    # Safety counter for the current graph invocation only.
    # Reset when execution enters through START/validation.
    run_iteration: int

    max_iterations: int

    route_reason: str | None

    errors: list[str]

    audit_events: list[dict[str, Any]]
