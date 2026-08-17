#!/usr/bin/env python3

"""
Legislative-status evidence for the Oklahoma bills referenced by
regulatory.build_permit_matrix (SB2, HB2751).

Unlike every other spike script in this project, this one does
NOT query a machine-readable API - the Oklahoma Legislature's
bill-status pages are HTML/ASPX with no clean REST endpoint, and
LegiScan blocks automated fetches. The facts below were verified
directly against oklegislature.gov and the Oklahoma Senate's own
press release on 2026-08-17, and are recorded here as a governed,
timestamped, cited evidence artifact rather than as hardcoded
Python constants - specifically so a future staleness check has
something to check against.

This evidence requires periodic MANUAL re-verification; there is
no automated freshness signal for it the way there is for the
ArcGIS-backed sources (see scripts/smoke_live_sources.py, which
deliberately does not attempt to cover this source for the same
reason).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit("RESULT_DIR is not set")

OUT_DIR = Path(RESULT_DIR) / "gis" / "legislative_status"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_PATH = OUT_DIR / "ok_wind_legislation_summary.json"


VERIFIED_AT = "2026-08-17"


summary = {
    "source": {
        "authority": "Oklahoma Legislature",
        "dataset": (
            "Bill status - wind-energy setback legislation, "
            "2025-2026 Regular Session"
        ),
        "verification_method": (
            "MANUAL - official Legislature bill-status pages "
            "and the Oklahoma Senate's own press release checked "
            "directly; no machine-readable API is available for "
            "this source."
        ),
        "verified_utc": (
            f"{VERIFIED_AT}T00:00:00+00:00"
        ),
    },
    "bills": [
        {
            "bill": "SB2",
            "legislative_session": (
                "2025-2026 Regular Session"
            ),
            "subject": (
                "Wind energy; setback requirements for certain "
                "affected counties; waiver; referral to eligible "
                "voters; zoning; construction; exemptions; "
                "database."
            ),
            "status": "FAILED",
            "last_action": (
                "Second Conference Committee Report adopted by "
                "the Senate 31-16, then rejected by the House "
                "20-67 the same day; the bill will not advance "
                "further this Legislature."
            ),
            "last_action_date": "2026-05-14",
            "source_urls": [
                "https://www.oklegislature.gov/BillInfo.aspx?Bill=SB2&Session=2600",
                "https://oksenate.gov/press-releases/pro-tem-paxton-comments-senate-bill-2-receiving-no-further-action",
            ],
        },
        {
            "bill": "HB2751",
            "legislative_session": (
                "2025-2026 Regular Session"
            ),
            "subject": (
                "Wind turbine setback requirements based on "
                "population density and geographic area."
            ),
            "status": "FAILED",
            "last_action": (
                "Failed in the Senate Energy Committee, 4-6. Its "
                "substance was later folded into an SB2 amendment "
                "attempt, which the Senate Pro Tem blocked on "
                "procedural grounds (same-subject-matter rule) "
                "before SB2 itself ultimately failed."
            ),
            "last_action_date": "2025-04-24",
            "source_urls": [
                "https://okenergytoday.com/2025/04/wind-turbine-setback-bill-fails-in-oklahoma-senate-committee/",
            ],
        },
    ],
    "evidence_classification": "SOURCE_FACT",
    "limitations": [
        (
            "This evidence was manually verified against official "
            f"sources as of {VERIFIED_AT} and is not refreshed "
            "automatically; treat it as stale after any subsequent "
            "legislative session convenes."
        ),
        (
            "A bill's failure in one session does not preclude "
            "materially similar legislation being reintroduced in "
            "a future session."
        ),
    ],
}

SUMMARY_PATH.write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("=== OKLAHOMA WIND-SETBACK LEGISLATION STATUS ===")
for bill in summary["bills"]:
    print(
        f"{bill['bill']:<8} {bill['status']:<8} "
        f"{bill['last_action_date']}"
    )
    print("   ", bill["last_action"])

print()
print("Summary:", SUMMARY_PATH)
