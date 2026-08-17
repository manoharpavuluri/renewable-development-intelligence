#!/usr/bin/env python3

import json
import os
from pathlib import Path

import geopandas as gpd


PROJECT_DIR = Path(
    "data/scenarios/western_ok_250mw"
)

PROJECT_PATH = PROJECT_DIR / "project.json"
AREA_PATH = PROJECT_DIR / "candidate_area.geojson"

RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit("RESULT_DIR is not set")

OUTPUT_DIR = Path(RESULT_DIR) / "gis"
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "candidate_area_profile.json"
)


# ------------------------------------------------------------
# Load project
# ------------------------------------------------------------

project = json.loads(
    PROJECT_PATH.read_text(
        encoding="utf-8"
    )
)

gdf = gpd.read_file(
    AREA_PATH
)


# ------------------------------------------------------------
# Basic validation
# ------------------------------------------------------------

if gdf.empty:
    raise SystemExit(
        "Candidate-area GeoJSON contains no features."
    )

if gdf.crs is None:
    raise SystemExit(
        "Candidate-area CRS is missing."
    )

if len(gdf) != 1:
    raise SystemExit(
        "Expected exactly one candidate-area feature."
    )

geometry = gdf.geometry.iloc[0]

if geometry is None:
    raise SystemExit(
        "Candidate-area geometry is missing."
    )

if geometry.is_empty:
    raise SystemExit(
        "Candidate-area geometry is empty."
    )

if not geometry.is_valid:
    raise SystemExit(
        "Candidate-area geometry is invalid."
    )

if geometry.geom_type not in (
    "Polygon",
    "MultiPolygon",
):
    raise SystemExit(
        f"Expected polygon geometry; "
        f"found {geometry.geom_type}"
    )


# ------------------------------------------------------------
# Normalize to WGS84
# ------------------------------------------------------------

wgs84 = gdf.to_crs(
    "EPSG:4326"
)

wgs_geometry = (
    wgs84.geometry.iloc[0]
)


# ------------------------------------------------------------
# Select local projected CRS automatically
#
# GeoPandas chooses an appropriate UTM zone based
# on the candidate geography.
# ------------------------------------------------------------

projected_crs = (
    wgs84.estimate_utm_crs()
)

if projected_crs is None:
    raise SystemExit(
        "Unable to determine projected CRS."
    )

projected = wgs84.to_crs(
    projected_crs
)

projected_geometry = (
    projected.geometry.iloc[0]
)


# ------------------------------------------------------------
# Area
# ------------------------------------------------------------

area_m2 = (
    projected_geometry.area
)

area_km2 = (
    area_m2 / 1_000_000
)

area_acres = (
    area_m2 / 4046.8564224
)


# ------------------------------------------------------------
# Perimeter
# ------------------------------------------------------------

perimeter_m = (
    projected_geometry.length
)

perimeter_km = (
    perimeter_m / 1000
)


# ------------------------------------------------------------
# Centroid
#
# Calculate centroid in projected CRS,
# then convert back to WGS84.
# ------------------------------------------------------------

centroid_projected = (
    projected_geometry.centroid
)

centroid_series = gpd.GeoSeries(
    [centroid_projected],
    crs=projected_crs,
)

centroid_wgs = centroid_series.to_crs(
    "EPSG:4326"
).iloc[0]


# ------------------------------------------------------------
# Bounds
# ------------------------------------------------------------

minx, miny, maxx, maxy = (
    wgs_geometry.bounds
)


# ------------------------------------------------------------
# Capacity-density screening
#
# This is NOT a turbine-layout calculation.
# It is simply gross candidate acreage divided
# by proposed project MW.
# ------------------------------------------------------------

target_capacity_mw = float(
    project["target_capacity_mw"]
)

gross_acres_per_mw = (
    area_acres / target_capacity_mw
)


# ------------------------------------------------------------
# Output
# ------------------------------------------------------------

result = {
    "project": {
        "project_id": project["project_id"],
        "project_name": project["project_name"],
        "technology": project["technology"],
        "target_capacity_mw": target_capacity_mw,
        "target_cod": project["target_cod"],
        "development_stage": (
            project["development_stage"]
        ),
    },

    "input_classification": (
        "DEVELOPER_ASSUMPTION"
    ),

    "geometry": {
        "source_file": str(
            AREA_PATH
        ),

        "source_crs": str(
            gdf.crs
        ),

        "analysis_crs": str(
            projected_crs
        ),

        "geometry_type": (
            geometry.geom_type
        ),

        "is_valid": (
            geometry.is_valid
        ),

        "bounds_wgs84": {
            "west": minx,
            "south": miny,
            "east": maxx,
            "north": maxy,
        },

        "centroid_wgs84": {
            "longitude": (
                centroid_wgs.x
            ),
            "latitude": (
                centroid_wgs.y
            ),
        },
    },

    "gross_site_metrics": {
        "area_square_meters": (
            area_m2
        ),

        "area_square_km": (
            area_km2
        ),

        "area_acres": (
            area_acres
        ),

        "perimeter_km": (
            perimeter_km
        ),

        "gross_acres_per_target_mw": (
            gross_acres_per_mw
        ),
    },

    "limitations": [
        (
            "Gross polygon area only; "
            "no setbacks or exclusions applied."
        ),
        (
            "Does not represent land ownership "
            "or land-control status."
        ),
        (
            "Does not represent a turbine layout."
        ),
        (
            "Does not establish developable acreage."
        ),
    ],
}


OUTPUT_PATH.write_text(
    json.dumps(
        result,
        indent=2,
    ),
    encoding="utf-8",
)


# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

print(
    "=== CANDIDATE AREA PROFILE ==="
)

print(
    "Project:",
    project["project_id"],
)

print(
    "Technology:",
    project["technology"],
)

print(
    "Target capacity:",
    f"{target_capacity_mw:,.1f} MW",
)

print(
    "Target COD:",
    project["target_cod"],
)


print(
    "\n=== GEOMETRY ==="
)

print(
    "Input CRS:",
    gdf.crs,
)

print(
    "Analysis CRS:",
    projected_crs,
)

print(
    "Geometry:",
    geometry.geom_type,
)

print(
    "Valid:",
    geometry.is_valid,
)


print(
    "\n=== LOCATION ==="
)

print(
    "Centroid:",
    f"{centroid_wgs.y:.6f}, "
    f"{centroid_wgs.x:.6f}",
)

print(
    "Bounds:",
    (
        f"W={minx:.6f}, "
        f"S={miny:.6f}, "
        f"E={maxx:.6f}, "
        f"N={maxy:.6f}"
    ),
)


print(
    "\n=== GROSS SITE METRICS ==="
)

print(
    "Area:",
    f"{area_km2:,.2f} km²",
)

print(
    "Area:",
    f"{area_acres:,.0f} acres",
)

print(
    "Perimeter:",
    f"{perimeter_km:,.2f} km",
)

print(
    "Gross acres / target MW:",
    f"{gross_acres_per_mw:,.1f}",
)


print(
    "\n=== IMPORTANT ==="
)

print(
    "Gross area is developer-supplied screening "
    "geography, not developable acreage."
)

print(
    "Environmental, terrain, infrastructure, "
    "setback, and other exclusions have not "
    "yet been applied."
)

print(
    "\nOutput:"
)

print(
    OUTPUT_PATH
)
