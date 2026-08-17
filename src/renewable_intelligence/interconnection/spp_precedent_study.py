from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def clean(value):
    if value is None:
        return None

    value = str(value).strip()
    return value or None


def analyze_precedent_study(
    *,
    state,
    task,
) -> dict[str, Any]:

    # --------------------------------------------------------
    # Locate source artifact.
    #
    # Support either:
    #   task["source_artifact"]
    #
    # or the currently recommended follow-up stored in state.
    # --------------------------------------------------------

    source_artifact = (
        task.get("source_artifact")
        or (
            state.get(
                "recommended_follow_up",
                {}
            )
            or {}
        ).get(
            "source_artifact"
        )
    )

    if not source_artifact:
        raise RuntimeError(
            "No precedent-study source artifact "
            "was supplied."
        )

    source_path = Path(
        source_artifact
    )

    if not source_path.exists():
        raise FileNotFoundError(
            source_path
        )


    study = json.loads(
        source_path.read_text(
            encoding="utf-8"
        )
    )


    # --------------------------------------------------------
    # Core request identity
    # --------------------------------------------------------

    request = study.get(
        "request",
        {}
    )

    study_id = request.get(
        "Gen Number"
    )

    poi = request.get(
        "POI"
    )

    mw = request.get(
        "MW Amount"
    )

    fuel = request.get(
        "Fuel Type"
    )

    service = request.get(
        "Service"
    )

    area = request.get(
        "Area"
    )


    # --------------------------------------------------------
    # Constraint summary
    # --------------------------------------------------------

    constraints = study.get(
        "constraints",
        []
    )

    constraint_type_counts = Counter(
        clean(
            row.get(
                "Constraint Type"
            )
        )
        or "UNKNOWN"
        for row in constraints
    )


    constraint_details = []

    for row in constraints:

        constraint_details.append(
            {
                "type": clean(
                    row.get(
                        "Constraint Type"
                    )
                ),

                "constraint": clean(
                    row.get(
                        "Constraints"
                    )
                ),

                "season": clean(
                    row.get(
                        "Seasons"
                    )
                ),

                "most_severe_contingency": clean(
                    row.get(
                        "Most Severe Contingency"
                    )
                ),

                "base_case_loading_percent": (
                    row.get(
                        "BC Loading %"
                    )
                ),

                "transfer_case_loading_percent": (
                    row.get(
                        "TC Loading %"
                    )
                ),

                "upgrade_name": clean(
                    row.get(
                        "Upgrade Name"
                    )
                ),
            }
        )


    # --------------------------------------------------------
    # Cost context
    # --------------------------------------------------------

    assigned_cost_summary = study.get(
        "assigned_cost_summary",
        {}
    )

    upgrade_summary = study.get(
        "upgrade_summary",
        {}
    )


    cost_context = {
        "known_allocated_upgrade_cost_total": (
            assigned_cost_summary.get(
                "known_allocated_cost_total"
            )
        ),

        "allocated_cost_contains_tbd": (
            assigned_cost_summary.get(
                "contains_tbd_allocated_cost"
            )
        ),

        "known_total_upgrade_cost_represented": (
            upgrade_summary.get(
                "known_total_upgrade_cost"
            )
        ),

        "known_cost_upgrade_count": (
            upgrade_summary.get(
                "known_cost_upgrade_count"
            )
        ),

        "tbd_cost_upgrade_count": (
            upgrade_summary.get(
                "tbd_cost_upgrade_count"
            )
        ),

        "upgrade_count": (
            upgrade_summary.get(
                "upgrade_count"
            )
        ),

        "interpretation": (
            "Known total upgrade cost represented in "
            "the study is not equivalent to the studied "
            "project's allocated interconnection cost."
        ),
    }


    # --------------------------------------------------------
    # Thermal
    # --------------------------------------------------------

    thermal = study.get(
        "thermal_summary",
        {}
    )


    thermal_context = {
        "result_count": (
            thermal.get(
                "result_count"
            )
        ),

        "max_transfer_case_loading": (
            thermal.get(
                "max_transfer_case_loading"
            )
        ),

        "facilities": (
            thermal.get(
                "facilities",
                []
            )
        ),

        "upgrades": (
            thermal.get(
                "upgrades",
                []
            )
        ),
    }


    # --------------------------------------------------------
    # Voltage
    # --------------------------------------------------------

    voltage = study.get(
        "voltage_summary",
        {}
    )


    voltage_context = {
        "result_count": (
            voltage.get(
                "result_count"
            )
        ),

        "facilities": (
            voltage.get(
                "facilities",
                []
            )
        ),
    }


    # --------------------------------------------------------
    # Stability
    #
    # IMPORTANT:
    # raw_criterion_no_counts are NOT automatically failures.
    # --------------------------------------------------------

    stability = study.get(
        "stability_summary",
        {}
    )


    stability_context = {
        "events_analyzed": (
            stability.get(
                "events_analyzed"
            )
        ),

        "raw_criterion_no_counts": (
            stability.get(
                "raw_criterion_no_counts",
                {}
            )
        ),

        "unique_violation_patterns": (
            stability.get(
                "unique_violation_patterns"
            )
        ),

        "top_violation_patterns": (
            stability.get(
                "top_violation_patterns",
                []
            )
        ),

        "top_primary_mitigations": (
            stability.get(
                "top_primary_mitigations",
                []
            )
        ),

        "interpretation_limit": (
            "Raw criterion-NO counts are study outputs "
            "and are not interpreted here as project "
            "stability failures without methodology "
            "and narrative context."
        ),
    }


    # --------------------------------------------------------
    # Short circuit
    # --------------------------------------------------------

    short_circuit = study.get(
        "short_circuit_summary",
        {}
    )


    short_circuit_context = {
        "buses_analyzed": (
            short_circuit.get(
                "buses_analyzed"
            )
        ),

        "maximum_fault_current_change_ka": (
            short_circuit.get(
                "maximum_fault_current_change_ka"
            )
        ),

        "breaker_capacity_issue_rows": (
            short_circuit.get(
                "breaker_capacity_issue_rows"
            )
        ),

        "required_facility_rows": (
            short_circuit.get(
                "required_facility_rows"
            )
        ),
    }


    # --------------------------------------------------------
    # SCR / CCT
    # --------------------------------------------------------

    scrcct = study.get(
        "scrcct_summary",
        {}
    )

    scrcct_results = study.get(
        "scrcct_results",
        []
    )


    scrcct_context = {
        "cases_analyzed": (
            scrcct.get(
                "cases_analyzed"
            )
        ),

        "minimum_scr": (
            scrcct.get(
                "minimum_scr"
            )
        ),

        "scr_failures": (
            scrcct.get(
                "scr_failures"
            )
        ),

        "minimum_cct": (
            scrcct.get(
                "minimum_cct"
            )
        ),

        "cct_failures": (
            scrcct.get(
                "cct_failures"
            )
        ),

        "summary_results": (
            scrcct_results
        ),
    }


    # --------------------------------------------------------
    # JTIQ screening
    # --------------------------------------------------------

    jtiq = study.get(
        "jtiq_screening",
        []
    )


    # --------------------------------------------------------
    # Contingent upgrades
    #
    # Deliberately preserve rows instead of summing their
    # total costs into a fake project-cost number.
    # --------------------------------------------------------

    contingent_upgrades = []

    for row in study.get(
        "contingent_upgrades",
        []
    ):

        contingent_upgrades.append(
            {
                "project_name": clean(
                    row.get(
                        "Project Name"
                    )
                ),

                "upgrade_name": clean(
                    row.get(
                        "Upgrade Name"
                    )
                ),

                "upgrade_description": clean(
                    row.get(
                        "Upgrade Description"
                    )
                ),

                "study_identified": clean(
                    row.get(
                        "Study Identified"
                    )
                ),

                "ptdf": (
                    row.get(
                        "PTDF"
                    )
                ),

                "estimated_in_service_date": (
                    row.get(
                        "Estimated In-Service Date"
                    )
                ),

                "total_upgrade_cost": (
                    row.get(
                        "Total Upgrade Cost"
                    )
                ),

                "financial_risk": clean(
                    row.get(
                        "Financial Risk on Total Upgrade Cost"
                    )
                ),
            }
        )


    # --------------------------------------------------------
    # Deterministic findings
    # --------------------------------------------------------

    findings = [
        {
            "finding_type": (
                "PRECEDENT_IDENTITY"
            ),

            "statement": (
                f"{study_id} is a {mw} MW "
                f"{fuel} interconnection study "
                f"at {poi}."
            ),

            "evidence_class": (
                "SOURCE_FACT"
            ),
        },

        {
            "finding_type": (
                "COST_DISTINCTION"
            ),

            "statement": (
                "The precedent has zero known allocated "
                "upgrade cost in the extracted structured "
                "fields, while some allocated costs remain "
                "TBD and the study represents substantial "
                "system upgrade costs. These figures must "
                "not be interpreted as the cost of the "
                "250-MW candidate project."
            ),

            "evidence_class": (
                "DERIVED_FACT"
            ),
        },
    ]


    if thermal_context[
        "result_count"
    ]:

        findings.append(
            {
                "finding_type": (
                    "THERMAL_CONSTRAINT_PRECEDENT"
                ),

                "statement": (
                    "The Tatonga precedent contains "
                    "modeled thermal constraint results "
                    "and associated upgrade context."
                ),

                "evidence_class": (
                    "SOURCE_FACT"
                ),
            }
        )


    if (
        short_circuit_context[
            "breaker_capacity_issue_rows"
        ]
        == 0
    ):

        findings.append(
            {
                "finding_type": (
                    "SHORT_CIRCUIT_PRECEDENT"
                ),

                "statement": (
                    "The extracted precedent summary "
                    "contains no breaker-capacity issue "
                    "rows."
                ),

                "evidence_class": (
                    "SOURCE_FACT"
                ),
            }
        )


    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    return {
        "task_id": (
            task.get(
                "task_id"
            )
            or task.get(
                "action_id"
            )
        ),

        "domain": (
            "interconnection"
        ),

        "capability": (
            "spp.analyze_precedent_study"
        ),

        "executed": True,

        "relationship_to_candidate": (
            "PRECEDENT_ONLY"
        ),

        "candidate_project_id": (
            state.get(
                "project_id"
            )
        ),

        "study": {
            "study_id": study_id,
            "fuel_type": fuel,
            "mw": mw,
            "poi": poi,
            "area": area,
            "service": service,
            "source_artifact": (
                str(source_path)
            ),
        },

        "constraints": {
            "count": (
                len(constraints)
            ),

            "type_counts": dict(
                sorted(
                    constraint_type_counts.items()
                )
            ),

            "details": (
                constraint_details
            ),
        },

        "cost_context": (
            cost_context
        ),

        "thermal": (
            thermal_context
        ),

        "voltage": (
            voltage_context
        ),

        "stability": (
            stability_context
        ),

        "short_circuit": (
            short_circuit_context
        ),

        "scrcct": (
            scrcct_context
        ),

        "jtiq_screening": (
            jtiq
        ),

        "contingent_upgrade_count": (
            len(
                contingent_upgrades
            )
        ),

        "contingent_upgrades": (
            contingent_upgrades
        ),

        "findings": (
            findings
        ),

        "precedent_evidence_confidence": (
            "HIGH"
        ),

        "candidate_applicability_confidence": (
            "LOW"
        ),

        "evidence_status": (
            "PARTIAL"
        ),

        "limitations": [
            (
                "GEN-2026-PR2 represents a "
                "41.89-MW wind request and is not "
                "the 250-MW candidate project."
            ),

            (
                "Precedent constraints and costs "
                "cannot be transferred directly "
                "to RDI-WOK-250-001."
            ),

            (
                "Known total upgrade cost represented "
                "in the study is not the candidate's "
                "interconnection cost."
            ),

            (
                "Raw stability criterion counts "
                "require study-methodology context "
                "before interpretation."
            ),
        ],
    }
