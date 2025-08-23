#!/bin/bash

# SERP Radio Backend Smoke Tests
# Validates critical API endpoints and functionality

set -e  # Exit on any error

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_SECRET="${ADMIN_SECRET:-dev-secret}"
TIMEOUT=30
POLL_INTERVAL=2
MAX_POLLS=15

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "Running test: $test_name"
    
    if eval "$test_command"; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_success "✓ $test_name"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "✗ $test_name"
        return 1
    fi
}

# Helper function to extract JSON field
extract_json() {
    python3 -c "import json, sys; print(json.load(sys.stdin)['$1'])" 2>/dev/null || echo ""
}

# Test 1: Health Check
test_health() {
    local response=$(curl -s -f "${BASE_URL}/api/healthz" || return 1)
    local status=$(echo "$response" | extract_json "status")
    
    if [[ "$status" == "healthy" ]]; then
        log_info "Health check passed: $status"
        return 0
    else
        log_error "Health check failed: $response"
        return 1
    fi
}

# Test 2: Create Demo Sonification
test_demo_sonification() {
    local payload='{
        "tenant": "smoke-test",
        "source": "demo", 
        "sound_pack": "Arena Rock",
        "seed": 42,
        "override_metrics": {
            "ctr": 0.75,
            "position": 0.8,
            "clicks": 0.7,
            "impressions": 0.6
        }
    }'
    
    local response=$(curl -s -f -X POST "${BASE_URL}/api/demo" \
        -H "Content-Type: application/json" \
        -d "$payload" || return 1)
    
    DEMO_JOB_ID=$(echo "$response" | extract_json "job_id")
    
    if [[ -n "$DEMO_JOB_ID" ]]; then
        log_info "Demo job created: $DEMO_JOB_ID"
        return 0
    else
        log_error "Demo creation failed: $response"
        return 1
    fi
}

# Test 3: Poll Job Status
test_poll_job() {
    if [[ -z "$DEMO_JOB_ID" ]]; then
        log_error "No job ID to poll"
        return 1
    fi
    
    local polls=0
    local status=""
    
    log_info "Polling job status (max ${MAX_POLLS} attempts)..."
    
    while [[ $polls -lt $MAX_POLLS ]]; do
        local response=$(curl -s -f "${BASE_URL}/api/jobs/${DEMO_JOB_ID}" || return 1)
        status=$(echo "$response" | extract_json "status")
        
        log_info "Poll $((polls + 1)): Status = $status"
        
        if [[ "$status" == "done" ]]; then
            # Extract additional info
            local sound_pack=$(echo "$response" | extract_json "sound_pack")
            local duration=$(echo "$response" | extract_json "duration_sec")
            
            log_success "Job completed successfully"
            log_info "Sound pack: $sound_pack"
            log_info "Duration: ${duration}s"
            
            # Store MP3 URL for later tests
            DEMO_MP3_URL=$(echo "$response" | extract_json "mp3_url")
            return 0
        elif [[ "$status" == "error" ]]; then
            local error_id=$(echo "$response" | extract_json "error_id")
            log_error "Job failed with error: $error_id"
            return 1
        fi
        
        polls=$((polls + 1))
        sleep $POLL_INTERVAL
    done
    
    log_error "Job polling timed out after $((MAX_POLLS * POLL_INTERVAL)) seconds"
    return 1
}

# Test 4: Test Share Functionality
test_share_creation() {
    if [[ -z "$DEMO_JOB_ID" ]]; then
        log_error "No job ID to share"
        return 1
    fi
    
    local response=$(curl -s -f -X POST "${BASE_URL}/api/share/${DEMO_JOB_ID}" || return 1)
    SHARE_TOKEN=$(echo "$response" | extract_json "share_token")
    
    if [[ -n "$SHARE_TOKEN" ]]; then
        log_success "Share token created: $SHARE_TOKEN"
        return 0
    else
        log_error "Share creation failed: $response"
        return 1
    fi
}

