# 🔧 Debug SERP Radio Iframe 502 Error

## Problem: 502 Error at https://api.serpradio.com/iframe/

A 502 error means nginx can't find the iframe files or there's a configuration issue.

## Step-by-Step Debugging:

### 1. Check if files exist on server
```bash
ssh root@your-server
ls -la /opt/serpradio/iframe/
# Should show: index.html
```

### 2. Check nginx snippet exists
```bash
ls -la /etc/nginx/snippets/serpradio_iframe.conf
# Should exist and contain location block
cat /etc/nginx/snippets/serpradio_iframe.conf
```

### 3. Check nginx site includes snippet
```bash
grep -n "serpradio_iframe" /etc/nginx/sites-enabled/serpradio
# Should show: include snippets/serpradio_iframe.conf;
```

### 4. Test nginx configuration
```bash
nginx -t
# Should show: syntax is ok, test is successful
```

### 5. Check nginx error logs
```bash
tail -f /var/log/nginx/error.log
# Then try accessing https://api.serpradio.com/iframe/ in browser
```

## Quick Fix Commands:

### If files are missing:
```bash
# On your local machine:
scp -r iframe/ root@your-server:/opt/serpradio/
ssh root@your-server "chmod -R 644 /opt/serpradio/iframe/*"
```

### If nginx snippet is missing:
```bash
# On server:
mkdir -p /etc/nginx/snippets
cat > /etc/nginx/snippets/serpradio_iframe.conf << 'EOF'
location /iframe/ {
    alias /opt/serpradio/iframe/;
    index index.html;
    add_header X-Frame-Options "ALLOWALL";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; connect-src https://api.serpradio.com wss://api.serpradio.com; frame-ancestors *;";
}
EOF
```

### If include directive is missing:
```bash
# Check current nginx config:
cat /etc/nginx/sites-enabled/serpradio

# Add include line after server_name:
sed -i '/server_name api.serpradio.com;/a\    include snippets/serpradio_iframe.conf;' /etc/nginx/sites-enabled/serpradio
```

### Test and reload:
```bash
nginx -t && systemctl reload nginx
```

## Alternative: Manual nginx config

If the snippet approach doesn't work, add directly to your main nginx config:

```nginx
server {
    listen 443 ssl http2;
    server_name api.serpradio.com;
    
    # ... existing SSL config ...
    
    # Add this location block:
    location /iframe/ {
        alias /opt/serpradio/iframe/;
        index index.html;
        try_files $uri $uri/ =404;
        add_header X-Frame-Options "ALLOWALL";
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; connect-src https://api.serpradio.com wss://api.serpradio.com; frame-ancestors *;";
    }
    
    # ... rest of config ...
}
```

## Verification:

Once fixed, these should work:
```bash
# Check file is served:
curl -I https://api.serpradio.com/iframe/
# Should return: HTTP/2 200

# Check content:
curl -s https://api.serpradio.com/iframe/ | head -5
# Should show: <!DOCTYPE html>
```

## Common Issues:

1. **Permissions**: Files need to be readable by nginx (644)
2. **Path**: Must be `/opt/serpradio/iframe/index.html` exactly
3. **Include**: The include directive must be inside the server block
4. **SSL**: Make sure it's in the HTTPS server block, not HTTP

## Full Deployment Script:

Run this on your server to ensure everything is set up:

```bash
#!/bin/bash
set -e

# Create directory and copy files
mkdir -p /opt/serpradio/iframe
# (Copy iframe/index.html to this location)

# Create nginx snippet
mkdir -p /etc/nginx/snippets
cat > /etc/nginx/snippets/serpradio_iframe.conf << 'EOF'
location /iframe/ {
    alias /opt/serpradio/iframe/;
    index index.html;
    try_files $uri $uri/ =404;
    add_header X-Frame-Options "ALLOWALL";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; connect-src https://api.serpradio.com wss://api.serpradio.com; frame-ancestors *;";
}
EOF

# Add include to nginx config if not present
if ! grep -q "snippets/serpradio_iframe.conf" /etc/nginx/sites-enabled/serpradio; then
    sed -i '/server_name api.serpradio.com;/a\    include snippets/serpradio_iframe.conf;' /etc/nginx/sites-enabled/serpradio
fi

# Test and reload
nginx -t && systemctl reload nginx

echo "✅ Iframe should now be live at https://api.serpradio.com/iframe/"
``` 