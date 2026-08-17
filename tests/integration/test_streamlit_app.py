"""
Smoke tests for the Streamlit presentation layer. These run the
real app script headlessly (streamlit.testing.v1.AppTest) against
the frozen example - no browser, no network, no credentials - and
assert it renders without exceptions and that the one interactive
business action (human review) correctly calls the real
human_review.finalize_recommendation() and enforces its validation.

This does not re-test business logic (that's covered by
tests/unit/test_human_review.py and
tests/unit/test_recommendation_policy.py) - it only proves the UI
wiring doesn't crash and doesn't bypass that validation.
"""

from __future__ import annotations

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")

AppTest = streamlit_testing.AppTest


def _fresh_app():

    at = AppTest.from_file("streamlit_app.py")
    at.run(timeout=30)
    return at


def _page_radio(at):

    return [r for r in at.radio if r.label == "Page"][0]


def _decision_radio(at):

    return [r for r in at.radio if r.label == "Decision"][0]


def _button(at, label):

    return [b for b in at.button if b.label == label][0]


def test_app_renders_without_exception_in_frozen_mode():

    at = _fresh_app()

    assert not at.exception
    assert set(_page_radio(at).options) == {
        "Decision",
        "Investigation",
        "Evidence",
        "Review",
    }


def test_switching_to_current_workspace_mode_does_not_crash():

    at = _fresh_app()

    mode_radio = [
        r for r in at.sidebar.radio if r.label == "Data source"
    ][0]

    mode_radio.set_value("Current Workspace").run(timeout=30)

    assert not at.exception


def test_review_evidence_button_navigates_to_evidence_page():

    at = _fresh_app()

    _button(at, "Review evidence").click().run(timeout=30)

    assert not at.exception
    assert at.session_state["page"] == "Evidence"


def test_full_recommendation_button_navigates_to_review_page():

    at = _fresh_app()

    _button(at, "Full recommendation").click().run(timeout=30)

    assert not at.exception
    assert at.session_state["page"] == "Review"


@pytest.mark.parametrize(
    "page", ["Decision", "Investigation", "Evidence", "Review"]
)
def test_each_page_renders_without_exception(page):

    at = _fresh_app()

    _page_radio(at).set_value(page).run(timeout=30)

    assert not at.exception


def test_evidence_page_provenance_selection_does_not_crash():

    at = _fresh_app()

    _page_radio(at).set_value("Evidence").run(timeout=30)

    if at.selectbox:
        at.selectbox[0].set_value(
            at.selectbox[0].options[0]
        ).run(timeout=30)

    assert not at.exception


def test_how_the_ai_works_panel_opens_and_closes():

    at = _fresh_app()

    _button(at, "⚙️ How the AI works").click().run(timeout=30)

    assert not at.exception
    assert at.session_state["show_how_it_works"] is True

    _button(at, "← Back to the decision").click().run(timeout=30)

    assert not at.exception
    assert at.session_state["show_how_it_works"] is False


def test_planner_trace_selection_inside_how_it_works_does_not_crash():

    at = _fresh_app()

    _button(at, "⚙️ How the AI works").click().run(timeout=30)

    if at.selectbox:
        at.selectbox[0].set_value(0).run(timeout=30)

    assert not at.exception


def test_human_review_approve_calls_real_finalize_and_sets_final():

    at = _fresh_app()

    _page_radio(at).set_value("Review").run(timeout=30)

    at.text_input[0].set_value("Test Reviewer")
    _decision_radio(at).set_value("approve")
    _button(at, "Submit review").click().run(timeout=30)

    assert not at.exception

    result = at.session_state["review_result"]

    assert result["human_approved"] is True
    assert result["status"] == "FINAL"
    assert result["human_review"]["reviewed_by"] == "Test Reviewer"


def test_human_review_reject_without_comment_is_rejected():

    # Proves the UI does not bypass finalize_recommendation()'s
    # own validation - a reject with no comment must surface the
    # real ValueError, not silently succeed.
    at = _fresh_app()

    _page_radio(at).set_value("Review").run(timeout=30)

    at.text_input[0].set_value("Test Reviewer")
    _decision_radio(at).set_value("reject")
    _button(at, "Submit review").click().run(timeout=30)

    assert not at.exception
    assert "review_result" not in at.session_state
    assert any(
        "comment is required" in e.value for e in at.error
    )


def test_human_review_modify_outside_envelope_requires_justification():

    # The admissible set for the frozen example is
    # {ADVANCE_WITH_CONDITIONS, HOLD}; overriding to
    # DO_NOT_ADVANCE without a justification must be rejected by
    # the real backend validation, not the UI.
    at = _fresh_app()

    _page_radio(at).set_value("Review").run(timeout=30)

    at.text_input[0].set_value("Test Reviewer")
    _decision_radio(at).set_value("modify")
    at.run(timeout=30)

    _decision_radio(at).set_value("modify")

    override_select = [
        s
        for s in at.selectbox
        if s.label == "Override recommendation"
    ][0]

    override_select.set_value("DO_NOT_ADVANCE")
    _button(at, "Submit review").click().run(timeout=30)

    assert not at.exception
    assert "review_result" not in at.session_state
    assert any(
        "falls outside the deterministic admissible set"
        in e.value
        for e in at.error
    )
