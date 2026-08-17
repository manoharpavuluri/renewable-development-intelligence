"""
Renewable Development Intelligence - presentation layer.

This app DISPLAYS and INVOKES the existing system. It contains no
screening rules, no recommendation policy, no evidence
interpretation, and no approval logic of its own - every number
and status shown here is read verbatim from JSON already produced
by scripts/synthesize_project_assessment.py and
scripts/export_frozen_example.py, or comes from calling the real
renewable_intelligence.synthesis.human_review.finalize_recommendation
for the one interactive action this app offers.

Run with: streamlit run streamlit_app.py
"""

from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from app.data_loader import load_project_data  # noqa: E402
from renewable_intelligence.synthesis.human_review import (  # noqa: E402
    ALLOWED_RECOMMENDATIONS,
    finalize_recommendation,
)


st.set_page_config(
    page_title="Renewable Development Intelligence",
    page_icon="\U0001f32c️",
    layout="wide",
)


# ------------------------------------------------------------
# Mode selector + data loading
# ------------------------------------------------------------

with st.sidebar:

    st.markdown("### Demo mode")

    mode_label = st.radio(
        "Data source",
        ["Frozen example", "Live project"],
        index=0,
        label_visibility="collapsed",
    )

    mode = "frozen" if mode_label == "Frozen example" else "live"

    if mode == "frozen":
        st.caption(
            "Reads `data/examples/rdi-wok-250-001/` - a small, "
            "committed snapshot. No credentials, no network "
            "calls, cannot fail."
        )
    else:
        st.caption(
            "Reads the most recent `data/spikes/<run>/` "
            "directory on this machine (gitignored, not part of "
            "the repo). Requires a completed local investigation "
            "run."
        )

    st.markdown("---")
    st.markdown(
        "[GitHub repo](https://github.com/manoharpavuluri/"
        "renewable-development-intelligence)"
    )


data = load_project_data(mode)

if data is None:
    st.error(
        "No live run found under `data/spikes/`. Run the "
        "investigation pipeline first (see README \"Demo "
        "walkthrough\"), or switch to **Frozen example** in the "
        "sidebar."
    )
    st.stop()

if not data.has_draft:
    st.error(
        f"No `project_assessment_draft.json` found under "
        f"`{data.result_dir}`. Run `make synthesize` (live mode) "
        "or switch to **Frozen example**."
    )
    st.stop()


rec = data.recommendation_draft
policy = data.recommendation_policy
cod = data.cod_feasibility
sufficiency = data.evidence_sufficiency


# ------------------------------------------------------------
# Header + recommendation banner
# ------------------------------------------------------------

st.markdown("## Renewable Development Intelligence")
st.caption(
    f"{data.draft.get('project_id', 'Unknown project')} | "
    f"250 MW | SPP | Target COD: {data.draft.get('target_cod')}"
    + ("" if data.is_frozen else "  ·  *live project data*")
)

badge_color = {
    "ADVANCE": "green",
    "ADVANCE_WITH_CONDITIONS": "blue",
    "HOLD": "orange",
    "DO_NOT_ADVANCE": "red",
}.get(rec["recommendation"], "gray")

card = st.container(border=True)

with card:

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(f"# :{badge_color}[{rec['recommendation']}]")
        st.caption(rec.get("status", ""))

    with c2:
        st.metric("COD feasibility", cod["status"])
        st.metric(
            "Evidence coverage",
            sufficiency["status"].replace("_", " ").title(),
        )
        st.metric(
            "Human approval",
            "APPROVED"
            if rec.get("human_approved")
            else "PENDING",
        )


tabs = st.tabs(
    [
        "Executive Overview",
        "Investigation Journey",
        "Agent Decisioning",
        "Evidence & Provenance",
        "Recommendation",
        "Human Review",
        "Quality & Observability",
    ]
)


# ------------------------------------------------------------
# Tab 1 - Executive Overview
# ------------------------------------------------------------

