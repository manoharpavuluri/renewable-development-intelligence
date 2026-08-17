#!/usr/bin/env python3

import csv
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit("RESULT_DIR is not set")

PATH = (
    Path(RESULT_DIR)
    / "wind_resource"
    / "hrrr_met_2025_test_point.csv"
)


def clean(value):
    value = (value or "").strip()
    return value if value else None


def number(value):
    value = clean(value)

    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def percentile(values, pct):
    values = sorted(values)

    if not values:
        return None

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * pct

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    fraction = position - lower

    return (
        values[lower] * (1 - fraction)
        + values[upper] * fraction
    )


def circular_mean_degrees(values):
    if not values:
        return None

    sin_sum = sum(
        math.sin(math.radians(v))
        for v in values
    )

    cos_sum = sum(
        math.cos(math.radians(v))
        for v in values
    )

    angle = math.degrees(
        math.atan2(sin_sum, cos_sum)
    )

    return angle % 360


def direction_sector(degrees):
    sectors = [
        "N", "NE", "E", "SE",
        "S", "SW", "W", "NW",
    ]

    index = int(
        ((degrees + 22.5) % 360) / 45
    )

    return sectors[index]


with PATH.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as f:

    reader = csv.reader(f)

    metadata_row = next(reader)
    header = next(reader)

    rows = [
        dict(zip(header, row))
        for row in reader
        if any(clean(v) for v in row)
    ]


metadata = {
    metadata_row[i]: metadata_row[i + 1]
    for i in range(0, len(metadata_row) - 1, 2)
}


# ----------------------------------------------------------
# Build timestamps
# ----------------------------------------------------------

timestamps = []

for row in rows:
    timestamps.append(
        datetime(
            int(row["Year"]),
            int(row["Month"]),
            int(row["Day"]),
            int(row["Hour"]),
            int(row["Minute"]),
        )
    )


timestamp_counts = Counter(timestamps)

duplicates = [
    ts
    for ts, count in timestamp_counts.items()
    if count > 1
]


expected = []

if timestamps:
    cursor = min(timestamps)
    end = max(timestamps)

    while cursor <= end:
        expected.append(cursor)
        cursor += timedelta(hours=1)


missing_timestamps = sorted(
    set(expected) - set(timestamps)
)


# ----------------------------------------------------------
# Wind speeds
# ----------------------------------------------------------

speed_fields = {
    "100m": "wind speed at 100m (m/s)",
    "120m": "wind speed at 120m (m/s)",
    "160m": "wind speed at 160m (m/s)",
}

speed_values = {}

for height, field in speed_fields.items():

    speed_values[height] = [
        value
        for row in rows
        if (
            value := number(row.get(field))
        ) is not None
    ]


# ----------------------------------------------------------
# Wind shear alpha
#
# Power law:
#
# V2 / V1 = (H2 / H1) ^ alpha
#
# alpha =
# ln(V2 / V1) / ln(H2 / H1)
# ----------------------------------------------------------

shear_values = []

for row in rows:

    v100 = number(
        row.get("wind speed at 100m (m/s)")
    )

    v160 = number(
        row.get("wind speed at 160m (m/s)")
    )

    if (
        v100 is None
        or v160 is None
        or v100 <= 0
        or v160 <= 0
    ):
        continue

    alpha = (
        math.log(v160 / v100)
        / math.log(160 / 100)
    )

    shear_values.append(alpha)


# ----------------------------------------------------------
# Direction
# ----------------------------------------------------------

direction_field = (
    "wind direction at 100m (deg)"
)

directions = [
    value
    for row in rows
    if (
        value := number(
            row.get(direction_field)
        )
    ) is not None
]


direction_sectors = Counter(
    direction_sector(value)
    for value in directions
)


# ----------------------------------------------------------
# Monthly wind speed
# ----------------------------------------------------------

monthly = defaultdict(list)

for row in rows:

    value = number(
        row.get(
            "wind speed at 120m (m/s)"
        )
    )

    if value is not None:
        monthly[int(row["Month"])].append(value)


# ----------------------------------------------------------
# Missing-value profile
# ----------------------------------------------------------

important_fields = [
    "wind speed at 100m (m/s)",
    "wind speed at 120m (m/s)",
    "wind speed at 160m (m/s)",
    "wind direction at 100m (deg)",
    "air temperature at 100m (C)",
    "air pressure at 100m (hPa)",
]


# Calculate circular mean before building the persisted summary.
mean_direction = circular_mean_degrees(
    directions
)


# ----------------------------------------------------------
# Persist deterministic screening summary
# ----------------------------------------------------------

OUTPUT_PATH = (
    Path(RESULT_DIR)
    / "wind_resource"
    / "hrrr_met_2025_test_point_summary.json"
)


def wind_stats(values):
    return {
        "observations": len(values),
        "mean_mps": statistics.fmean(values),
        "median_mps": statistics.median(values),
        "p10_mps": percentile(values, 0.10),
        "p50_mps": percentile(values, 0.50),
        "p90_mps": percentile(values, 0.90),
        "max_mps": max(values),
    }


