#!/usr/bin/env python3

"""
Applies a HUMAN review decision to a draft recommendation
produced by synthesize_project_assessment.py.

This script is meant to be run by a person, from a terminal,
after they have actually read the draft (recommendation,
rationale, critical conditions, unresolved risks, next diligence,
and the underlying gate synthesis / evidence artifacts). It is
the only place in this codebase that can produce
human_approved: true, and it requires a real --reviewer name to
do so - there is no default reviewer and no way to invoke this
non-interactively without naming someone accountable for the
decision.

Usage:
  finalize_recommendation.py --decision approve \
      --reviewer "Jane Smith"

  finalize_recommendation.py --decision modify \
      --reviewer "Jane Smith" \
      --override-recommendation HOLD \
      --comment "Agree with HOLD pending IPaC species list."

  finalize_recommendation.py --decision reject \
      --reviewer "Jane Smith" \
      --comment "Candidate area needs to be redrawn first."
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from renewable_intelligence.synthesis.human_review import (
    finalize_recommendation,
)


def main() -> int:

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--decision",
        required=True,
        choices=["approve", "modify", "reject"],
    )

    parser.add_argument(
        "--reviewer",
        required=True,
        help=(
            "Name of the accountable human reviewer. Required "
            "for every decision type."
        ),
    )

    parser.add_argument("--comment", default=None)

    parser.add_argument(
        "--override-recommendation",
        default=None,
        choices=[
            "ADVANCE",
            "ADVANCE_WITH_CONDITIONS",
            "HOLD",
            "DO_NOT_ADVANCE",
        ],
    )

    parser.add_argument(
        "--override-justification", default=None
    )

    parser.add_argument(
        "--draft-path",
        default=None,
        help=(
            "Path to project_assessment_draft.json. Defaults "
            "to $RESULT_DIR/screening/"
            "project_assessment_draft.json."
        ),
    )

    args = parser.parse_args()

    if args.draft_path:
        draft_path = Path(args.draft_path)
    else:
        result_dir = os.environ.get("RESULT_DIR")
        if not result_dir:
            parser.error(
                "--draft-path or RESULT_DIR is required."
            )
        draft_path = (
            Path(result_dir)
            / "screening"
            / "project_assessment_draft.json"
        )

    if not draft_path.exists():
        parser.error(f"Draft not found: {draft_path}")

    draft_document = json.loads(
        draft_path.read_text(encoding="utf-8")
    )

    try:

        final = finalize_recommendation(
            draft_document=draft_document,
            decision=args.decision,
            reviewer=args.reviewer,
            comment=args.comment,
            override_recommendation=(
                args.override_recommendation
            ),
            override_justification=(
                args.override_justification
            ),
        )

    except ValueError as exc:

        print(f"REJECTED BY POLICY: {exc}", file=sys.stderr)
        return 1

    output_path = draft_path.with_name(
        "final_recommendation.json"
    )

    output_path.write_text(
        json.dumps(final, indent=2, default=str),
        encoding="utf-8",
    )

    print("=== FINALIZED ===")
    print("Status:", final["status"])
    print("Human approved:", final["human_approved"])
    print(
        "Final recommendation:",
        final["final_recommendation"],
    )
    print("Reviewed by:", final["human_review"]["reviewed_by"])
    print("Output:", output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
