#!/usr/bin/env python3

"""
Builds the small, committed data/examples/rdi-wok-250-001/ snapshot
used by `make demo` and the Streamlit presentation layer.

Reads the real LangGraph checkpoint (data/spikes/ + the SQLite
checkpoint, both gitignored) and writes two compact, curated JSON
files:

  investigation/domain_summaries.json - one card per screened
    domain: the original investigation question, source authority,
    finding narrative, evidence quality, decision confidence,
    outcome, remaining diligence, and severity-rated material
    risks (via gate_synthesis.DOMAIN_RISK_EXTRACTORS, not
    reclassified here).

  investigation/evidence_provenance.json - one row per domain:
    authority, dataset, evidence quality, and a SHA-256 of the
    underlying artifact(s), computed now while the gitignored
    data/spikes/ artifacts are still present on disk.

This is export/curation, not synthesis - every field here is read
straight out of already-computed investigation results and the
existing gate_synthesis/evidence_sufficiency/recommendation_policy
outputs (already frozen separately in screening/
project_assessment_draft.json by synthesize_project_assessment.py).
No screening or recommendation logic is re-derived here.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
)
from renewable_intelligence.persistence.checkpointing import (
    open_checkpointer,
)
from renewable_intelligence.synthesis.gate_synthesis import (
    DOMAIN_RISK_EXTRACTORS,
)
from renewable_intelligence.tools.bootstrap import (
    register_implemented_capabilities,
)


THREAD_ID = os.environ.get(
    "RDI_THREAD_ID",
    "RDI-WOK-250-001:screening:v1",
)

# Mirrors synthesize_project_assessment.py's RESULT_DIR
# convention, so the Streamlit app's "Live Project" mode and this
# export agree on where a run's data lives.
RESULT_DIR = os.environ.get(
    "RESULT_DIR", "data/examples/rdi-wok-250-001"
)

OUTPUT_DIR = Path(RESULT_DIR) / "investigation"


def _sha256(path_str: str) -> str | None:

    path = Path(path_str)

    if not path.exists() or not path.is_file():
        return None

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _latest_result(
    *,
    latest_task_id: str,
    latest_capability: str,
    investigation_history: list[dict],
) -> dict | None:

    for entry in reversed(investigation_history):

        if (
            entry.get("task_id") == latest_task_id
            and entry.get("capability") == latest_capability
        ):
            return entry.get("result", {})

    return None


def build_domain_summaries(v: dict) -> list[dict]:

    questions_by_domain = {
        task["domain"]: task
        for task in v["gate_assessment"]["investigation_queue"]
    }

    summaries = []

    for domain, outcome in v["project_domain_outcomes"].items():

        task = questions_by_domain.get(domain, {})

        result = _latest_result(
            latest_task_id=outcome["latest_task_id"],
            latest_capability=outcome["latest_capability"],
            investigation_history=v["investigation_history"],
        )

        finding = (result or {}).get("finding", {})

        # Reuses the exact same per-domain risk-severity classifier
        # gate_synthesis.py itself calls when rolling up gates - the
        # icon/status shown for a domain in the UI is a presentation
        # mapping of these real severity-rated risks, never a
        # reclassification of the underlying evidence.
        extractor = DOMAIN_RISK_EXTRACTORS.get(domain)

        material_risks = (
            [
                {
                    "severity": str(risk["severity"]),
                    "description": risk["description"],
                }
                for risk in extractor(finding)
            ]
            if extractor
            else []
        )

        summaries.append(
            {
                "domain": domain,
                "gate_id": outcome["gate_id"],
                "material_risks": material_risks,
                "question": task.get("question"),
                "reason": task.get("reason"),
                "source_authority": finding.get(
                    "source_authority"
                )
                or finding.get("padus_source_authority"),
                "source_dataset": finding.get("source_dataset")
                or finding.get("padus_source_dataset"),
                "evidence_quality": (result or {}).get(
                    "evidence_quality"
                ),
                "evidence_quality_reason": (
                    result or {}
                ).get("evidence_quality_reason"),
                "interpretation_limits": (result or {}).get(
                    "interpretation_limits", []
                ),
                "screening_status": outcome["screening_status"],
                "gate_status": outcome["gate_status"],
                "decision_confidence": outcome[
                    "decision_confidence"
                ],
                "resolved_uncertainty": outcome[
                    "resolved_uncertainty"
                ],
                "remaining_uncertainty": outcome[
                    "remaining_uncertainty"
                ],
                "completed_task_ids": outcome[
                    "completed_task_ids"
                ],
            }
        )

    order = [
        "interconnection",
        "wind_resource",
        "terrain",
        "land_cover",
        "species",
        "land_status",
        "regulatory",
        "aviation",
        "flood",
        "cultural",
    ]

    summaries.sort(
        key=lambda s: order.index(s["domain"])
        if s["domain"] in order
        else 99
    )

    return summaries


def build_evidence_provenance(v: dict) -> list[dict]:

    single_artifact_domains = {
        "land_status": (
            "land_status_evidence",
            "padus_summary_artifact",
        ),
        "species": (
            "species_evidence",
            "critical_habitat_summary_artifact",
        ),
        "terrain": (
            "terrain_evidence",
            "terrain_summary_artifact",
        ),
        "land_cover": (
            "land_cover_evidence",
            "land_cover_summary_artifact",
        ),
        "flood": (
            "flood_evidence",
            "fema_nfhl_summary_artifact",
        ),
        "regulatory": (
            "regulatory_evidence",
            "jurisdiction_summary_artifact",
        ),
        "aviation": (
            "aviation_evidence",
            "aviation_summary_artifact",
        ),
        "wind_resource": (
            "wind_resource_evidence",
            "hrrr_met_summary_artifact",
        ),
        "cultural": (
            "cultural_resources_evidence",
            "nrhp_summary_artifact",
        ),
    }

    domain_summaries = {
        s["domain"]: s for s in build_domain_summaries(v)
    }

    rows = []

    for domain, (
        evidence_key,
        artifact_key,
    ) in single_artifact_domains.items():

        evidence = v.get(evidence_key) or {}
        artifact_path = evidence.get(artifact_key)
        summary = domain_summaries.get(domain, {})

        rows.append(
            {
                "domain": domain,
                "gate_id": summary.get("gate_id"),
                "authority": summary.get("source_authority"),
                "dataset": summary.get("source_dataset"),
                "evidence_quality": summary.get(
                    "evidence_quality"
                ),
                "artifact_count": 1,
                "sha256": _sha256(artifact_path)
                if artifact_path
                else None,
            }
        )

    # Interconnection draws on multiple HCT grid-data.csv files
    # (one per POI per SPP model case) plus a transmission-lines
    # geojson, not one single artifact - represented as a set.
    hct_paths = [
        path
        for case in (v.get("spp_hct_model_cases") or {}).values()
        for path in case.get("pois", {}).values()
    ]

    transmission_path = (
        v.get("transmission_context_evidence") or {}
    ).get("transmission_lines_artifact")

    all_interconnection_paths = hct_paths + (
        [transmission_path] if transmission_path else []
    )

    interconnection_summary = domain_summaries.get(
        "interconnection", {}
    )

    rows.insert(
        0,
        {
            "domain": "interconnection",
            "gate_id": interconnection_summary.get("gate_id"),
            "authority": "Southwest Power Pool",
            "dataset": (
                "HCT/Pre-Screening grid-data (multiple POIs x "
                "model cases) + HIFLD transmission lines"
            ),
            "evidence_quality": interconnection_summary.get(
                "evidence_quality"
            ),
            "artifact_count": len(all_interconnection_paths),
            "sha256": None,
            "artifact_hashes": [
                _sha256(p) for p in all_interconnection_paths
            ],
        },
    )

    order = [
        "interconnection",
        "wind_resource",
        "terrain",
        "land_cover",
        "species",
        "land_status",
        "regulatory",
        "aviation",
        "flood",
        "cultural",
    ]

    rows.sort(
        key=lambda r: order.index(r["domain"])
        if r["domain"] in order
        else 99
    )

    return rows


def build_planner_decisions(v: dict) -> list[dict]:

    """
    Reconstructs each real planner decision point (deterministic
    candidate/admissible filtering, then either an LLM selection
    or a bypassed singleton, then deterministic validation) from
    the actual audit trail - not a fabricated illustration.
    """

    decisions = []
    current: dict | None = None

    for event in v.get("audit_events", []):

        event_type = event.get("event_type")

        if event_type == "PLANNER_POLICY_APPLIED":

            if current:
                decisions.append(current)

            current = {
                "timestamp_utc": event["timestamp_utc"],
                "candidate_count": event["candidate_count"],
                "admissible_count": event["admissible_count"],
                "mode": None,
                "selected_action_id": None,
                "selected_capability": None,
                "confidence": None,
                "reason": None,
                "validated_allowed": None,
            }

        elif event_type == "LLM_PLANNER_INVOKED" and current:

            current["mode"] = "FOUNDRY_LLM"

        elif event_type == "LLM_PLANNER_DECISION" and current:

            current["selected_action_id"] = event["action_id"]
            current["selected_capability"] = event[
                "capability"
            ]
            current["confidence"] = event.get("confidence")

        elif (
            event_type == "PLANNER_BYPASSED_SINGLETON"
            and current
        ):

            current["mode"] = "DETERMINISTIC_SINGLETON"

        elif event_type == "PLANNER_DECISION_VALIDATED" and current:

            current["validated_allowed"] = event["allowed"]

            if not current["selected_action_id"]:
                current["selected_action_id"] = event.get(
                    "action_id"
                )
                current["selected_capability"] = event.get(
                    "capability"
                )

            if current["mode"] is None:
                current["mode"] = "DETERMINISTIC_SINGLETON"

    if current:
        decisions.append(current)

    # audit_events only retain action_id/capability/confidence per
    # decision point, not the LLM's free-text reasoning; the top-
    # level planner_decision field still holds that text, but only
    # for the most recent decision, so it's attached here rather
    # than fabricated for earlier points.
    final_decision = v.get("planner_decision") or {}

    for decision in decisions:

        if decision["selected_action_id"] == final_decision.get(
            "selected_action_id"
        ):
            decision["reason"] = final_decision.get("reason")

    return decisions


def main() -> None:

    register_implemented_capabilities()

    config = {"configurable": {"thread_id": THREAD_ID}}

    with open_checkpointer() as checkpointer:

        graph = build_investigation_graph(
            checkpointer=checkpointer
        )

        snapshot = graph.get_state(config)

    v = snapshot.values

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    domain_summaries = build_domain_summaries(v)
    evidence_provenance = build_evidence_provenance(v)
    planner_decisions = build_planner_decisions(v)

    (OUTPUT_DIR / "domain_summaries.json").write_text(
        json.dumps(domain_summaries, indent=2),
        encoding="utf-8",
    )

    (OUTPUT_DIR / "evidence_provenance.json").write_text(
        json.dumps(evidence_provenance, indent=2),
        encoding="utf-8",
    )

    (OUTPUT_DIR / "planner_decisions.json").write_text(
        json.dumps(planner_decisions, indent=2),
        encoding="utf-8",
    )

    print(
        f"Wrote {len(domain_summaries)} domain summaries, "
        f"{len(evidence_provenance)} provenance rows, and "
        f"{len(planner_decisions)} planner decisions to "
        f"{OUTPUT_DIR}/"
    )


if __name__ == "__main__":
    main()
