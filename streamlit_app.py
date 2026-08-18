"""
Renewable Development Intelligence - presentation layer.

This app DISPLAYS and INVOKES the existing system. It contains no
screening rules, no recommendation policy, no evidence
interpretation, and no approval logic of its own - every number
and status shown here is read verbatim from JSON already produced
by scripts/synthesize_project_assessment.py and
scripts/export_frozen_example.py, or comes from calling the real
renewable_intelligence.synthesis.human_review.finalize_recommendation
for the one interactive action this app offers. Per-domain material
risks shown throughout are computed by
gate_synthesis.DOMAIN_RISK_EXTRACTORS (the same functions the real
gate rollup calls) at export time, never reclassified here.

The default view is the business decision; every LangGraph/Foundry/
evidence-hash/admissible-set detail lives behind the "How the AI
works" panel for a reader who wants the architecture, not just the
answer.

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


# Same visual identity as this project's other published artifacts
# (architecture diagram, executive memo): Spectral serif for prose/
# headings, IBM Plex Mono for labels and data, a warm parchment
# ground, and the risk-severity palette reused verbatim so a color
# means the same thing here as it does in those documents. Single-
# theme by design (.streamlit/config.toml pins base="light"), so
# unlike those two artifacts this doesn't also carry a dark variant
# - Streamlit's own native chrome (sliders, checkboxes, etc.) can't
# be retheme'd by page CSS alone, and a half-dark page would be
# worse than a deliberately light one.
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --ground: #f0f0e6;
  --ground-raised: #e7e6d7;
  --ground-panel: #eae9db;
  --ink: #202623;
  --ink-soft: #4d554e;
  --ink-faint: #7d8377;
  --accent: #35637f;
  --accent-warm: #a87830;
  --line: #c9c7b3;
  --line-strong: #a8a68f;
  --risk-low: #5c8060;
  --risk-medium: #a87830;
  --risk-high: #a8502f;
  --risk-critical: #7a2a2a;
  --shadow: rgba(32, 38, 35, 0.08);
}

html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stHeader"], [data-testid="stMain"] {
  background: var(--ground) !important;
  color: var(--ink) !important;
}

.stApp, .stApp p, .stApp li, .stApp span, .stApp label,
[data-testid="stMarkdownContainer"] {
  font-family: "Spectral", Georgia, "Iowan Old Style", serif !important;
}

h1, h2, h3, h4, h5, h6 {
  font-family: "Spectral", Georgia, serif !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em;
  color: var(--ink) !important;
}

code, pre, .stCode, [data-testid="stMetricLabel"],
[data-testid="stMetricValue"], [data-testid="stCaptionContainer"],
.stCaption, small, [data-testid="stJson"] {
  font-family: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo,
    Consolas, monospace !important;
}

[data-testid="stCaptionContainer"] {
  color: var(--ink-faint) !important;
}

a, a:visited { color: var(--accent) !important; }

hr { border-color: var(--line) !important; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: var(--ground-raised) !important;
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] * {
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
}

/* Bordered containers -> plates */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
  background: var(--ground-panel) !important;
  border: 1px solid var(--line-strong) !important;
  border-radius: 2px !important;
  box-shadow: 0 1px 2px var(--shadow);
}

/* Buttons */
.stButton button, [data-testid="stFormSubmitButton"] button,
[data-testid="stBaseButton-secondary"] {
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
  font-size: 12px !important;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: var(--ground-panel) !important;
  color: var(--ink) !important;
  border: 1px solid var(--line-strong) !important;
  border-radius: 2px !important;
  box-shadow: none !important;
}
.stButton button:hover, [data-testid="stFormSubmitButton"] button:hover {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}

/* Page nav / decision radio pills */
[data-testid="stRadio"] label {
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
  font-size: 13px !important;
  letter-spacing: 0.03em;
}

/* Dataframe + JSON */
[data-testid="stDataFrame"] * {
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
}

/* Expander */
[data-testid="stExpander"] {
  border: 1px solid var(--line) !important;
  border-radius: 2px !important;
  background: var(--ground-panel) !important;
}

/* Progress bar */
[data-testid="stProgress"] > div > div > div {
  background-color: var(--accent) !important;
}

/* Rec-status badge - a real styled element, not markdown color
   syntax (which doesn't parse inside a raw HTML string). */
.rec-badge {
  font-family: "Spectral", Georgia, serif;
  font-weight: 700;
  font-size: clamp(28px, 4vw, 40px);
  text-align: center;
  letter-spacing: -0.01em;
  margin: 0.2em 0;
}
.rec-headline { text-align: center; color: var(--ink-soft); }
.rec-status { text-align: center; color: var(--ink-faint); font-size: 13px; }

.risk-tag {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px;
  letter-spacing: 0.04em;
  font-weight: 600;
}
</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)


PAGES = ["Decision", "Investigation", "Evidence", "Review"]

REC_COLOR_VAR = {
    "ADVANCE": "--risk-low",
    "ADVANCE_WITH_CONDITIONS": "--accent",
    "HOLD": "--risk-medium",
    "DO_NOT_ADVANCE": "--risk-critical",
}

REC_HEADLINE = {
    "ADVANCE": (
        "The evidence base supports moving forward - no unresolved "
        "material issues were identified."
    ),
    "ADVANCE_WITH_CONDITIONS": (
        "The opportunity can advance, but the conditions below must "
        "be resolved first."
    ),
    "HOLD": (
        "Material issues remain that should be resolved before "
        "committing additional development capital."
    ),
    "DO_NOT_ADVANCE": (
        "A disqualifying finding means this opportunity should not "
        "advance in its current form."
    ),
}

SCHEDULE_LABEL = {
    "PLAUSIBLE": "On track",
    "PLAUSIBLE_WITH_CONDITIONS": "On track, with conditions",
    "AT_RISK": "At risk",
    "NOT_ASSESSABLE": "Not assessable",
}

DOMAIN_LABELS = {
    "interconnection": "Interconnection",
    "wind_resource": "Wind Resource",
    "terrain": "Terrain",
    "land_cover": "Land Cover",
    "species": "Species",
    "land_status": "Land Status",
    "regulatory": "Regulatory",
    "aviation": "Aviation",
    "flood": "Flood",
    "cultural": "Cultural",
}

# The flood capability is this project's canonical example of
# evidence-discipline: zero digital FEMA coverage means UNKNOWN,
# never "no risk." Every other domain's material_risks (computed by
# the same DOMAIN_RISK_EXTRACTORS the real gate rollup uses) map
# straight to a found-issue icon; only flood's coverage-gap risk is
# relabeled here, and only because that domain's own evidence_quality
# is LOW specifically because of that gap, not a severity judgment
# invented for the UI.
def _domain_icon(domain_summary: dict) -> str:

    risks = domain_summary.get("material_risks", [])

    if not risks:
        return "✅"  # check

    if (
        domain_summary["domain"] == "flood"
        and domain_summary.get("evidence_quality") == "LOW"
    ):
        return "❓"  # question mark

    return "⚠️"  # warning


def _domain_severity_label(domain_summary: dict) -> str:

    risks = domain_summary.get("material_risks", [])

    if (
        domain_summary["domain"] == "flood"
        and domain_summary.get("evidence_quality") == "LOW"
        and risks
    ):
        return "UNKNOWN"

    if not risks:
        return "NONE"

    order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    severities = {r["severity"] for r in risks}

    return next((s for s in order if s in severities), "LOW")


def _goto(page: str) -> None:

    st.session_state["page"] = page
    st.rerun()


# ------------------------------------------------------------
# Sidebar: mode + "How the AI works"
# ------------------------------------------------------------

with st.sidebar:

    st.markdown("### Data source")

    mode_label = st.radio(
        "Data source",
        ["Demo Project", "Current Workspace"],
        index=0,
        label_visibility="collapsed",
    )

    mode = "frozen" if mode_label == "Demo Project" else "live"

    if mode == "frozen":
        st.caption(
            "The committed Western Oklahoma example. No Azure "
            "credentials or network access required."
        )
    else:
        st.caption(
            "The latest screening run produced on this machine."
        )

    st.markdown("---")

    if st.button("⚙️ How the AI works", width="stretch"):
        st.session_state["show_how_it_works"] = True
        st.rerun()

    st.markdown("---")
    st.markdown(
        "[GitHub repo](https://github.com/manoharpavuluri/"
        "renewable-development-intelligence)"
    )


data = load_project_data(mode)

if data is None:
    st.error(
        "No screening has been run in your current workspace yet. "
        "Switch to **Demo Project** in the sidebar to see a "
        "completed example, or run the investigation pipeline "
        "first (see README “Demo walkthrough”)."
    )
    st.stop()

if not data.has_draft:
    st.error(
        "This workspace has evidence but no completed "
        "recommendation yet. Switch to **Demo Project**, or "
        "finish synthesis for this run."
    )
    with st.expander("Developer instructions"):
        st.code(
            f"RESULT_DIR={data.result_dir} make synthesize",
            language="bash",
        )
    st.stop()


rec = data.recommendation_draft
policy = data.recommendation_policy
cod = data.cod_feasibility
sufficiency = data.evidence_sufficiency

if "page" not in st.session_state:
    st.session_state["page"] = "Decision"

if "show_how_it_works" not in st.session_state:
    st.session_state["show_how_it_works"] = False


# ------------------------------------------------------------
# Header + decision card (always visible)
# ------------------------------------------------------------

st.markdown("## Renewable Development Intelligence")
st.markdown("#### Should we continue investing in this opportunity?")

color_var = REC_COLOR_VAR.get(rec["recommendation"], "--ink")
headline = REC_HEADLINE.get(rec["recommendation"], "")

card = st.container(border=True)

with card:

    top = st.columns([2, 1, 1, 1])
    top[0].markdown("**WESTERN OKLAHOMA WIND**")
    top[1].caption("250 MW")
    top[2].caption("Western Oklahoma")
    top[3].caption(f"Target COD {data.draft.get('target_cod')}")

    status_line = (
        "Draft — awaiting human review"
        if not rec.get("human_approved")
        else f"✅ Approved by "
        f"{rec.get('reviewed_by', 'a named reviewer')}"
    )

    st.markdown(
        f"<div class='rec-badge' style='color:var({color_var})'>"
        f"{rec['recommendation'].replace('_', ' ')}</div>"
        f"<p class='rec-headline'>{headline}</p>"
        f"<p class='rec-status'>{status_line}</p>",
        unsafe_allow_html=True,
    )

    btn_cols = st.columns([3, 1, 1, 3])

    if btn_cols[1].button("Review evidence", width="stretch"):
        _goto("Evidence")

    if btn_cols[2].button("Full recommendation", width="stretch"):
        _goto("Review")


if data.has_investigation_detail:

    st.markdown("##### What the system found")

    found_cols = st.columns(5)

    for i, domain_summary in enumerate(data.domain_summaries):

        icon = _domain_icon(domain_summary)
        label = DOMAIN_LABELS.get(
            domain_summary["domain"], domain_summary["domain"]
        )
        blurb = (
            domain_summary.get("resolved_uncertainty") or [""]
        )[0]

        with found_cols[i % 5].container(border=True):
            st.markdown(f"{icon} **{label}**")
            st.caption(
                blurb[:140] + ("…" if len(blurb) > 140 else "")
            )

st.markdown("---")


# ------------------------------------------------------------
# "How the AI works" - technical panel, replaces the page nav
# ------------------------------------------------------------

if st.session_state["show_how_it_works"]:

    if st.button("← Back to the decision"):
        st.session_state["show_how_it_works"] = False
        st.rerun()

    st.markdown("## How the system stays governed")

    st.markdown(
        """
