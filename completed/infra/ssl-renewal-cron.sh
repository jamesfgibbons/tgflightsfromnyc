#!/bin/bash
# SSL Certificate Auto-Renewal Script for SERP Radio
# Add this to root's crontab: 0 3 * * * /path/to/ssl-renewal-cron.sh

# Set paths
CERTBOT_PATH="/usr/bin/certbot"
NGINX_SERVICE="nginx"
LOG_FILE="/var/log/serpradio-ssl-renewal.log"
DOMAIN="api.serpradio.com"

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Start renewal process
log_message "Starting SSL certificate renewal check"

# Check if certbot is available
if [ ! -f "$CERTBOT_PATH" ]; then
    log_message "ERROR: certbot not found at $CERTBOT_PATH"
    exit 1
fi

# Check certificate expiration (renew if less than 30 days)
EXPIRY_DAYS=$($CERTBOT_PATH certificates 2>/dev/null | grep -A 1 "$DOMAIN" | grep "VALID" | grep -o "[0-9]\+ days" | grep -o "[0-9]\+")

if [ -n "$EXPIRY_DAYS" ] && [ "$EXPIRY_DAYS" -lt 30 ]; then
    log_message "Certificate expires in $EXPIRY_DAYS days, attempting renewal"
    
    # Attempt renewal
    if $CERTBOT_PATH renew --quiet --nginx --post-hook "systemctl reload $NGINX_SERVICE"; then
        log_message "SUCCESS: Certificate renewed successfully"
        
        # Test nginx configuration
        if nginx -t 2>/dev/null; then
            log_message "SUCCESS: Nginx configuration test passed"
        else
            log_message "WARNING: Nginx configuration test failed after renewal"
        fi
        
        # Check if SERP Radio API is responding
        if curl -sf "https://$DOMAIN/health" >/dev/null; then
            log_message "SUCCESS: SERP Radio API responding after renewal"
        else
            log_message "WARNING: SERP Radio API not responding after renewal"
        fi
        
    else
        log_message "ERROR: Certificate renewal failed"
        exit 1
    fi
else
    log_message "Certificate is valid for $EXPIRY_DAYS days, no renewal needed"
fi

# Cleanup old log entries (keep last 100 lines)
tail -n 100 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

log_message "SSL renewal check completed" 