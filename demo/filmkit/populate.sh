#!/usr/bin/env bash
set -e
TOK="Authorization: Bearer mpp_tok_demo"
CT="Content-Type: application/json"
URL=http://localhost:8010
for r in 1 2 3; do
  for p in 1 2 3 4 5; do
    curl -s -o /dev/null -X POST -H "$TOK" -H "$CT" \
      -d "{\"property_id\":\"prop-00$p\",\"current_rate\":200,\"occupancy_rate\":0.75,\"local_events\":[],\"comp_set_rates\":[195,215],\"season\":\"peak\",\"day_of_week\":\"sat\"}" \
      "$URL/str/act3/price"
  done
done
for i in $(seq 1 8); do
  curl -s -o /dev/null -X POST -H "$TOK" -H "$CT" \
    -d '{"listing_text":"Beach cottage in Oceanside, dog friendly, walk to the strand.","amenities_list":["wifi","parking"],"existing_schema":{},"listing_url":"https://example.com/l"}' \
    "$URL/str/act3/aeo-audit"
done
for p in 1 2 3 4 5 1; do
  curl -s -o /dev/null -X POST -H "$TOK" -H "$CT" \
    -d "{\"guest_context\":\"Is the place dog friendly and is early check-in possible?\",\"property_id\":\"prop-00$p\",\"inquiry_type\":\"general\"}" \
    "$URL/str/act3/guest-comms"
done
echo "=== metrics ==="
curl -s "$URL/str/act3/metrics"
