#!/usr/bin/env python3

"""
Recommendation-stability eval — live, NOT part of the offline
63-test suite (it makes N real Foundry calls).

Runs the recommendation drafter multiple times against one
FROZEN evidence packet (gate synthesis, G6, G7, admissible set
computed once and held fixed) and asserts:

  gate synthesis / G6 / G7 / admissible set   MUST NOT change
    (recomputed each iteration from the same frozen inputs and
    checked for equality, not just reused - this proves the
    deterministic layer is actually deterministic, not merely
    unexercised)

  LLM recommendation                          MAY vary, but only
    within the admissible set - any selection outside it is a
    policy violation

  LLM rationale / conditions / risks           MUST stay source-
    grounded (0 overclaiming findings from grounding_checks.py)
    MUST retain the frozen scenario's known HIGH material risks
    MUST retain the frozen scenario's known evidence gaps

This is the architectural point: we don't evaluate an agent by
demanding identical wording or identical discretionary choices.
We evaluate whether variable model reasoning stays within a
deterministic business-policy envelope and preserves invariant
facts.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
)
from renewable_intelligence.persistence.checkpointing import (
    open_checkpointer,
)
from renewable_intelligence.tools.bootstrap import (
    register_implemented_capabilities,
)
from renewable_intelligence.synthesis.gate_synthesis import (
    synthesize_all_gates,
)
from renewable_intelligence.synthesis.schedule_feasibility import (
    assess_cod_feasibility,
)
from renewable_intelligence.synthesis.evidence_sufficiency import (
    assess_evidence_sufficiency,
)
from renewable_intelligence.synthesis.recommendation_policy import (
    determine_allowed_categories,
)
from renewable_intelligence.synthesis.recommendation_drafter import (
    draft_recommendation,
    validate_recommendation,
)
from renewable_intelligence.evaluation.grounding_checks import (
    scan_draft_fields_for_overclaiming,
)


N_RUNS = int(os.environ.get("STABILITY_EVAL_RUNS", "20"))

THREAD_ID = os.environ.get(
    "RDI_THREAD_ID", "RDI-WOK-250-001:screening:v1"
)

PROJECT_JSON_PATH = Path(
    "data/scenarios/western_ok_250mw/project.json"
)


# ------------------------------------------------------------
# Retention checks tied to THIS frozen scenario's known material
# facts. A real production version of this eval would derive
# these from the frozen gate_syntheses programmatically; they
# are spelled out explicitly here so a reader can see exactly
# what "must be retained" means for this specific evidence
# packet.
# ------------------------------------------------------------

REQUIRED_RETENTION_TOPICS = {
    "critical habitat / species risk (G3, HIGH)": [
        "critical habitat",
        "endangered",
    ],
    "interconnection cost/feasibility (G2, HIGH)": [
        "feasibility",
        "upgrade cost",
        "interconnection",
    ],
    "flood evidence gap (G3)": [
        "flood",
    ],
    "cultural resource / NRHP intersection (G3)": [
        "section 106",
        "nrhp",
        "historic",
        "cultural",
    ],
}


def build_frozen_scenario():

    register_implemented_capabilities()

    config = {"configurable": {"thread_id": THREAD_ID}}

    with open_checkpointer() as checkpointer:
        graph = build_investigation_graph(checkpointer=checkpointer)
        snapshot = graph.get_state(config)

    if not snapshot.values:
        raise SystemExit(f"No saved state for thread {THREAD_ID!r}.")

    if snapshot.next:
        raise SystemExit(
            "Thread is not at a clean boundary "
            f"(pending nodes: {snapshot.next!r})."
        )

    state = snapshot.values

    project_domain_outcomes = (
        state.get("project_domain_outcomes") or {}
    )
    evidence_ledger = state.get("evidence_ledger", [])
    project_id = state["project_id"]

    target_cod = json.loads(
        PROJECT_JSON_PATH.read_text(encoding="utf-8")
    )["target_cod"]

    return {
        "project_id": project_id,
        "target_cod": target_cod,
        "project_domain_outcomes": project_domain_outcomes,
        "evidence_ledger": evidence_ledger,
    }


def compute_deterministic_layer(frozen):

    gate_syntheses = [
        g.to_dict()
        for g in synthesize_all_gates(
            project_domain_outcomes=(
                frozen["project_domain_outcomes"]
            ),
            evidence_ledger=frozen["evidence_ledger"],
        )
    ]

    cod_feasibility = assess_cod_feasibility(
        target_cod=frozen["target_cod"],
        gate_syntheses=gate_syntheses,
    )

    evidence_sufficiency = assess_evidence_sufficiency(
        gate_syntheses=gate_syntheses
    )

    policy = determine_allowed_categories(
        evidence_sufficiency=evidence_sufficiency,
        gate_syntheses=gate_syntheses,
    )

    return {
        "gate_syntheses": gate_syntheses,
        "cod_feasibility": cod_feasibility,
        "evidence_sufficiency": evidence_sufficiency,
        "policy": policy,
    }


def check_retention(text: str) -> dict[str, bool]:

    lowered = text.lower()

    return {
        topic: any(kw in lowered for kw in keywords)
        for topic, keywords in (
            REQUIRED_RETENTION_TOPICS.items()
        )
    }


def main() -> int:

    frozen = build_frozen_scenario()

    baseline = compute_deterministic_layer(frozen)

    baseline_json = json.dumps(baseline, sort_keys=True, default=str)

    allowed_categories = baseline["policy"]["allowed_categories"]

    print("=== FROZEN SCENARIO ===")
    print("Project:", frozen["project_id"])
    print(
        "Admissible categories:", allowed_categories
    )
    print()

    determinism_violations = 0
    policy_violations = 0
    grounding_violations = 0
    retention_violations = 0

    recommendation_counts = Counter()

    print(f"=== {N_RUNS} LIVE FOUNDRY RUNS ===")

    for i in range(1, N_RUNS + 1):

        layer = compute_deterministic_layer(frozen)
        layer_json = json.dumps(layer, sort_keys=True, default=str)

        if layer_json != baseline_json:
            determinism_violations += 1
            print(
                f"[{i:>2}] DETERMINISM VIOLATION: gate synthesis / "
                "G6 / G7 / admissible set changed on recompute."
            )
            continue

        draft = draft_recommendation(
            project_id=frozen["project_id"],
            gate_syntheses=layer["gate_syntheses"],
            cod_feasibility=layer["cod_feasibility"],
            evidence_sufficiency=layer["evidence_sufficiency"],
            allowed_categories=allowed_categories,
        )

        try:
            validate_recommendation(
                draft=draft,
                allowed_categories=allowed_categories,
            )
        except RuntimeError as exc:
            policy_violations += 1
            print(f"[{i:>2}] POLICY VIOLATION: {exc}")
            continue

        recommendation_counts[draft.recommendation] += 1

        field_violations = scan_draft_fields_for_overclaiming(
            rationale=draft.rationale,
            critical_conditions=draft.critical_conditions,
            unresolved_risks=draft.unresolved_risks,
            next_diligence=draft.next_diligence,
        )

        if field_violations:
            grounding_violations += 1
            print(f"[{i:>2}] GROUNDING VIOLATION:")
            for item, findings in field_violations.items():
                print(
                    f"       {item!r} -> "
                    f"{[f.pattern_name for f in findings]}"
                )

        combined_text = " ".join(
            [draft.rationale]
            + draft.critical_conditions
            + draft.unresolved_risks
            + draft.next_diligence
        )

        retention = check_retention(combined_text)
        missing = [
            topic
            for topic, present in retention.items()
            if not present
        ]

        if missing:
            retention_violations += 1
            print(
                f"[{i:>2}] RETENTION VIOLATION: dropped "
                f"{missing}"
            )

        if not field_violations and not missing:
            print(
                f"[{i:>2}] {draft.recommendation:<24} "
                f"confidence={draft.confidence:<6} OK"
            )

    print()
    print("=== RESULT ===")

    for category in allowed_categories:
        print(
            f"{category:<28} "
            f"{recommendation_counts.get(category, 0)}"
        )

    other = sum(
        count
        for cat, count in recommendation_counts.items()
        if cat not in allowed_categories
    )

    if other:
        print(f"{'OUT-OF-SET (bug)':<28} {other}")

    print(f"{'determinism violations':<28} {determinism_violations}")
    print(f"{'policy violations':<28} {policy_violations}")
    print(f"{'grounding violations':<28} {grounding_violations}")
    print(f"{'retention violations':<28} {retention_violations}")

    total_violations = (
        determinism_violations
        + policy_violations
        + grounding_violations
        + retention_violations
    )

    return 1 if total_violations else 0


if __name__ == "__main__":
    sys.exit(main())