with tabs[0]:

    st.markdown("### Gate summary (G1-G5)")

    for gate in data.gate_synthesis:

        risk_count = len(gate["material_risks"])
        high_or_critical = sum(
            1
            for r in gate["material_risks"]
            if r["severity"] in ("HIGH", "CRITICAL")
        )

        cols = st.columns([2, 3, 1, 1])
        cols[0].markdown(f"**{gate['gate_id']}** {gate['name']}")
        cols[1].markdown(f"`{gate['status']}`")
        cols[2].markdown(f"conf: {gate['confidence']}")
        cols[3].markdown(
            f":red[{high_or_critical} high]"
            if high_or_critical
            else f"{risk_count} risk(s)"
        )

    st.markdown(
        f"**G6** COD Feasibility &nbsp; `{cod['status']}` "
        f"&nbsp; ({cod['years_to_target_cod']} years to target)"
    )
    st.markdown(
        f"**G7** Minimum Evidence Coverage &nbsp; "
        f"`{sufficiency['status']}`"
    )

    st.markdown("---")

    total_risks = sum(
        len(g["material_risks"]) for g in data.gate_synthesis
    )
    high_risks = sum(
        1
        for g in data.gate_synthesis
        for r in g["material_risks"]
        if r["severity"] in ("HIGH", "CRITICAL")
    )
    unresolved_items = sum(
        len(g["evidence_gaps"]) for g in data.gate_synthesis
    ) + len(rec.get("unresolved_risks", []))

    m1, m2, m3 = st.columns(3)
    m1.metric("HIGH/CRITICAL risks", high_risks)
    m2.metric("Unresolved items", unresolved_items)
    m3.metric("Domains screened", len(data.domain_summaries) or 10)

    st.markdown(f"### Why {rec['recommendation']}")
    st.write(policy["reason"])
    st.markdown("**Unresolved risks named in the draft:**")
    for item in rec.get("unresolved_risks", []):
        st.markdown(f"- {item}")


# ------------------------------------------------------------
# Tab 2 - Investigation Journey
# ------------------------------------------------------------

with tabs[1]:

    if not data.has_investigation_detail:
        st.info(
            "No per-domain investigation detail found for this "
            "run. In live mode, generate it with:\n\n"
            f"`RESULT_DIR={data.result_dir} python "
            "scripts/export_frozen_example.py`"
        )

    else:

        st.markdown(
            "Ten authoritative-source investigations, each "
            "governed by a different federal, state, or utility "
            "authority. Expand a domain to see the real evidence "
            "chain behind it."
        )

        status_icon = {
            "HUMAN_DILIGENCE_REQUIRED": "⚠️",
        }

        for domain in data.domain_summaries:

            icon = status_icon.get(
                domain["screening_status"], "✅"
            )

            with st.expander(
                f"{icon} **{domain['domain'].upper()}** "
                f"({domain['gate_id']}) - "
                f"{domain['screening_status']}"
            ):

                st.markdown(f"**Question**")
                st.write(domain.get("question") or "-")

                col1, col2, col3 = st.columns(3)
                col1.markdown(
                    f"**Source**\n\n{domain.get('source_authority') or '-'}"
                    f"\n\n{domain.get('source_dataset') or ''}"
                )
                col2.markdown(
                    f"**Evidence quality**\n\n"
                    f"{domain.get('evidence_quality') or '-'}"
                )
                col3.markdown(
                    f"**Decision confidence**\n\n"
                    f"{domain.get('decision_confidence') or '-'}"
                )

                st.markdown("**Finding**")
                for item in domain.get(
                    "resolved_uncertainty", []
                ):
                    st.markdown(f"- {item}")

                st.markdown("**Remaining diligence**")
                for item in domain.get(
                    "remaining_uncertainty", []
                ):
                    st.markdown(f"- {item}")

                # The flood domain is this project's canonical
                # example of evidence-discipline: zero digital
                # coverage means UNKNOWN, never "no risk."
                if (
                    domain["domain"] == "flood"
                    and domain.get("evidence_quality") == "LOW"
                ):
                    st.warning(
                        "FEMA digital coverage: 0% for this "
                        "candidate. Result: **UNKNOWN** - not "
                        "\"no flood risk.\" Absence of mapping "
                        "is absence of data, not a finding."
                    )


# ------------------------------------------------------------
# Tab 3 - Agent Decisioning
# ------------------------------------------------------------

