#!/usr/bin/env python3

import csv
import os
from collections import Counter, defaultdict
from pathlib import Path


result_dir = os.environ.get("RESULT_DIR")

if not result_dir:
    raise SystemExit(
        "RESULT_DIR is not set. Example:\n"
        "export RESULT_DIR=$(find data/spikes -maxdepth 1 "
        "-type d -name 'public_sources_*' | sort | tail -1)"
    )

path = Path(result_dir) / "spp_active_queue.csv"

if not path.exists():
    raise SystemExit(f"File not found: {path}")


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


with path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f)

    # SPP puts metadata on row 1.
    metadata_row = next(reader)

    # Actual CSV header is row 2.
    header = next(reader)

    rows = [
        dict(zip(header, row))
        for row in reader
        if any(clean(v) for v in row)
    ]


print("=== FILE ===")
print(path)

print("\n=== SPP METADATA ===")
print(metadata_row)

print("\n=== ROW / COLUMN COUNTS ===")
print("Rows:", len(rows))
print("Columns:", len(header))

print("\n=== COLUMN NAMES ===")
for i, column in enumerate(header, start=1):
    print(f"{i:02d}. {column}")


print("\n=== FIRST 3 RECORDS ===")

display_fields = [
    "Generation Interconnection Number",
    "IFS Queue Number",
    "Current Cluster",
    " Nearest Town or County",
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

for row in rows[:3]:
    print("-" * 80)
    for field in display_fields:
        if field in row:
            print(f"{field}: {clean(row[field])}")


# -------------------------------------------------------------------
# Oklahoma / Wind screening
# -------------------------------------------------------------------

oklahoma = [
    row for row in rows
    if clean(row.get("State")).upper() == "OK"
]

wind = [
    row for row in rows
    if "wind" in clean(row.get("Generation Type")).lower()
    or "wind" in clean(row.get("Fuel Type")).lower()
]

oklahoma_wind = [
    row for row in oklahoma
    if "wind" in clean(row.get("Generation Type")).lower()
    or "wind" in clean(row.get("Fuel Type")).lower()
]


def capacity(rows_):
    return sum(number(row.get("Capacity")) for row in rows_)


print("\n=== HIGH-LEVEL QUEUE PROFILE ===")
print(f"All active requests:       {len(rows):,}")
print(f"All active capacity:       {capacity(rows):,.1f} MW")
print()
print(f"Oklahoma requests:         {len(oklahoma):,}")
print(f"Oklahoma capacity:         {capacity(oklahoma):,.1f} MW")
print()
print(f"Wind requests all SPP:     {len(wind):,}")
print(f"Wind capacity all SPP:     {capacity(wind):,.1f} MW")
print()
print(f"Oklahoma wind requests:    {len(oklahoma_wind):,}")
print(f"Oklahoma wind capacity:    {capacity(oklahoma_wind):,.1f} MW")


def show_counter(title, rows_, field, n=15):
    counter = Counter(
        clean(row.get(field)) or "<blank>"
        for row in rows_
    )

    print(f"\n=== {title} ===")

    for value, count in counter.most_common(n):
        print(f"{count:4d}  {value}")


show_counter(
    "OKLAHOMA WIND — STATUS",
    oklahoma_wind,
    "Status",
)

show_counter(
    "OKLAHOMA WIND — CURRENT CLUSTER",
    oklahoma_wind,
    "Current Cluster",
)

show_counter(
    "OKLAHOMA WIND — TRANSMISSION OWNER AT POI",
    oklahoma_wind,
    "TO at POI",
)

show_counter(
    "OKLAHOMA WIND — TOWN / COUNTY",
    oklahoma_wind,
    " Nearest Town or County",
)

show_counter(
    "OKLAHOMA WIND — SUBSTATION OR LINE",
    oklahoma_wind,
    "Substation or Line",
)


# MW aggregation by POI/substation rather than just project count.
poi_mw = defaultdict(float)

for row in oklahoma_wind:
    poi = clean(row.get("Substation or Line")) or "<blank>"
    poi_mw[poi] += number(row.get("Capacity"))

print("\n=== OKLAHOMA WIND — TOP POI / LINE BY REQUESTED CAPACITY ===")

for poi, mw in sorted(
    poi_mw.items(),
    key=lambda item: item[1],
    reverse=True,
)[:20]:
    print(f"{mw:10,.1f} MW  {poi}")
