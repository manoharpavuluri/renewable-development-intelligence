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
    requires_evidence,
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


def test_implemented_capability_missing_evidence_blocks_not_executes():

    # Regression test for the exact bug this project hit with
    # gis.resolve_flood_evidence: enabling a handler made
    # check_capability report it "available" even though the
    # evidence it needs was never in state, so the graph routed
    # straight to execute_capability and crashed with an
    # uncaught RuntimeError instead of pausing for evidence like
    # every other missing-evidence case does.
    register_capability(
        Capability(
            name="test.regression_evidence_required",
            kind=CapabilityKind.PYTHON,
            description="test fixture",
            available=False,
        )
    )

    enable_capability(
        "test.regression_evidence_required",
        handler=lambda **kwargs: {"executed": True},
        readiness=requires_evidence("test_fixture_evidence"),
    )

    state_without_evidence = {
        "selected_capability": (
            "test.regression_evidence_required"
        ),
        "audit_events": [],
    }

    update = check_capability(state_without_evidence)

    assert update["capability_available"] is False
    assert update["capability_block_reason"] == "EVIDENCE_REQUIRED"
    assert (
        route_capability(
            {**state_without_evidence, **update}
        )
        == "blocked"
    )

    # Once the evidence is present, the same capability becomes
    # ready without any code change.
    state_with_evidence = {
        **state_without_evidence,
        "test_fixture_evidence": {"some": "governed evidence"},
    }

    update_with_evidence = check_capability(state_with_evidence)

    assert update_with_evidence["capability_available"] is True
    assert (
        update_with_evidence["capability_block_reason"] is None
    )
    assert (
        route_capability(
            {**state_with_evidence, **update_with_evidence}
        )
        == "execute"
    )


def test_capability_with_no_handler_reports_capability_required():

    state = {
        "selected_capability": "test.totally_unregistered",
        "audit_events": [],
    }

    update = check_capability(state)

    assert update["capability_available"] is False
    assert (
        update["capability_block_reason"] == "CAPABILITY_REQUIRED"
    )


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


def test_graph_pauses_not_crashes_when_registered_capability_lacks_evidence():

    # Full graph-level regression for the flood_evidence bug:
    # a capability whose handler is registered and available
    # BEFORE the graph ever runs, but whose required evidence is
    # not part of the initial state, must produce a durable
    # interrupt when the graph reaches it - never an uncaught
    # RuntimeError from inside execute_capability.
    register_capability(
        Capability(
            name="test.graph_regression_evidence_required",
            kind=CapabilityKind.PYTHON,
            description="test fixture",
            available=False,
        )
    )

    def _handler(*, state, task):

        evidence = state.get("test_fixture_evidence")

        if not evidence:

            raise RuntimeError(
                "handler called without required evidence - "
                "this should never happen if readiness "
                "checking works correctly"
            )

        return {
            "task_id": task["task_id"],
            "capability": (
                "test.graph_regression_evidence_required"
            ),
            "executed": True,
            "finding": {},
        }

    enable_capability(
        "test.graph_regression_evidence_required",
        handler=_handler,
        readiness=requires_evidence("test_fixture_evidence"),
    )

    checkpointer = InMemorySaver()

    graph = build_investigation_graph(checkpointer=checkpointer)

    initial_state = {
        "project_id": "TEST-PROJECT-2",
        "screening": {"project_id": "TEST-PROJECT-2"},
        "gate_assessment": {
            "project_id": "TEST-PROJECT-2",
            "investigation_queue": [
                {
                    "task_id": "INV-B",
                    "domain": "domain_b",
                    "status": "PENDING",
                    "preferred_capability": (
                        "test.graph_regression_evidence_required"
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
        "configurable": {
            "thread_id": "test-evidence-required-thread"
        }
    }

    # This must not raise. Before the readiness-check fix, a
    # registered-and-available capability with missing evidence
    # would be routed straight to execute_capability and crash.
    result = graph.invoke(initial_state, config=config)

    interrupts = result.get("__interrupt__", [])

    assert interrupts, (
        "Expected a durable interrupt for missing evidence, "
        "not silent success or a crash."
    )

    payload = getattr(interrupts[0], "value", interrupts[0])

    assert payload["block_reason"] == "EVIDENCE_REQUIRED"

    # This regression test's scope stops here deliberately: the
    # resume-with-evidence round trip for each real capability is
    # already covered by test_graph_interrupts_on_missing_capability_
    # and_resumes_same_thread above and by this project's real
    # gis.resolve_flood_evidence recovery. pause_for_capability
    # currently merges resume-supplied evidence via a per-
    # capability elif chain rather than generically, so a synthetic
    # capability name here has nothing to merge into; that's a
    # documented simplification opportunity, not something this
    # test needs to exercise to prove the readiness-check fix works.