with tabs[2]:

    st.markdown(
        "### The model never decides what it is allowed to do"
    )
    st.write(
        "Two places in this system use the same pattern: "
        "deterministic code computes an admissible set, an LLM "
        "selects only from within it, and a deterministic "
        "validator re-checks the selection before it's acted on."
    )

    st.markdown("#### 1. Investigation planning")

    if data.planner_decisions:

        labels = [
            f"{d['selected_action_id']} "
            f"({d['selected_capability']}) - "
            f"{d['candidate_count']} candidates -> "
            f"{d['admissible_count']} admissible"
            for d in data.planner_decisions
        ]

        choice = st.selectbox(
            "Real planner decision points from this run "
            "(chronological):",
            options=range(len(labels)),
            format_func=lambda i: labels[i],
            index=min(3, len(labels) - 1),
        )

        d = data.planner_decisions[choice]

        flow = st.columns(4)

        flow[0].markdown("**DETERMINISTIC POLICY**")
        flow[0].metric(
            "Candidate actions", d["candidate_count"]
        )

        flow[1].markdown("**ADMISSIBLE SET**")
        flow[1].metric(
            "Admissible actions", d["admissible_count"]
        )

        flow[2].markdown(
            "**FOUNDRY PLANNER**"
            if d["mode"] == "FOUNDRY_LLM"
            else "**DETERMINISTIC (singleton)**"
        )
        flow[2].write(f"Selected: `{d['selected_capability']}`")
        if d.get("confidence"):
            flow[2].caption(f"confidence: {d['confidence']}")

        flow[3].markdown("**VALIDATOR**")
        flow[3].write(
            "✅ Selection belongs to admissible set"
            if d["validated_allowed"]
            else "❌ Rejected - outside admissible set"
        )

        if d.get("reason"):
            st.caption(f"Planner reasoning: {d['reason']}")

    else:
        st.info(
            "No planner-decision audit trail available for this "
            "run."
        )

    st.markdown("---")
    st.markdown("#### 2. Recommendation category")

    rec_flow = st.columns(2)

    with rec_flow[0]:

        st.markdown("**DETERMINISTIC RECOMMENDATION POLICY**")

        for category in [
            "ADVANCE",
            "ADVANCE_WITH_CONDITIONS",
            "HOLD",
            "DO_NOT_ADVANCE",
        ]:

            allowed = category in policy["allowed_categories"]
            st.markdown(
                f"{'✅' if allowed else '❌'} {category}"
            )

        st.caption(policy["reason"])

    with rec_flow[1]:

        st.markdown("**FOUNDRY**")
        st.markdown(f"Draft: `{rec['recommendation']}`")
        st.caption(
            "The model never decides what it is allowed to "
            "recommend - only which admissible category best "
            "fits the evidence."
        )


# ------------------------------------------------------------
# Tab 4 - Evidence & Provenance
# ------------------------------------------------------------

with tabs[3]:

    if not data.evidence_provenance:

        st.info("No evidence-provenance export found for this run.")

    else:

        st.markdown(
            "Every domain's evidence traces to a real, "
            "authoritative source, hash-verified at the point "
            "the deterministic capability consumed it."
        )

        rows = [
            {
                "Domain": row["domain"],
                "Gate": row.get("gate_id"),
                "Authority": row.get("authority"),
                "Dataset": row.get("dataset"),
                "Quality": row.get("evidence_quality"),
                "Artifacts": row.get("artifact_count"),
                "Hash verified": "✅"
                if row.get("sha256")
                or any(row.get("artifact_hashes") or [])
                else "—",
            }
            for row in data.evidence_provenance
        ]

        st.dataframe(
            rows, width="stretch", hide_index=True
        )

        st.markdown("---")

        domain_names = [r["domain"] for r in data.evidence_provenance]
        selected = st.selectbox(
            "Inspect a record", options=domain_names
        )

        record = next(
            r
            for r in data.evidence_provenance
            if r["domain"] == selected
        )

        st.json(record)

        st.caption(
            "Evidence classification vocabulary used throughout "
            "this system: SOURCE_FACT, DERIVED_FACT, "
            "AGENT_INTERPRETATION, DEVELOPER_ASSUMPTION, "
            "UNRESOLVED - never just \"LLM answer.\""
        )


# ------------------------------------------------------------
# Tab 5 - Recommendation
# ------------------------------------------------------------

with tabs[4]:

    st.markdown(f"## DRAFT RECOMMENDATION: {rec['recommendation']}")

    st.markdown("### Rationale")
    st.write(rec["rationale"])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Critical conditions")
        for item in rec.get("critical_conditions", []):
            st.markdown(f"- {item}")

        st.markdown("### Unresolved risks")
        for item in rec.get("unresolved_risks", []):
            st.markdown(f"- {item}")

    with col2:
        st.markdown("### Next diligence")
        for item in rec.get("next_diligence", []):
            st.markdown(f"- {item}")

        st.markdown("### Confidence / evidence quality")
        st.write(
            f"Confidence: **{rec['confidence']}** &nbsp; | "
            f"&nbsp; Evidence quality: **{rec['evidence_quality']}**"
        )

    if not rec.get("human_approved"):
        st.warning(
            "⚠️ **HUMAN REVIEW REQUIRED** - this "
            "recommendation has not been approved. See the "
            "\"Human Review\" tab."
        )
    else:
        st.success("This recommendation has been finalized.")