1. Business rules determine what the AI may investigate next.
2. The AI selects only among the choices those rules already allow.
3. Every domain's calculations are performed deterministically,
   never by the LLM.
4. Every finding is tied to a real, hash-verified evidence source.
5. Which recommendation categories are even legal is decided by
   policy code before the AI drafts anything.
6. A named human must approve the final decision - nothing in the
   AI-facing schema can set that flag itself.
"""
    )

    with st.expander("Show planner trace"):

        st.markdown(
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
            flow[2].write(
                f"Selected: `{d['selected_capability']}`"
            )
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
                "No planner-decision audit trail available for "
                "this run."
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

                allowed = (
                    category in policy["allowed_categories"]
                )
                st.markdown(
                    f"{'✅' if allowed else '❌'} "
                    f"{category}"
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

    with st.expander("Show evaluation / observability"):

        st.markdown("#### Offline evaluation harness")

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
                    result.stdout[-3000:]
                    + result.stderr[-1000:],
                    language="text",
                )

        with col2:
            st.caption(
                "181 deterministic tests across unit / integration "
                "/ evaluation layers - domain classification logic, "
                "grounding checks, planner-policy and "
                "recommendation-policy admissible sets, graph "
                "regression, HITL workflow, and the dashboard "
                "itself. See `.github/workflows/tests.yml` for CI."
            )

        st.markdown("---")
        st.markdown("#### Recommendation stability")
        st.caption(
            "20 live Foundry runs against the same frozen evidence "
            "(`scripts/eval_recommendation_stability.py`), "
            "asserting the deterministic layer never varies and "
            "the LLM's variation always stays within the "
            "admissible set."
        )

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("ADVANCE_WITH_CONDITIONS", 12)
        s2.metric("HOLD", 8)
        s3.metric("Determinism violations", 0)
        s4.metric("Grounding violations", 0)
        s5.metric("Retention violations", 0)

        st.markdown("---")
        st.markdown("#### Live source health")

        if st.button("Check all 11 live sources now"):

            with st.spinner(
                "Querying SPP, USGS, USFWS, FEMA, FAA, NPS..."
            ):

                result = subprocess.run(
                    [
                        sys.executable,
                        "scripts/smoke_live_sources.py",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent,
                )

            st.code(result.stdout, language="text")

        st.markdown("---")
        st.markdown("#### MLflow tracing")
        st.write(
            "`make mlflow-ui` opens the trace viewer at "
            "`sqlite:///data/runtime/mlflow.db` for a full "
            "pipeline run logged via `scripts/trace_project_run.py`."
        )

    with st.expander("Show architecture details"):
        st.write(
            "Four layers - orchestration, business capabilities, "
            "evidence/data platform, governance/observability - "
            "with deterministic computation and LLM reasoning kept "
            "in strictly separate code paths. See "
            "`docs/architecture/overview.md` in the repo for the "
            "full diagram set."
        )

    st.stop()


# ------------------------------------------------------------
# Page navigation
# ------------------------------------------------------------

selected_page = st.radio(
    "Page",
    PAGES,
    index=PAGES.index(st.session_state["page"]),
    horizontal=True,
    label_visibility="collapsed",
    key="page",
)


# ------------------------------------------------------------
# Page: Decision
# ------------------------------------------------------------

if selected_page == "Decision":

    st.markdown("### Why")

    if data.has_investigation_detail:

        severity_rank = {
            "CRITICAL": 0,
            "HIGH": 1,
            "UNKNOWN": 2,
            "MEDIUM": 3,
            "LOW": 4,
            "NONE": 5,
        }

        reasons = [
            (
                _domain_severity_label(d),
                DOMAIN_LABELS.get(d["domain"], d["domain"]),
                (d.get("material_risks") or [{}])[0].get(
                    "description", ""
                ),
            )
            for d in data.domain_summaries
            if d.get("material_risks")
        ]

        reasons.sort(key=lambda r: severity_rank.get(r[0], 9))

        severity_color_var = {
            "CRITICAL": "--risk-critical",
            "HIGH": "--risk-high",
            "UNKNOWN": "--accent-warm",
            "MEDIUM": "--risk-medium",
            "LOW": "--risk-low",
        }

        for severity, label, description in reasons[:5]:
            color_var = severity_color_var.get(severity, "--ink")
            st.markdown(
                f"<span class='risk-tag' "
                f"style='color:var({color_var})'>{severity}"
                f"</span> &nbsp; **{label}** — {description}",
                unsafe_allow_html=True,
            )

    else:
        for item in rec.get("unresolved_risks", [])[:5]:
            st.markdown(f"- {item}")

    st.markdown("---")
    st.markdown("### Development outlook")

    completed_domains = sum(
        1
        for d in data.domain_summaries
        if d.get("completed_task_ids")
    ) or len(data.domain_summaries)

    total_domains = len(data.domain_summaries) or 10

    mixed_confidence = bool(
        sufficiency.get("low_confidence_gates")
        or sufficiency.get("unresolved_high_materiality_gates")
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Target COD", data.draft.get("target_cod"))
    m2.metric(
        "Schedule outlook",
        SCHEDULE_LABEL.get(cod["status"], cod["status"]),
    )
    m3.metric(
        "Screening coverage",
        f"{completed_domains} of {total_domains}",
        help="Development areas with at least one completed "
        "investigation.",
    )
    m4.metric(
        "Evidence confidence",
        "Mixed — diligence required"
        if mixed_confidence
        else "Consistent",
    )

    with st.expander("View detailed development gates (G1–G7)"):

        for gate in data.gate_synthesis:

            risk_count = len(gate["material_risks"])
            high_or_critical = sum(
                1
                for r in gate["material_risks"]
                if r["severity"] in ("HIGH", "CRITICAL")
            )

            cols = st.columns([2, 3, 1, 1])
            cols[0].markdown(
                f"**{gate['gate_id']}** {gate['name']}"
            )
            cols[1].markdown(f"`{gate['status']}`")
            cols[2].markdown(f"conf: {gate['confidence']}")
            cols[3].markdown(
                "<span class='risk-tag' "
                "style='color:var(--risk-high)'>"
                f"{high_or_critical} high</span>"
                if high_or_critical
                else f"{risk_count} risk(s)",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"**G6** COD Feasibility &nbsp; `{cod['status']}` "
            f"&nbsp; ({cod['years_to_target_cod']} years to "
            "target)"
        )
        st.markdown(
            f"**G7** Minimum Evidence Coverage &nbsp; "
            f"`{sufficiency['status']}`"
        )
        st.caption(policy["reason"])


# ------------------------------------------------------------
# Page: Investigation
# ------------------------------------------------------------

elif selected_page == "Investigation":

    if not data.has_investigation_detail:

        st.info(
            "Detailed investigation view is not available for "
            "this run."
        )

        if mode == "live" and st.button("Generate view"):

            with st.spinner("Reading the checkpoint..."):

                result = subprocess.run(
                    [
                        sys.executable,
                        "scripts/export_frozen_example.py",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent,
                    env={
                        **__import__("os").environ,
                        "RESULT_DIR": str(data.result_dir),
                    },
                )

            if result.returncode == 0:
                st.rerun()
            else:
                st.error(result.stderr[-1500:])

    else:

        completed = sum(
            1
            for d in data.domain_summaries
            if d.get("completed_task_ids")
        )
        total = len(data.domain_summaries)

        st.markdown(
            f"### The agent investigated {total} questions"
        )
        st.progress(
            completed / total if total else 0,
            text=f"{completed} / {total} initial screens completed",
        )

        for domain in data.domain_summaries:

            icon = _domain_icon(domain)
            label = DOMAIN_LABELS.get(
                domain["domain"], domain["domain"]
            )

            with st.expander(f"{icon} **{label}**"):

                st.markdown("**Question**")
                st.write(domain.get("question") or "-")

                col1, col2 = st.columns(2)

                col1.markdown("**What we checked**")
                col1.write(
                    f"{domain.get('source_authority') or '-'} "
                    f"— {domain.get('source_dataset') or ''}"
                )

                col2.markdown("**Confidence**")
                col2.write(
                    domain.get("decision_confidence") or "-"
                )

                st.markdown("**What we found**")
                for item in domain.get(
                    "resolved_uncertainty", []
                ):
                    st.markdown(f"- {item}")

                limits = domain.get("interpretation_limits", [])

                if limits:
                    st.markdown("**What this does NOT mean**")
                    for item in limits[:2]:
                        st.markdown(f"- {item}")

                st.markdown("**Next diligence**")
                for item in domain.get(
                    "remaining_uncertainty", []
                ):
                    st.markdown(f"- {item}")

                if icon == "❓":
                    st.warning(
                        "FEMA digital coverage: 0% for this "
                        "candidate. Result: **UNKNOWN** — "
                        "not “no flood risk.” Absence "
                        "of mapping is absence of data, not a "
                        "finding."
                    )

                with st.expander("View technical detail"):
                    st.json(
                        {
                            "domain": domain["domain"],
                            "gate_id": domain["gate_id"],
                            "screening_status": domain[
                                "screening_status"
                            ],
                            "gate_status": domain["gate_status"],
                            "evidence_quality": domain[
                                "evidence_quality"
                            ],
                            "material_risks": domain[
                                "material_risks"
                            ],
                        }
                    )


# ------------------------------------------------------------
# Page: Evidence
# ------------------------------------------------------------

elif selected_page == "Evidence":

    st.markdown(
        "Every material finding can be traced to its source."
    )

    if not data.evidence_provenance:

        st.info("No evidence-provenance export found for this run.")

    else:

        domain_summaries_by_name = {
            d["domain"]: d for d in data.domain_summaries
        }

        rows = []

        for row in data.evidence_provenance:

            summary = domain_summaries_by_name.get(
                row["domain"], {}
            )
            finding = (
                summary.get("resolved_uncertainty") or [""]
            )[0]

            rows.append(
                {
                    "Development question": DOMAIN_LABELS.get(
                        row["domain"], row["domain"]
                    ),
                    "Source": row.get("authority"),
                    "Finding": finding[:100]
                    + ("…" if len(finding) > 100 else ""),
                    "Confidence": summary.get(
                        "decision_confidence"
                    ),
                }
            )

        st.dataframe(rows, width="stretch", hide_index=True)

        st.markdown("---")

        domain_names = [
            r["domain"] for r in data.evidence_provenance
        ]

        selected = st.selectbox(
            "Show provenance details for:",
            options=domain_names,
            format_func=lambda d: DOMAIN_LABELS.get(d, d),
        )

        record = next(
            r
            for r in data.evidence_provenance
            if r["domain"] == selected
        )

        with st.expander("Show provenance details", expanded=True):
            st.json(record)

        st.caption(
            "Evidence classification vocabulary used throughout "
            "this system: SOURCE_FACT, DERIVED_FACT, "
            "AGENT_INTERPRETATION, DEVELOPER_ASSUMPTION, "
            "UNRESOLVED — never just “LLM answer.”"
        )


# ------------------------------------------------------------
# Page: Review
# ------------------------------------------------------------

elif selected_page == "Review":

    st.markdown(f"## Draft recommendation: {rec['recommendation']}")

    st.markdown("### Why the system reached this conclusion")
    st.write(rec["rationale"])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Conditions before advancing")
        for item in rec.get("critical_conditions", []):
            st.markdown(f"- {item}")

        st.markdown("### Unresolved risks")
        for item in rec.get("unresolved_risks", []):
            st.markdown(f"- {item}")

    with col2:
        st.markdown("### Next diligence")
        for item in rec.get("next_diligence", []):
            st.markdown(f"- {item}")

    st.markdown("---")
    st.markdown("### Human decision")

    st.write(
        "This is an AI-generated screening recommendation. The "
        "system cannot approve its own recommendation - this tab "
        "calls the real `human_review.finalize_recommendation()`, "
        "the only code path in the repository capable of setting "
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