# Test 5: Test Share Access
test_share_access() {
    if [[ -z "$SHARE_TOKEN" ]]; then
        log_error "No share token to test"
        return 1
    fi
    
    local response=$(curl -s -f "${BASE_URL}/api/share/${SHARE_TOKEN}" || return 1)
    local status=$(echo "$response" | extract_json "status")
    local sound_pack=$(echo "$response" | extract_json "sound_pack")
    
    if [[ "$status" == "done" && -n "$sound_pack" ]]; then
        log_success "Share access successful: $sound_pack"
        return 0
    else
        log_error "Share access failed: $response"
        return 1
    fi
}

# Test 6: Hero Status
test_hero_status() {
    local response=$(curl -s -f "${BASE_URL}/api/hero-status" || return 1)
    
    # Check if response contains pack information
    if echo "$response" | grep -q "Arena Rock" && echo "$response" | grep -q "packs"; then
        log_success "Hero status retrieved successfully"
        return 0
    else
        log_error "Hero status failed: $response"
        return 1
    fi
}

# Test 7: Admin Hero Render (if admin secret available)
test_hero_render() {
    if [[ -z "$ADMIN_SECRET" ]]; then
        log_warning "Skipping hero render test (no admin secret)"
        return 0
    fi
    
    local response=$(curl -s -f -X POST "${BASE_URL}/api/render-hero" \
        -H "X-Admin-Secret: $ADMIN_SECRET" \
        -d "sound_pack=Arena Rock" || return 1)
    
    local job_id=$(echo "$response" | extract_json "job_id")
    
    if [[ -n "$job_id" ]]; then
        log_success "Hero render started: $job_id"
        return 0
    else
        log_error "Hero render failed: $response"
        return 1
    fi
}

# Test 8: Preview Endpoint
test_preview() {
    local payload='{
        "tenant": "smoke-preview",
        "source": "demo",
        "sound_pack": "Synthwave", 
        "total_bars": 8,
        "override_metrics": {
            "ctr": 0.6,
            "position": 0.7
        }
    }'
    
    local response=$(curl -s -f -X POST "${BASE_URL}/api/preview" \
        -H "Content-Type: application/json" \
        -d "$payload" || return 1)
    
    local status=$(echo "$response" | extract_json "status")
    local sound_pack=$(echo "$response" | extract_json "sound_pack")
    
    if [[ "$status" == "done" && "$sound_pack" == "Synthwave" ]]; then
        log_success "Preview generated successfully"
        return 0
    else
        log_error "Preview failed: $response"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting SERP Radio Backend Smoke Tests"
    log_info "Base URL: $BASE_URL"
    log_info "Timeout: ${TIMEOUT}s"
    echo
    
    # Run all tests
    run_test "Health Check" "test_health"
    run_test "Demo Sonification" "test_demo_sonification" 
    run_test "Job Polling" "test_poll_job"
    run_test "Share Creation" "test_share_creation"
    run_test "Share Access" "test_share_access"
    run_test "Hero Status" "test_hero_status"
    run_test "Hero Render (Admin)" "test_hero_render"
    run_test "Preview Endpoint" "test_preview"
    
    # Summary
    echo
    echo "========================================"
    log_info "SMOKE TEST SUMMARY"
    echo "========================================"
    log_info "Tests run: $TESTS_RUN"
    log_success "Passed: $TESTS_PASSED"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Failed: $TESTS_FAILED"
        echo
        log_error "Some tests failed. Check the output above for details."
        exit 1
    else
        echo
        log_success "All tests passed! 🎉"
        log_info "Backend is ready for staging deployment."
        exit 0
    fi
}

# Check dependencies
if ! command -v curl &> /dev/null; then
    log_error "curl is required but not installed"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    log_error "python3 is required but not installed"
    exit 1
fi

# Run main function
main "$@"