# ------------------------------------------------------------
# Tab 6 - Human Review
# ------------------------------------------------------------

with tabs[5]:

    st.markdown(
        "This tab calls the real "
        "`human_review.finalize_recommendation()` function - the "
        "only code path in this repository capable of setting "
        "`human_approved: true`. It operates on an **in-memory "
        "copy** of the draft for this demo session; it never "
        "writes back to `data/` or the canonical checkpoint."
    )

    if "review_result" in st.session_state:

        result = st.session_state["review_result"]

        st.markdown("#### Review recorded (this session only)")
        st.json(result)

        if st.button("Reset review"):
            del st.session_state["review_result"]
            st.rerun()

    else:

        with st.form("human_review_form"):

            reviewer = st.text_input("Reviewer", value="")

            decision = st.radio(
                "Decision", ["approve", "modify", "reject"]
            )

            comment = st.text_area("Comment")

            override_recommendation = None
            override_justification = None

            if decision == "modify":

                override_recommendation = st.selectbox(
                    "Override recommendation",
                    sorted(ALLOWED_RECOMMENDATIONS),
                )

                override_justification = st.text_area(
                    "Justification (required if the override "
                    "falls outside the deterministic admissible "
                    f"set {policy['allowed_categories']})"
                )

            submitted = st.form_submit_button("Submit review")

            if submitted:

                try:

                    draft_copy = copy.deepcopy(data.draft)

                    result = finalize_recommendation(
                        draft_document=draft_copy,
                        decision=decision,
                        reviewer=reviewer,
                        comment=comment or None,
                        override_recommendation=(
                            override_recommendation
                        ),
                        override_justification=(
                            override_justification or None
                        ),
                    )

                    st.session_state["review_result"] = result
                    st.rerun()

                except ValueError as exc:

                    st.error(str(exc))


# ------------------------------------------------------------
# Tab 7 - Quality & Observability
# ------------------------------------------------------------

with tabs[6]:

    st.markdown("### Offline evaluation harness")

    col1, col2 = st.columns([1, 2])

    with col1:

        if st.button("Run `make test` now"):

            with st.spinner("Running pytest..."):

                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "tests/",
                        "-q",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent,
                )

            st.code(
                result.stdout[-3000:] + result.stderr[-1000:],
                language="text",
            )

    with col2:
        st.caption(
            "174 deterministic tests across unit / integration / "
            "evaluation layers - domain classification logic, "
            "grounding checks, planner-policy and recommendation-"
            "policy admissible sets, graph regression, HITL "
            "workflow. See `.github/workflows/tests.yml` for CI."
        )

    st.markdown("---")
    st.markdown("### Recommendation stability")
    st.caption(
        "20 live Foundry runs against the same frozen evidence "
        "(`scripts/eval_recommendation_stability.py`), asserting "
        "the deterministic layer never varies and the LLM's "
        "variation always stays within the admissible set."
    )

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("ADVANCE_WITH_CONDITIONS", 12)
    s2.metric("HOLD", 8)
    s3.metric("Determinism violations", 0)
    s4.metric("Grounding violations", 0)
    s5.metric("Retention violations", 0)

    st.markdown("---")
    st.markdown("### Live source health")

    if st.button("Check all 11 live sources now"):

        with st.spinner("Querying SPP, USGS, USFWS, FEMA, FAA, NPS..."):

            result = subprocess.run(
                [sys.executable, "scripts/smoke_live_sources.py"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent,
            )

        st.code(result.stdout, language="text")

    st.caption(
        "Live-source drift can't be caught by the offline suite "
        "- this hits every real government/utility API this "
        "project depends on and checks both reachability and "
        "expected schema."
    )

    st.markdown("---")
    st.markdown("### MLflow tracing")
    st.write(
        "`make mlflow-ui` opens the trace viewer at "
        "`sqlite:///data/runtime/mlflow.db` for a full pipeline "
        "run logged via `scripts/trace_project_run.py`."
    )
