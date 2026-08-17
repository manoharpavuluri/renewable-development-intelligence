#!/usr/bin/env bash
set -euo pipefail

: "${RESULT_DIR:?RESULT_DIR is not set}"
: "${NLR_EMAIL:?Set NLR_EMAIL first}"

NLR_API_KEY="${NLR_API_KEY:-DEMO_KEY}"

OUT_DIR="$RESULT_DIR/wind_resource"
OUT="$OUT_DIR/hrrr_met_2025_test_point.csv"

mkdir -p "$OUT_DIR"

# Temporary source-access test coordinate only.
# This is NOT the final candidate project location.
TEST_WKT='POINT(-99.0 36.0)'

ATTRIBUTES='windspeed_100m,windspeed_120m,windspeed_160m,winddirection_100m,temperature_100m,pressure_100m'

URL='https://developer.nlr.gov/api/wind-toolkit/v2/wind/wtk-hrrr-met-toolkit-v1-0-0-download.csv'

echo "=== HRRR MET TOOLKIT API SPIKE ==="
echo "WKT:        $TEST_WKT"
echo "Year:       2025"
echo "Interval:   60 minutes"
echo "Attributes: $ATTRIBUTES"
echo

HTTP_CODE=$(
  curl \
    --location \
    --silent \
    --show-error \
    --get \
    "$URL" \
    --data-urlencode "api_key=$NLR_API_KEY" \
    --data-urlencode "wkt=$TEST_WKT" \
    --data-urlencode "attributes=$ATTRIBUTES" \
    --data-urlencode "names=2025" \
    --data-urlencode "interval=60" \
    --data-urlencode "email=$NLR_EMAIL" \
    --output "$OUT" \
    --write-out '%{http_code}'
)

echo "HTTP: $HTTP_CODE"

if [[ "$HTTP_CODE" != "200" ]]; then
    echo
    echo "Request failed. Response body:"
    cat "$OUT"
    exit 1
fi

echo
echo "=== FILE ==="
file "$OUT"

echo
echo "=== SIZE ==="
ls -lh "$OUT"

echo
echo "=== LINE COUNT ==="
wc -l "$OUT"

echo
echo "=== FIRST 5 LINES ==="
head -5 "$OUT"

echo
echo "=== SHA256 ==="
shasum -a 256 "$OUT"
