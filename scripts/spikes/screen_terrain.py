#!/usr/bin/env python3

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.io import MemoryFile


CANDIDATE_PATH = Path(
    "data/scenarios/western_ok_250mw/candidate_area.geojson"
)

RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit("RESULT_DIR is not set")

OUT_DIR = Path(RESULT_DIR) / "gis" / "terrain"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEM_PATH = OUT_DIR / "candidate_dem_10m.tif"
SLOPE_PATH = OUT_DIR / "candidate_slope_percent_10m.tif"
SUMMARY_PATH = OUT_DIR / "terrain_summary.json"


IMAGE_SERVER = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer"
)

EXPORT_URL = f"{IMAGE_SERVER}/exportImage"

TARGET_CRS = "EPSG:32614"
PIXEL_SIZE_M = 10.0
SQM_PER_ACRE = 4046.8564224


candidate = gpd.read_file(CANDIDATE_PATH).to_crs(TARGET_CRS)

if candidate.empty:
    raise SystemExit("Candidate polygon is empty.")

candidate_geom = candidate.geometry.iloc[0]
candidate_acres = candidate_geom.area / SQM_PER_ACRE

minx, miny, maxx, maxy = candidate.total_bounds

width_px = int(round((maxx - minx) / PIXEL_SIZE_M))
height_px = int(round((maxy - miny) / PIXEL_SIZE_M))


session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "RenewableDevelopmentIntelligence/"
            "source-access-spike"
        )
    }
)


response = session.get(
    EXPORT_URL,
    params={
        "bbox": f"{minx},{miny},{maxx},{maxy}",
        "bboxSR": 32614,
        "imageSR": 32614,
        "size": f"{width_px},{height_px}",
        "format": "tiff",
        "pixelType": "F32",
        "noDataInterpretation": "esriNoDataMatchAny",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    },
    timeout=120,
)

response.raise_for_status()

if response.headers.get("Content-Type", "").startswith(
    "application/json"
):
    raise SystemExit(
        "3DEPElevation service returned an error: "
        + response.text[:2000]
    )


DEM_PATH.write_bytes(response.content)


with rasterio.open(DEM_PATH) as src:

    dem = src.read(1)
    transform = src.transform
    nodata = src.nodata
    crs = src.crs


valid_mask = np.isfinite(dem)

if nodata is not None:
    valid_mask &= dem != nodata

# 3DEP ocean/void sentinel and clearly implausible values.
valid_mask &= dem > -1000
valid_mask &= dem < 9000


if not valid_mask.any():
    raise RuntimeError("No valid elevation samples were returned.")


elevation_m = dem[valid_mask]


# ------------------------------------------------------------
# Slope from the elevation raster (Horn's method), percent rise.
# ------------------------------------------------------------

dem_filled = np.where(valid_mask, dem, np.nan)

dzdx = np.zeros_like(dem_filled)
dzdy = np.zeros_like(dem_filled)

dzdx[:, 1:-1] = (
    dem_filled[:, 2:] - dem_filled[:, :-2]
) / (2 * PIXEL_SIZE_M)

dzdy[1:-1, :] = (
    dem_filled[2:, :] - dem_filled[:-2, :]
) / (2 * PIXEL_SIZE_M)

slope_percent = (
    np.sqrt(dzdx**2 + dzdy**2) * 100
)

interior_mask = np.zeros_like(valid_mask)
interior_mask[1:-1, 1:-1] = True

slope_valid_mask = (
    valid_mask
    & interior_mask
    & np.isfinite(slope_percent)
)

slope_values = slope_percent[slope_valid_mask]


with rasterio.open(
    SLOPE_PATH,
    "w",
    driver="GTiff",
    height=slope_percent.shape[0],
    width=slope_percent.shape[1],
    count=1,
    dtype="float32",
    crs=crs,
    transform=transform,
    nodata=-9999.0,
) as dst:

    out = np.where(
        slope_valid_mask,
        slope_percent,
        -9999.0,
    ).astype("float32")

    dst.write(out, 1)


def pct(values, q):
    return float(np.percentile(values, q))


