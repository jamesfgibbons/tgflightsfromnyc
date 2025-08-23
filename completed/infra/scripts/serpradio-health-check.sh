#!/bin/bash

# SERP Radio Health Check Script
# This script checks the health of the SERP Radio API and restarts services if needed

set -euo pipefail

# Configuration
HEALTH_URL="https://api.serpradio.com/health"
DOCKER_COMPOSE_FILE="/opt/serpradio/docker/docker-compose.yml"
LOG_FILE="/var/log/serpradio-health.log"
MAX_RETRIES=3
RETRY_DELAY=10

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if service is healthy
check_health() {
    local url="$1"
    local response
    local http_code
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo -e "\n000")
    http_code=$(echo "$response" | tail -n1)
    
    if [[ "$http_code" == "200" ]]; then
        # Parse JSON response to check status
        local status=$(echo "$response" | head -n -1 | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        if [[ "$status" == "ok" ]]; then
            return 0
        else
            log "WARNING: Health endpoint returned status: $status"
            return 1
        fi
    else
        log "ERROR: Health endpoint returned HTTP $http_code"
        return 1
    fi
}

# Restart Docker services
restart_services() {
    log "Attempting to restart SERP Radio services..."
    
    if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
        cd "$(dirname "$DOCKER_COMPOSE_FILE")"
        
        # Try graceful restart first
        if docker-compose restart python-api publisher; then
            log "Services restarted successfully"
            sleep 30  # Wait for services to start
            return 0
        else
            log "ERROR: Failed to restart services with docker-compose restart"
            
            # Try full recreation if restart fails
            log "Attempting full service recreation..."
            if docker-compose down && docker-compose up -d; then
                log "Services recreated successfully"
                sleep 60  # Wait longer for full startup
                return 0
            else
                log "CRITICAL: Failed to recreate services"
                return 1
            fi
        fi
    else
        log "ERROR: Docker Compose file not found at $DOCKER_COMPOSE_FILE"
        return 1
    fi
}

# Send alert (extend this function for Slack/Discord/email notifications)
send_alert() {
    local message="$1"
    log "ALERT: $message"
    
    # Example: Send to syslog
    logger -t serpradio-health "$message"
    
    # Example: Send to Discord webhook (uncomment and configure)
    # DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK"
    # curl -X POST -H "Content-Type: application/json" \
    #      -d "{\"content\": \"🚨 SERP Radio Alert: $message\"}" \
    #      "$DISCORD_WEBHOOK_URL" 2>/dev/null || true
}

# Main health check logic
main() {
    log "Starting health check..."
    
    local retries=0
    local service_restarted=false
    
    while [[ $retries -lt $MAX_RETRIES ]]; do
        if check_health "$HEALTH_URL"; then
            if [[ $retries -gt 0 ]]; then
                log "Health check passed after $retries retries"
                if [[ "$service_restarted" == "true" ]]; then
                    send_alert "SERP Radio services recovered after restart"
                fi
            else
                log "Health check passed"
            fi
            exit 0
        else
            retries=$((retries + 1))
            log "Health check failed (attempt $retries/$MAX_RETRIES)"
            
            if [[ $retries -lt $MAX_RETRIES ]]; then
                log "Waiting $RETRY_DELAY seconds before retry..."
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    # All retries failed, attempt service restart
    log "All health checks failed, attempting service restart..."
    send_alert "SERP Radio health check failed $MAX_RETRIES times, restarting services"
    
    if restart_services; then
        service_restarted=true
        log "Services restarted, performing final health check..."
        sleep 30  # Wait for services to stabilize
        
        if check_health "$HEALTH_URL"; then
            log "Health check passed after service restart"
            send_alert "SERP Radio services successfully restarted and healthy"
            exit 0
        else
            log "CRITICAL: Health check still failing after service restart"
            send_alert "CRITICAL: SERP Radio services failed to recover after restart"
            exit 1
        fi
    else
        log "CRITICAL: Failed to restart services"
        send_alert "CRITICAL: SERP Radio services could not be restarted"
        exit 1
    fi
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Run main function
main "$@" 