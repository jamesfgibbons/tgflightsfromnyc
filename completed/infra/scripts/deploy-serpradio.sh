#!/bin/bash

# SERP Radio Production Deployment Script
# Run this on your DigitalOcean server (159.223.153.111) as root

set -euo pipefail

# Configuration
DOMAIN="serpradio.com"
API_DOMAIN="api.serpradio.com"
PROJECT_DIR="/opt/serpradio"
NGINX_SITES_DIR="/etc/nginx/sites-available"
NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
EMAIL="admin@serpradio.com"  # Change this to your email

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Update system packages
update_system() {
    log "Updating system packages..."
    apt update && apt upgrade -y
}

# Install required packages
install_packages() {
    log "Installing required packages..."
    apt install -y \
        nginx \
        certbot \
        python3-certbot-nginx \
        docker.io \
        docker-compose-v2 \
        git \
        curl \
        jq \
        ufw \
        fail2ban \
        unattended-upgrades
}

# Configure firewall
setup_firewall() {
    log "Configuring firewall..."
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
    
    # Configure fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
}

# Setup Docker
setup_docker() {
    log "Setting up Docker..."
    systemctl enable docker
    systemctl start docker
    
    # Create docker group and add current user
    groupadd -f docker
    usermod -aG docker $USER
}

# Clone or update project
setup_project() {
    log "Setting up project directory..."
    
    if [[ -d "$PROJECT_DIR" ]]; then
        log "Project directory exists, updating..."
        cd "$PROJECT_DIR"
        git pull origin main
    else
        log "Cloning project..."
        git clone https://github.com/yourusername/serp-loop-radio.git "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
    
    # Set proper permissions
    chown -R root:root "$PROJECT_DIR"
    chmod +x infra/scripts/*.sh
}

# Create production environment file
create_env_file() {
    log "Creating production environment file..."
    
    if [[ ! -f "$PROJECT_DIR/.env.production" ]]; then
        cp "$PROJECT_DIR/env.production.example" "$PROJECT_DIR/.env.production"
        
        # Generate secure tokens
        local live_token=$(openssl rand -hex 32)
        local api_key=$(openssl rand -hex 32)
        
        # Update the environment file
        sed -i "s/LIVE_MODE_TOKEN=.*/LIVE_MODE_TOKEN=${live_token}/" "$PROJECT_DIR/.env.production"
        sed -i "s/VITE_API_KEY=.*/VITE_API_KEY=${api_key}/" "$PROJECT_DIR/.env.production"
        
        warning "Please edit $PROJECT_DIR/.env.production with your DataForSEO credentials"
        warning "DATAFORSEO_LOGIN=your_login"
        warning "DATAFORSEO_PASSWORD=your_password"
    else
        log "Production environment file already exists"
    fi
}

# Setup nginx configuration
setup_nginx() {
    log "Setting up nginx configuration..."
    
    # Copy nginx config
    cp "$PROJECT_DIR/infra/nginx-serpradio.conf" "$NGINX_SITES_DIR/serpradio"
    
    # Create symlink to enable site
    ln -sf "$NGINX_SITES_DIR/serpradio" "$NGINX_ENABLED_DIR/serpradio"
    
    # Remove default site if it exists
    rm -f "$NGINX_ENABLED_DIR/default"
    
    # Test nginx configuration
    nginx -t
    
    # Create web directory for frontend
    mkdir -p /var/www/serpradio
    chown -R www-data:www-data /var/www/serpradio
}

# Setup SSL certificates
setup_ssl() {
    log "Setting up SSL certificates..."
    
    # Stop nginx temporarily
    systemctl stop nginx
    
    # Get certificates for both domains
    certbot certonly --standalone \
        -d "$DOMAIN" \
        -d "$API_DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive
    
    # Start nginx
    systemctl start nginx
    systemctl enable nginx
    
    # Test auto-renewal
    certbot renew --dry-run
}

# Setup systemd health monitoring
setup_health_monitoring() {
    log "Setting up health monitoring..."
    
    # Copy systemd files
    cp "$PROJECT_DIR/infra/systemd/serpradio-health.service" /etc/systemd/system/
    cp "$PROJECT_DIR/infra/systemd/serpradio-health.timer" /etc/systemd/system/
    
    # Copy health check script
    cp "$PROJECT_DIR/infra/scripts/serpradio-health-check.sh" /usr/local/bin/
    chmod +x /usr/local/bin/serpradio-health-check.sh
    
    # Update paths in health check script
    sed -i "s|/opt/serpradio|$PROJECT_DIR|g" /usr/local/bin/serpradio-health-check.sh
    
    # Enable and start timer
    systemctl daemon-reload
    systemctl enable serpradio-health.timer
    systemctl start serpradio-health.timer
    
    log "Health monitoring timer started"
}

