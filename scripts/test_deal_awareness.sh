#!/usr/bin/env bash
#
# Test Deal Awareness Feature End-to-End
#
# Usage:
#   ./scripts/test_deal_awareness.sh [BASE_URL]
#
# Example:
#   ./scripts/test_deal_awareness.sh https://your-service.up.railway.app
#

set -euo pipefail

# Configuration
BASE="${1:-http://localhost:8000}"
ROUTES=(
  "JFK:MIA:3"
  "JFK:LAX:6"
  "EWR:LAS:4"
  "LGA:MCO:7"
)

echo "🧪 Testing Deal Awareness Feature"
echo "Base URL: $BASE"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASS=0
FAIL=0

# Helper: Test a single endpoint
test_endpoint() {
  local name="$1"
  local url="$2"
  local expected_status="${3:-200}"

  echo -n "Testing $name... "

  response=$(curl -s -w "\n%{http_code}" "$url")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [ "$http_code" = "$expected_status" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
    ((PASS++))
    return 0
  else
    echo -e "${RED}✗ FAIL${NC} (HTTP $http_code, expected $expected_status)"
    echo "Response: $body"
    ((FAIL++))
    return 1
  fi
}

# Helper: Test JSON field exists
test_json_field() {
  local name="$1"
  local json="$2"
  local field="$3"

  echo -n "  Checking field '$field'... "

  if echo "$json" | jq -e ".$field" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    return 0
  else
    echo -e "${RED}✗ Missing${NC}"
    return 1
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_endpoint "Deals API Health" "$BASE/api/deals/health" 200
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Evaluate Deal (Single Route)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test JFK → MIA for March
URL="$BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=3&cabin=economy"
echo "Testing: $URL"
echo ""

response=$(curl -s "$URL")
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$http_code" = "200" ]; then
  echo -e "${GREEN}✓ Request succeeded${NC}"
  ((PASS++))

  # Check required fields
  test_json_field "Response" "$response" "has_data"
  test_json_field "Response" "$response" "origin"
  test_json_field "Response" "$response" "dest"
  test_json_field "Response" "$response" "month"

  # Check if has_data is true
  has_data=$(echo "$response" | jq -r '.has_data')

  if [ "$has_data" = "true" ]; then
    echo ""
    echo -e "${GREEN}✓ Deal data available${NC}"

    # Extract key fields
    recommendation=$(echo "$response" | jq -r '.recommendation')
    confidence=$(echo "$response" | jq -r '.confidence')
    current_price=$(echo "$response" | jq -r '.current_price')
    delta_pct=$(echo "$response" | jq -r '.delta_pct')
    deal_score=$(echo "$response" | jq -r '.deal_score')

    # Display results
    echo ""
    echo "Results:"
    echo "  Recommendation: $recommendation"
    echo "  Confidence: $confidence%"
    echo "  Current Price: \$$current_price"
    echo "  Delta vs Median: ${delta_pct}%"
    echo "  Deal Score: $deal_score/100"

    # Check baseline
    p50=$(echo "$response" | jq -r '.baseline.p50')
    samples=$(echo "$response" | jq -r '.baseline.samples')
    echo "  Baseline Median: \$$p50 ($samples samples)"

    # Check sweet spot
    sweet_spot=$(echo "$response" | jq -r '.sweet_spot')
    if [ "$sweet_spot" != "null" ]; then
      min_days=$(echo "$response" | jq -r '.sweet_spot.min_days')
      max_days=$(echo "$response" | jq -r '.sweet_spot.max_days')
      echo "  Sweet Spot: ${min_days}-${max_days} days before departure"
    else
      echo "  Sweet Spot: Not available"
    fi

    # Validate recommendation is one of BUY/TRACK/WAIT
    if [[ "$recommendation" =~ ^(BUY|TRACK|WAIT)$ ]]; then
      echo -e "${GREEN}✓ Valid recommendation: $recommendation${NC}"
      ((PASS++))
    else
      echo -e "${RED}✗ Invalid recommendation: $recommendation${NC}"
      ((FAIL++))
    fi

  else
    message=$(echo "$response" | jq -r '.message')
    echo -e "${YELLOW}⚠ No data available: $message${NC}"
    echo "This is expected if database is not yet seeded."
  fi

else
  echo -e "${RED}✗ Request failed (HTTP $http_code)${NC}"
  ((FAIL++))
fi

echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Batch Evaluate (Multiple Routes)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

batch_payload=$(cat <<EOF
{
  "routes": [
    {"origin": "JFK", "dest": "MIA", "month": 3},
    {"origin": "JFK", "dest": "LAX", "month": 6},
    {"origin": "EWR", "dest": "LAS", "month": 4}
  ]
}
EOF
)

URL="$BASE/api/deals/batch"
echo "Testing: $URL"
echo "Payload: $batch_payload"
echo ""

response=$(curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "$batch_payload")

http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "$batch_payload")

if [ "$http_code" = "200" ]; then
  echo -e "${GREEN}✓ Batch request succeeded${NC}"
  ((PASS++))

  # Count results
  count=$(echo "$response" | jq '. | length')
  echo "Received $count evaluations"

  # Check each result
  for i in $(seq 0 $((count - 1))); do
    route=$(echo "$response" | jq -r ".[$i] | \"\(.origin)→\(.dest)\"")
    rec=$(echo "$response" | jq -r ".[$i].recommendation // \"N/A\"")
    has_data=$(echo "$response" | jq -r ".[$i].has_data")

    if [ "$has_data" = "true" ]; then
      echo -e "  ${GREEN}✓${NC} $route: $rec"
    else
      echo -e "  ${YELLOW}⚠${NC} $route: No data"
    fi
  done

  ((PASS++))
else
  echo -e "${RED}✗ Batch request failed (HTTP $http_code)${NC}"
  echo "Response: $response"
  ((FAIL++))
fi

echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Error Handling"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test invalid month
URL="$BASE/api/deals/evaluate?origin=JFK&dest=MIA&month=13"
echo "Testing invalid month (13)..."
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$http_code" = "422" ]; then
  echo -e "${GREEN}✓ Correctly rejected invalid month${NC}"
  ((PASS++))
else
  echo -e "${RED}✗ Should return 422 for invalid month (got $http_code)${NC}"
  ((FAIL++))
fi

# Test invalid airport code
URL="$BASE/api/deals/evaluate?origin=JFK&dest=INVALID&month=3"
echo "Testing invalid destination code..."
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

if [ "$http_code" = "422" ] || [ "$http_code" = "200" ]; then
  echo -e "${GREEN}✓ Handled invalid destination${NC}"
  ((PASS++))
else
  echo -e "${RED}✗ Unexpected response: $http_code${NC}"
  ((FAIL++))
fi

echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total Tests: $((PASS + FAIL))"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}✓ All tests passed!${NC}"
  echo ""
  echo "Next steps:"
  echo "1. Seed database with price observations"
  echo "2. Refresh materialized view: REFRESH MATERIALIZED VIEW route_baseline_30d;"
  echo "3. Test again to see deal recommendations with real data"
  exit 0
else
  echo -e "${RED}✗ Some tests failed${NC}"
  echo ""
  echo "Common issues:"
  echo "- Database not seeded with price_observation data"
  echo "- Materialized view route_baseline_30d not refreshed"
  echo "- SUPABASE_URL or SUPABASE_SERVICE_ROLE not configured"
  exit 1
fi