slope_thresholds_percent = [5, 10, 15, 20, 30]

slope_threshold_area = {}

pixel_area_acres = (PIXEL_SIZE_M * PIXEL_SIZE_M) / SQM_PER_ACRE
total_slope_pixels = int(slope_valid_mask.sum())
total_slope_acres = total_slope_pixels * pixel_area_acres

for threshold in slope_thresholds_percent:

    count_above = int((slope_values > threshold).sum())

    slope_threshold_area[f"gt_{threshold}pct"] = {
        "acres": count_above * pixel_area_acres,
        "percent_of_sampled_area": (
            count_above / total_slope_pixels * 100
            if total_slope_pixels
            else 0.0
        ),
    }


summary = {
    "source": {
        "authority": "U.S. Geological Survey",
        "dataset": "3D Elevation Program (3DEP) Bare Earth DEM",
        "service_url": IMAGE_SERVER,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "sample_resolution_m": PIXEL_SIZE_M,
        "sample_crs": str(crs),
        "raster_shape": list(dem.shape),
    },
    "candidate_area_acres": candidate_acres,
    "elevation_m": {
        "min": float(elevation_m.min()),
        "max": float(elevation_m.max()),
        "mean": float(elevation_m.mean()),
        "relief": float(
            elevation_m.max() - elevation_m.min()
        ),
        "p10": pct(elevation_m, 10),
        "p50": pct(elevation_m, 50),
        "p90": pct(elevation_m, 90),
        "valid_sample_count": int(valid_mask.sum()),
    },
    "slope_percent": {
        "min": float(slope_values.min()),
        "max": float(slope_values.max()),
        "mean": float(slope_values.mean()),
        "p50": pct(slope_values, 50),
        "p90": pct(slope_values, 90),
        "p99": pct(slope_values, 99),
        "sampled_area_acres": total_slope_acres,
        "sampled_pixel_count": total_slope_pixels,
    },
    "slope_threshold_area": slope_threshold_area,
    "evidence_classification": "SOURCE_FACT + DERIVED_FACT",
    "interpretation": (
        "Descriptive elevation and slope statistics computed from "
        "a 10 m resampled 3DEP bare-earth DEM clipped to the "
        "candidate polygon."
    ),
    "limitations": [
        (
            "Slope is computed on a 10 m resampled grid using a "
            "central-difference gradient; it is a screening-grade "
            "estimate, not a survey-grade or micro-siting-grade "
            "slope analysis."
        ),
        (
            "No wind-development slope suitability threshold is "
            "applied or endorsed here; thresholds for "
            "constructability, road/crane access, and turbine "
            "siting are project- and vendor-specific and must be "
            "set separately."
        ),
        (
            "This does not account for land cover, access, "
            "geotechnical conditions, or other constructability "
            "factors beyond slope and elevation."
        ),
    ],
}


SUMMARY_PATH.write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)


print("=== ELEVATION (m) ===")
print(
    f"min {summary['elevation_m']['min']:.1f} | "
    f"mean {summary['elevation_m']['mean']:.1f} | "
    f"max {summary['elevation_m']['max']:.1f} | "
    f"relief {summary['elevation_m']['relief']:.1f}"
)

print()
print("=== SLOPE (%) ===")
print(
    f"mean {summary['slope_percent']['mean']:.2f} | "
    f"p50 {summary['slope_percent']['p50']:.2f} | "
    f"p90 {summary['slope_percent']['p90']:.2f} | "
    f"p99 {summary['slope_percent']['p99']:.2f} | "
    f"max {summary['slope_percent']['max']:.2f}"
)

print()
print("=== AREA ABOVE SLOPE THRESHOLD ===")
for threshold in slope_thresholds_percent:
    values = slope_threshold_area[f"gt_{threshold}pct"]
    print(
        f"> {threshold:>2}% : "
        f"{values['acres']:>10,.1f} acres "
        f"({values['percent_of_sampled_area']:.2f}%)"
    )

print()
print("DEM:", DEM_PATH)
print("Slope raster:", SLOPE_PATH)
print("Summary:", SUMMARY_PATH)