# Start Docker services
start_services() {
    log "Starting Docker services..."
    
    cd "$PROJECT_DIR"
    
    # Build and start services
    docker compose -f docker/docker-compose.yml up -d --build
    
    # Wait for services to start
    sleep 30
    
    # Check service health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "Services started successfully"
    else
        error "Services failed to start properly"
        docker compose -f docker/docker-compose.yml logs
        exit 1
    fi
}

# Setup log rotation
setup_log_rotation() {
    log "Setting up log rotation..."
    
    cat > /etc/logrotate.d/serpradio << EOF
/var/log/serpradio-health.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
}

/var/log/nginx/serpradio.*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload nginx
    endscript
}
EOF
}

# Setup automatic updates
setup_auto_updates() {
    log "Setting up automatic security updates..."
    
    # Configure unattended upgrades
    cat > /etc/apt/apt.conf.d/20auto-upgrades << EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
    
    # Configure what to upgrade
    sed -i 's|//      "origin=Debian,codename=${distro_codename}-updates";|        "origin=Debian,codename=${distro_codename}-updates";|' /etc/apt/apt.conf.d/50unattended-upgrades
}

# Run validation tests
run_validation() {
    log "Running validation tests..."
    
    # Test health endpoint
    if curl -f http://localhost:8000/health | jq '.status' | grep -q "ok"; then
        log "✅ Health endpoint working"
    else
        error "❌ Health endpoint failed"
    fi
    
    # Test SSL certificates
    if openssl s_client -connect "$API_DOMAIN:443" -servername "$API_DOMAIN" < /dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
        log "✅ SSL certificate valid"
    else
        warning "⚠️ SSL certificate validation failed"
    fi
    
    # Test Docker services
    if docker ps | grep -q "serp-api"; then
        log "✅ Docker services running"
    else
        error "❌ Docker services not running"
    fi
    
    # Test health monitoring
    if systemctl is-active --quiet serpradio-health.timer; then
        log "✅ Health monitoring active"
    else
        error "❌ Health monitoring not active"
    fi
}

# Display final instructions
show_final_instructions() {
    log "🎉 Deployment completed successfully!"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Edit production environment file:"
    echo "   nano $PROJECT_DIR/.env.production"
    echo ""
    echo "2. Add your DataForSEO credentials:"
    echo "   DATAFORSEO_LOGIN=your_login"
    echo "   DATAFORSEO_PASSWORD=your_password"
    echo ""
    echo "3. Restart services after editing .env:"
    echo "   cd $PROJECT_DIR && docker compose -f docker/docker-compose.yml restart"
    echo ""
    echo "4. Upload your frontend build:"
    echo "   Upload ui/dist/* to /var/www/serpradio/"
    echo ""
    echo -e "${GREEN}Your SERP Radio is now available at:${NC}"
    echo "   🌐 Frontend: https://$DOMAIN"
    echo "   🔌 API: https://$API_DOMAIN"
    echo "   📊 Health: https://$API_DOMAIN/health"
    echo ""
    echo -e "${YELLOW}Monitor your deployment:${NC}"
    echo "   📋 Logs: journalctl -fu docker-compose@serpradio"
    echo "   🔍 Health: tail -f /var/log/serpradio-health.log"
    echo "   📈 Nginx: tail -f /var/log/nginx/serpradio.access.log"
}

# Main deployment function
main() {
    log "🚀 Starting SERP Radio Production Deployment"
    echo "Domain: $DOMAIN"
    echo "API Domain: $API_DOMAIN"
    echo "Project Directory: $PROJECT_DIR"
    echo ""
    
    check_root
    update_system
    install_packages
    setup_firewall
    setup_docker
    setup_project
    create_env_file
    setup_nginx
    setup_ssl
    setup_health_monitoring
    setup_log_rotation
    setup_auto_updates
    start_services
    run_validation
    show_final_instructions
    
    log "🎵 SERP Radio deployment complete!"
}

# Run main function
main "$@" 