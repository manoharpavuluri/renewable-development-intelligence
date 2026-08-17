#!/usr/bin/env python3

import csv
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit(
        "RESULT_DIR is not set.\n"
        "Run:\n"
        "export RESULT_DIR=$(find data/spikes -maxdepth 1 "
        "-type d -name 'public_sources_*' | sort | tail -1)"
    )

PATH = Path(RESULT_DIR) / "spp_active_queue.csv"


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clean(value):
    return (value or "").strip()


def number(value):
    value = clean(value).replace(",", "")

    if not value:
        return 0.0

    try:
        return float(value)
    except ValueError:
        return 0.0


def normalize_columns(header):
    """
    Normalize source column names for analysis while preserving
    source values.

    Production ingestion will eventually keep both raw and
    normalized schema metadata.
    """
    return [clean(col) for col in header]


def classify_status(status):
    """
    Screening-level analytical classification.

    IMPORTANT:
    This is our analytical grouping, not an SPP-defined status.
    Original SPP status is always retained separately.
    """

    s = clean(status).upper()

    if "COMMERCIAL OPERATION" in s:
        return "OPERATING"

    if "IA FULLY EXECUTED" in s:
        return "COMMITTED"

    if any(
        marker in s
        for marker in [
            "DISIS",
            "FACILITY STUDY",
            "SPECIAL STUDY",
            "IA PENDING",
            "IMPACT STUDY",
            "FEASIBILITY",
        ]
    ):
        return "IN_PROCESS"

    return "OTHER"


def capacity(rows):
    return sum(number(row.get("Capacity")) for row in rows)


def parse_date(value):
    value = clean(value)

    if not value:
        return None

    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


# ------------------------------------------------------------
# Read source
# ------------------------------------------------------------

with PATH.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f)

    metadata = next(reader)

    raw_header = next(reader)
    normalized_header = normalize_columns(raw_header)

    rows = []

    for raw_row in reader:
        if not any(clean(v) for v in raw_row):
            continue

        # Pad short rows defensively.
        if len(raw_row) < len(normalized_header):
            raw_row += [""] * (len(normalized_header) - len(raw_row))

        row = dict(zip(normalized_header, raw_row))

        row["_pipeline_class"] = classify_status(
            row.get("Status")
        )

        rows.append(row)


# ------------------------------------------------------------
# Base subsets
# ------------------------------------------------------------

ok = [
    row for row in rows
    if clean(row.get("State")).upper() == "OK"
]

ok_wind = [
    row for row in ok
    if "wind" in clean(row.get("Generation Type")).lower()
    or "wind" in clean(row.get("Fuel Type")).lower()
]

operating = [
    row for row in ok_wind
    if row["_pipeline_class"] == "OPERATING"
]

committed = [
    row for row in ok_wind
    if row["_pipeline_class"] == "COMMITTED"
]

in_process = [
    row for row in ok_wind
    if row["_pipeline_class"] == "IN_PROCESS"
]

other = [
    row for row in ok_wind
    if row["_pipeline_class"] == "OTHER"
]

development_pipeline = committed + in_process + other


# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

print("=== SPP SOURCE ===")
print(f"File: {PATH}")
print(f"Source last updated: {metadata}")
print(f"Logical records: {len(rows):,}")

print("\n=== OKLAHOMA WIND: RAW SPP TOTAL ===")

print(
    f"{len(ok_wind):>5,} projects"
    f"{capacity(ok_wind):>14,.1f} MW"
)

print("\n=== OKLAHOMA WIND: ANALYTICAL PIPELINE CLASS ===")

groups = [
    ("OPERATING", operating),
    ("COMMITTED", committed),
    ("IN_PROCESS", in_process),
    ("OTHER", other),
]

for label, group in groups:
    print(
        f"{label:<15}"
        f"{len(group):>5,} projects"
        f"{capacity(group):>14,.1f} MW"
    )

print("-" * 45)

print(
    f"{'NON-OPERATING':<15}"
    f"{len(development_pipeline):>5,} projects"
    f"{capacity(development_pipeline):>14,.1f} MW"
)


# ------------------------------------------------------------
# Exact SPP statuses
# ------------------------------------------------------------

print("\n=== NON-OPERATING OK WIND — ORIGINAL SPP STATUS ===")

counter = Counter(
    clean(row.get("Status")) or "<blank>"
    for row in development_pipeline
)