summary = {
    "source": {
        "dataset": "HRRR MET Toolkit",
        "source_file": str(PATH),
        "site_id": metadata.get("SiteID"),
        "site_timezone": metadata.get("Site Timezone"),
        "data_timezone": metadata.get("Data Timezone"),
        "returned_grid_point": {
            "longitude": number(metadata.get("Longitude")),
            "latitude": number(metadata.get("Latitude")),
        },
    },

    "screening_status": "PARTIAL",

    "time_series_quality": {
        "rows": len(rows),
        "unique_timestamps": len(set(timestamps)),
        "first_timestamp": (
            min(timestamps).isoformat()
            if timestamps else None
        ),
        "last_timestamp": (
            max(timestamps).isoformat()
            if timestamps else None
        ),
        "duplicate_timestamp_count": len(duplicates),
        "missing_hourly_slot_count": len(missing_timestamps),
    },

    "wind_speed": {
        "100m": wind_stats(speed_values["100m"]),
        "120m": wind_stats(speed_values["120m"]),
        "160m": wind_stats(speed_values["160m"]),
    },

    "wind_shear_100m_160m": {
        "valid_observations": len(shear_values),
        "mean_alpha": (
            statistics.fmean(shear_values)
            if shear_values
            else None
        ),
        "median_alpha": (
            statistics.median(shear_values)
            if shear_values
            else None
        ),
    },

    "wind_direction_100m": {
        "circular_mean_degrees": mean_direction,
        "sector_counts": dict(direction_sectors),
    },

    "monthly_mean_wind_speed_120m": {
        str(month): (
            statistics.fmean(monthly[month])
            if monthly.get(month)
            else None
        )
        for month in range(1, 13)
    },

    "evidence_classification": (
        "SOURCE_FACT + DERIVED_FACT"
    ),

    "limitations": [
        (
            "This extraction represents one modeled "
            "HRRR grid location, not the full candidate polygon."
        ),
        (
            "Only calendar year 2025 is included."
        ),
        (
            "HRRR values are modeled meteorological data, "
            "not site met-tower measurements."
        ),
        (
            "No turbine power curve has been applied."
        ),
        (
            "This result does not represent AEP, "
            "capacity factor, P50, or P90."
        ),
    ],
}


OUTPUT_PATH.write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)

# ----------------------------------------------------------
# Report
# ----------------------------------------------------------

print("=== HRRR MET TOOLKIT PROFILE ===")

print("File:", PATH)

print("\n=== SOURCE METADATA ===")

for key, value in metadata.items():
    print(f"{key}: {value}")


print("\n=== TIME SERIES QUALITY ===")

print(f"Rows:                {len(rows):,}")
print(
    f"Unique timestamps:   "
    f"{len(set(timestamps)):,}"
)

if timestamps:
    print(
        "First timestamp:     ",
        min(timestamps),
    )

    print(
        "Last timestamp:      ",
        max(timestamps),
    )

print(
    f"Duplicate timestamps: "
    f"{len(duplicates):,}"
)

print(
    f"Missing hourly slots: "
    f"{len(missing_timestamps):,}"
)


print("\n=== MISSING VALUES ===")

for field in important_fields:

    missing = sum(
        1
        for row in rows
        if clean(row.get(field)) is None
    )

    pct = (
        missing / len(rows) * 100
        if rows
        else 0
    )

    print(
        f"{field:<38} "
        f"{missing:>5} "
        f"({pct:>5.2f}%)"
    )


print("\n=== WIND SPEED SUMMARY ===")

for height in ("100m", "120m", "160m"):

    values = speed_values[height]

    print(f"\n{height}")

    print(
        f"  observations: {len(values):,}"
    )

    print(
        f"  mean:         "
        f"{statistics.fmean(values):.3f} m/s"
    )

    print(
        f"  median:       "
        f"{statistics.median(values):.3f} m/s"
    )

    print(
        f"  P10:          "
        f"{percentile(values, 0.10):.3f} m/s"
    )

    print(
        f"  P50:          "
        f"{percentile(values, 0.50):.3f} m/s"
    )

    print(
        f"  P90:          "
        f"{percentile(values, 0.90):.3f} m/s"
    )

    print(
        f"  max:          "
        f"{max(values):.3f} m/s"
    )


print("\n=== 100m → 160m WIND SHEAR ===")

print(
    "Valid observations:",
    f"{len(shear_values):,}",
)

if shear_values:

    print(
        "Mean alpha:       ",
        f"{statistics.fmean(shear_values):.4f}",
    )

    print(
        "Median alpha:     ",
        f"{statistics.median(shear_values):.4f}",
    )


print("\n=== WIND DIRECTION AT 100m ===")

mean_direction = circular_mean_degrees(
    directions
)

print(
    "Circular mean:",
    (
        f"{mean_direction:.1f}°"
        if mean_direction is not None
        else "N/A"
    ),
)

print("\nDirection sectors:")

total_directions = len(directions)

for sector in [
    "N", "NE", "E", "SE",
    "S", "SW", "W", "NW",
]:

    count = direction_sectors[sector]

    pct = (
        count / total_directions * 100
        if total_directions
        else 0
    )

    print(
        f"  {sector:<2} "
        f"{count:>5,} "
        f"({pct:>5.1f}%)"
    )


print("\n=== MONTHLY MEAN WIND SPEED — 120m ===")

month_names = [
    "",
    "Jan", "Feb", "Mar", "Apr",
    "May", "Jun", "Jul", "Aug",
    "Sep", "Oct", "Nov", "Dec",
]

for month in range(1, 13):

    values = monthly.get(month, [])

    if not values:
        print(
            f"{month_names[month]}: N/A"
        )
        continue

    print(
        f"{month_names[month]}: "
        f"{statistics.fmean(values):.3f} m/s "
        f"({len(values):,} hours)"
    )


print("\n=== IMPORTANT ===")

print(
    "These are screening-level statistics from "
    "HRRR modeled meteorological data."
)

print(
    "They are not met-tower measurements, "
    "bankable energy estimates, AEP, P50, or P90."
)
