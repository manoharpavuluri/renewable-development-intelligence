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


def test_app_renders_without_exception_in_frozen_mode():

    at = _fresh_app()

    assert not at.exception
    assert len(at.tabs) == 7


def test_switching_to_live_mode_does_not_crash():

    at = _fresh_app()

    at.sidebar.radio[0].set_value("Live project").run(timeout=30)

    assert not at.exception


def test_planner_decisioning_tab_selection_does_not_crash():

    at = _fresh_app()

    tab3 = at.tabs[2]

    if tab3.selectbox:
        tab3.selectbox[0].set_value(0).run(timeout=30)

    assert not at.exception


def test_evidence_provenance_tab_selection_does_not_crash():

    at = _fresh_app()

    tab4 = at.tabs[3]

    if tab4.selectbox:
        tab4.selectbox[0].set_value(
            tab4.selectbox[0].options[0]
        ).run(timeout=30)

    assert not at.exception


def test_human_review_approve_calls_real_finalize_and_sets_final():

    at = _fresh_app()

    tab6 = at.tabs[5]
    tab6.text_input[0].set_value("Test Reviewer")
    tab6.radio[0].set_value("approve")
    tab6.button[0].click().run(timeout=30)

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

    tab6 = at.tabs[5]
    tab6.text_input[0].set_value("Test Reviewer")
    tab6.radio[0].set_value("reject")
    tab6.button[0].click().run(timeout=30)

    assert not at.exception
    assert "review_result" not in at.session_state
    assert any(
        "comment is required" in e.value
        for e in at.tabs[5].error
    )


def test_human_review_modify_outside_envelope_requires_justification():

    # The admissible set for the frozen example is
    # {ADVANCE_WITH_CONDITIONS, HOLD}; overriding to
    # DO_NOT_ADVANCE without a justification must be rejected by
    # the real backend validation, not the UI.
    at = _fresh_app()

    tab6 = at.tabs[5]
    tab6.text_input[0].set_value("Test Reviewer")
    tab6.radio[0].set_value("modify")
    at.run(timeout=30)

    tab6 = at.tabs[5]
    tab6.selectbox[0].set_value("DO_NOT_ADVANCE")
    tab6.button[0].click().run(timeout=30)

    assert not at.exception
    assert "review_result" not in at.session_state
    assert any(
        "falls outside the deterministic admissible set"
        in e.value
        for e in at.tabs[5].error
    )
