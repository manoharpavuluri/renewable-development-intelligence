"""
Layer 4 — agent / LangGraph regression tests.

These cover the exact failure modes CLAUDE_HANDOFF.md described:
replay of completed work, missing-capability handling, evidence-
ledger duplication, domain-outcome progression, and interrupt /
resume semantics. Node functions are tested directly wherever
possible (fast, no network/LLM); one true graph-level test proves
the interrupt/resume mechanics using an in-memory checkpointer.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from renewable_intelligence.graph.investigation_graph import (
    assess_and_record_evidence,
    build_investigation_graph,
    check_capability,
    record_domain_outcome,
    route_after_assessment,
    route_capability,
    select_next_investigation,
)
from renewable_intelligence.tools.registry import (
    Capability,
    CapabilityKind,
    enable_capability,
    register_capability,
)


# ------------------------------------------------------------
# select_next_investigation: no replay of completed work
# ------------------------------------------------------------

def _base_state(**overrides):

    state = {
        "project_id": "TEST-PROJECT",
        "gate_assessment": {
            "investigation_queue": [
                {
                    "task_id": "INV-A",
                    "domain": "domain_a",
                    "status": "PENDING",
                    "preferred_capability": "test.capability_a",
                },
                {
                    "task_id": "INV-B",
                    "domain": "domain_b",
                    "status": "PENDING",
                    "preferred_capability": "test.capability_b",
                },
            ]
        },
        "investigation_history": [],
        "project_domain_outcomes": {},
        "audit_events": [],
    }

    state.update(overrides)

    return state


def test_completed_task_is_never_replayed():

    state = _base_state(
        investigation_history=[
            {"task_id": "INV-A", "domain": "domain_a"},
        ]
    )

    result = select_next_investigation(state)

    candidate_ids = {
        a["action_id"]
        for a in result["project_candidate_actions"]
    }

    assert "INV-A" not in candidate_ids
    assert "INV-B" in candidate_ids


def test_exhausted_domain_excludes_its_pending_tasks():

    state = _base_state(
        project_domain_outcomes={
            "domain_a": {
                "screening_status": "HUMAN_DILIGENCE_REQUIRED",
            }
        }
    )

    result = select_next_investigation(state)

    candidate_ids = {
        a["action_id"]
        for a in result["project_candidate_actions"]
    }

    assert "INV-A" not in candidate_ids
    assert "INV-B" in candidate_ids


def test_all_domains_exhausted_yields_no_pending_investigations():

    state = _base_state(
        investigation_history=[
            {"task_id": "INV-A", "domain": "domain_a"},
        ],
        project_domain_outcomes={
            "domain_a": {
                "screening_status": "HUMAN_DILIGENCE_REQUIRED"
            },
            "domain_b": {
                "screening_status": "HUMAN_DILIGENCE_REQUIRED"
            },
        },
    )

    result = select_next_investigation(state)

    assert (
        result["investigation_status"]
        == "NO_PENDING_INVESTIGATIONS"
    )
    assert result["project_candidate_actions"] == []


# ------------------------------------------------------------
# check_capability / route_capability
# ------------------------------------------------------------

def test_unregistered_capability_routes_to_blocked():

    state = {
        "selected_capability": "test.totally_unregistered",
        "audit_events": [],
    }

    update = check_capability(state)

    assert update["capability_available"] is False
    assert route_capability({**state, **update}) == "blocked"


def test_registered_available_capability_routes_to_execute():

    register_capability(
        Capability(
            name="test.regression_fake_capability",
            kind=CapabilityKind.PYTHON,
            description="test fixture",
            available=False,
        )
    )

    enable_capability(
        "test.regression_fake_capability",
        handler=lambda **kwargs: {"executed": True},
    )

    state = {
        "selected_capability": (
            "test.regression_fake_capability"
        ),
        "audit_events": [],
    }

    update = check_capability(state)

    assert update["capability_available"] is True
    assert route_capability({**state, **update}) == "execute"


# ------------------------------------------------------------
# evidence ledger: append-exactly-once / idempotent re-assessment
# ------------------------------------------------------------

def _flood_state(existing_ledger=None):

    return {
        "selected_task_id": "INV-010",
        "selected_capability": "gis.resolve_flood_evidence",
        "investigation_result": {
            "task_id": "INV-010",
            "capability": "gis.resolve_flood_evidence",
            "executed": True,
            "finding": {
                "nfhl_coverage_status": "NO_DIGITAL_COVERAGE",
                "nfhl_mapped_coverage_percent": 0.0,
                "nfhl_unmapped_or_unknown_percent": 100.0,
            },
            "zones": {},
        },
        "investigation_history": [
            {
                "task_id": "INV-010",
                "capability": "gis.resolve_flood_evidence",
                "domain": "flood",
            }
        ],
        "evidence_ledger": existing_ledger or [],
        "audit_events": [],
    }


def test_evidence_ledger_gets_exactly_one_entry():

    update = assess_and_record_evidence(_flood_state())

    assert len(update["evidence_ledger"]) == 1
    assert (
        update["evidence_ledger"][0]["task_id"] == "INV-010"
    )


def test_re_assessing_same_task_updates_ledger_instead_of_duplicating():

    first = assess_and_record_evidence(_flood_state())

    second = assess_and_record_evidence(
        _flood_state(
            existing_ledger=first["evidence_ledger"]
        )
    )

    assert len(second["evidence_ledger"]) == 1


# ------------------------------------------------------------
# record_domain_outcome: project progresses past a completed domain
# ------------------------------------------------------------

def test_record_domain_outcome_clears_lifecycle_and_records_result():

    state = {
        "evidence_sufficiency": {
            "status": "HUMAN_DILIGENCE_REQUIRED",
            "gate_id": "G3",
            "gate_status": "UNRESOLVED",
            "decision_confidence": "MEDIUM",
            "resolved_uncertainty": [],
            "remaining_uncertainty": [],
        },
        "current_investigation": {
            "task_id": "INV-010",
            "domain": "flood",
        },
        "selected_task_id": "INV-010",
        "selected_capability": "gis.resolve_flood_evidence",
        "investigation_history": [
            {
                "task_id": "INV-010",
                "domain": "flood",
                "capability": "gis.resolve_flood_evidence",
            }
        ],
        "project_domain_outcomes": {},
        "audit_events": [],
    }

    update = record_domain_outcome(state)

    assert "flood" in update["project_domain_outcomes"]
    assert update["current_investigation"] is None
    assert update["selected_task_id"] is None
    assert (
        update["investigation_status"]
        == "DOMAIN_SCREENING_RECORDED"
    )


# ------------------------------------------------------------
# route_after_assessment: domain_complete vs follow_up vs end
# ------------------------------------------------------------

def test_route_after_assessment_domain_complete():

    state = {
        "evidence_sufficiency": {
            "status": "HUMAN_DILIGENCE_REQUIRED"
        },
        "recommended_follow_up": None,
        "run_iteration": 0,
        "max_iterations": 25,
    }

    assert route_after_assessment(state) == "domain_complete"


def test_route_after_assessment_follow_up():

    state = {
        "evidence_sufficiency": {
            "status": "FOLLOW_UP_REQUIRED"
        },
        "recommended_follow_up": {"action_id": "X"},
        "run_iteration": 0,
        "max_iterations": 25,
    }

    assert route_after_assessment(state) == "follow_up"


def test_route_after_assessment_max_iterations_ends():

    state = {
        "evidence_sufficiency": {
            "status": "FOLLOW_UP_REQUIRED"
        },
        "recommended_follow_up": {"action_id": "X"},
        "run_iteration": 25,
        "max_iterations": 25,
    }

    assert route_after_assessment(state) == "end"


# ------------------------------------------------------------
# Full graph: interrupt on missing capability, resume same
# thread, never replay completed work.
# ------------------------------------------------------------

def test_graph_interrupts_on_missing_capability_and_resumes_same_thread():

    checkpointer = InMemorySaver()

    graph = build_investigation_graph(checkpointer=checkpointer)

    initial_state = {
        "project_id": "TEST-PROJECT",
        "screening": {"project_id": "TEST-PROJECT"},
        "gate_assessment": {
            "project_id": "TEST-PROJECT",
            "investigation_queue": [
                {
                    "task_id": "INV-A",
                    "domain": "domain_a",
                    "status": "PENDING",
                    "preferred_capability": (
                        "test.graph_regression_missing"
                    ),
                    "priority": "HIGH",
                }
            ],
        },
        "current_investigation": None,
        "selected_task_id": None,
        "selected_capability": None,
        "capability_available": None,
        "investigation_status": "INITIALIZED",
        "investigation_result": None,
        "evidence_sufficiency": None,
        "latest_evidence_assessment": None,
        "evidence_ledger": [],
        "recommended_follow_up": None,
        "investigation_history": [],
        "iteration": 0,
        "max_iterations": 25,
        "route_reason": None,
        "errors": [],
        "audit_events": [],
    }

    config = {
        "configurable": {"thread_id": "test-regression-thread"}
    }

    result = graph.invoke(initial_state, config=config)

    interrupts = result.get("__interrupt__", [])

    assert interrupts, (
        "Expected the graph to interrupt on an unregistered "
        "capability."
    )

    interrupt_payload = getattr(
        interrupts[0], "value", interrupts[0]
    )

    assert (
        interrupt_payload["type"]
        == "CAPABILITY_OR_EVIDENCE_REQUIRED"
    )
    assert interrupt_payload["task_id"] == "INV-A"


    # Register the capability now (as if a human had implemented
    # it) and resume the SAME thread.
    register_capability(
        Capability(
            name="test.graph_regression_missing",
            kind=CapabilityKind.PYTHON,
            description="test fixture",
            available=False,
        )
    )

    enable_capability(
        "test.graph_regression_missing",
        handler=lambda *, state, task: {
            "task_id": task["task_id"],
            "capability": "test.graph_regression_missing",
            "executed": True,
            "finding": {},
        },
    )

    resumed = graph.invoke(
        Command(resume={"action": "RETRY_CAPABILITY"}),
        config=config,
    )

    history = resumed.get("investigation_history", [])

    assert len(history) == 1
    assert history[0]["task_id"] == "INV-A"

    # A second identical invoke against the same thread must not
    # re-execute or duplicate the completed investigation: the
    # graph has reached a terminal state (fallback assessment ->
    # "end", since no result_assessment branch exists for this
    # synthetic capability), so state.next is empty and there is
    # nothing left to replay.
    final_snapshot = graph.get_state(config)

    assert final_snapshot.next == ()