for status, count in counter.most_common():
    status_rows = [
        r for r in development_pipeline
        if (clean(r.get("Status")) or "<blank>") == status
    ]

    print(
        f"{count:>4} projects "
        f"{capacity(status_rows):>10,.1f} MW  "
        f"{status}"
    )


# ------------------------------------------------------------
# POI capacity
# ------------------------------------------------------------

poi = defaultdict(
    lambda: {
        "projects": 0,
        "mw": 0.0,
        "statuses": Counter(),
    }
)

for row in development_pipeline:
    name = clean(row.get("Substation or Line")) or "<blank>"

    poi[name]["projects"] += 1
    poi[name]["mw"] += number(row.get("Capacity"))
    poi[name]["statuses"][clean(row.get("Status"))] += 1


print("\n=== NON-OPERATING OK WIND — TOP POI / LINE ===")

for name, values in sorted(
    poi.items(),
    key=lambda x: x[1]["mw"],
    reverse=True,
)[:25]:

    print(
        f"{values['mw']:>9,.1f} MW  "
        f"{values['projects']:>2} projects  "
        f"{name}"
    )


# ------------------------------------------------------------
# Transmission owners
# ------------------------------------------------------------

print("\n=== NON-OPERATING OK WIND — TRANSMISSION OWNER ===")

to_counter = defaultdict(
    lambda: {
        "projects": 0,
        "mw": 0.0,
    }
)

for row in development_pipeline:
    owner = clean(row.get("TO at POI")) or "<blank>"

    to_counter[owner]["projects"] += 1
    to_counter[owner]["mw"] += number(row.get("Capacity"))

for owner, values in sorted(
    to_counter.items(),
    key=lambda x: x[1]["mw"],
    reverse=True,
):
    print(
        f"{values['projects']:>3} projects  "
        f"{values['mw']:>10,.1f} MW  "
        f"{owner}"
    )


# ------------------------------------------------------------
# County / town source values
# ------------------------------------------------------------

print("\n=== NON-OPERATING OK WIND — LOCATION SOURCE VALUES ===")

location_counter = Counter(
    clean(row.get("Nearest Town or County")) or "<blank>"
    for row in development_pipeline
)

for value, count in location_counter.most_common(25):
    print(f"{count:>3}  {value}")


# ------------------------------------------------------------
# Commercial-operation-date profile
# ------------------------------------------------------------

print("\n=== NON-OPERATING OK WIND — COMMERCIAL OPERATION DATES ===")

cod_year_counter = Counter()

for row in development_pipeline:
    dt = parse_date(row.get("Commercial Operation Date"))

    if dt:
        cod_year_counter[str(dt.year)] += 1
    else:
        cod_year_counter["<blank/unparseable>"] += 1

for year, count in sorted(cod_year_counter.items()):
    print(f"{year:<20} {count:>3}")


# ------------------------------------------------------------
# Data quality checks
# ------------------------------------------------------------

print("\n=== DATA QUALITY OBSERVATIONS ===")

important_fields = [
    "Generation Interconnection Number",
    "Current Cluster",
    "Nearest Town or County",
    "State",
    "TO at POI",
    "Commercial Operation Date",
    "Capacity",
    "Generation Type",
    "Fuel Type",
    "Substation or Line",
    "Request Received",
    "Status",
]

for field in important_fields:
    missing = sum(
        1
        for row in rows
        if not clean(row.get(field))
    )

    pct = (missing / len(rows) * 100) if rows else 0

    print(
        f"{field:<45} "
        f"missing={missing:>4} "
        f"({pct:>5.1f}%)"
    )


# ------------------------------------------------------------
# Candidate normalization issues
# ------------------------------------------------------------

print("\n=== POTENTIAL NORMALIZATION ISSUES ===")

owners = sorted(
    {
        clean(row.get("TO at POI"))
        for row in ok_wind
        if clean(row.get("TO at POI"))
    }
)

print("Transmission-owner source values:")
for value in owners:
    print(f"  {value}")

print()

locations = sorted(
    {
        clean(row.get("Nearest Town or County"))
        for row in ok_wind
        if clean(row.get("Nearest Town or County"))
    }
)

county_variants = [
    x for x in locations
    if "county" in x.lower()
]

print("Location values explicitly containing 'County':")

for value in county_variants:
    print(f"  {value}")


print("\n=== IMPORTANT ===")
print(
    "Pipeline classes above are Renewable Development Intelligence "
    "analytical categories, not SPP-defined statuses."
)

