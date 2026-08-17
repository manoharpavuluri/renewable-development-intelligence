#!/usr/bin/env bash

set -u

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="data/spikes/public_sources_${TIMESTAMP}"

mkdir -p "$OUT_DIR"

echo "Renewable Development Intelligence"
echo "Public-source connectivity spike"
echo "Output: $OUT_DIR"
echo

probe() {
    NAME="$1"
    URL="$2"
    OUTPUT="$3"

    printf "%-28s " "$NAME"

    HTTP_CODE=$(
        curl \
            --location \
            --silent \
            --show-error \
            --connect-timeout 15 \
            --max-time 90 \
            --output "$OUTPUT" \
            --write-out "%{http_code}" \
            "$URL" 2>"$OUTPUT.error"
    )

    CURL_EXIT=$?

    if [ "$CURL_EXIT" -eq 0 ] && [[ "$HTTP_CODE" =~ ^2|^3 ]]; then
        SIZE=$(wc -c < "$OUTPUT" | tr -d ' ')
        printf "OK   HTTP=%s bytes=%s\n" "$HTTP_CODE" "$SIZE"
        rm -f "$OUTPUT.error"
    else
        printf "FAIL curl=%s HTTP=%s\n" "$CURL_EXIT" "$HTTP_CODE"

        if [ -s "$OUTPUT.error" ]; then
            sed 's/^/    /' "$OUTPUT.error"
        fi
    fi
}

echo "=== Structured / machine-accessible sources ==="

probe \
    "SPP active queue CSV" \
    "https://opsportal.spp.org/Studies/GenerateActiveCSV" \
    "$OUT_DIR/spp_active_queue.csv"

probe \
    "SPP study index" \
    "https://opsportal.spp.org/Studies/Gen" \
    "$OUT_DIR/spp_studies.html"

probe \
    "HRRR MET S3 listing" \
    "https://nrel-pds-wtk.s3.amazonaws.com/?list-type=2&prefix=hrrr_met_toolkit%2F&max-keys=5" \
    "$OUT_DIR/hrrr_met_s3.xml"

probe \
    "USGS TNMAccess" \
    "https://tnmaccess.nationalmap.gov/api/v1/docs" \
    "$OUT_DIR/usgs_tnm.html"

probe \
    "FEMA NFHL REST" \
    "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer?f=pjson" \
    "$OUT_DIR/fema_nfhl.json"

probe \
    "USFWS Wetlands REST" \
    "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/?f=pjson" \
    "$OUT_DIR/usfws_wetlands.json"

probe \
    "NPS NRHP REST" \
    "https://mapservices.nps.gov/arcgis/rest/services/cultural_resources/nrhp_locations/MapServer?f=pjson" \
    "$OUT_DIR/nps_nrhp.json"

echo
echo "=== Public document / workflow sources ==="

probe \
    "Oklahoma OCC wind" \
    "https://oklahoma.gov/occ/divisions/public-utility/energy/renewable-energy/ok-wind-farms-energy-facilities.html" \
    "$OUT_DIR/ok_occ_wind.html"

probe \
    "USFWS IPaC" \
    "https://ipac.ecosphere.fws.gov/" \
    "$OUT_DIR/usfws_ipac.html"

probe \
    "FAA OEAAA" \
    "https://oeaaa.faa.gov/" \
    "$OUT_DIR/faa_oeaaa.html"

probe \
    "USGS Annual NLCD" \
    "https://www.usgs.gov/centers/eros/science/annual-national-land-cover-database" \
    "$OUT_DIR/usgs_nlcd.html"

probe \
    "USGS PAD-US" \
    "https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-overview" \
    "$OUT_DIR/usgs_padus.html"

echo
echo "=== Files created ==="
find "$OUT_DIR" -maxdepth 1 -type f -not -name "*.error" -exec basename {} \; | sort

echo
echo "Spike complete."
echo "RESULT_DIR=$OUT_DIR"
