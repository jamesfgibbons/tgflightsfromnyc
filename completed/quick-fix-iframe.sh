#!/bin/bash
# Quick fix for 502 iframe error
# Run this on your production server

set -e
echo "🔧 Fixing SERP Radio iframe 502 error..."

# 1. Create iframe directory and files
echo "📁 Creating iframe files..."
mkdir -p /opt/serpradio/iframe

# 2. Create the iframe index.html
cat > /opt/serpradio/iframe/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SERP Radio Embed</title>
<style>html,body{margin:0;height:100%}iframe{border:none;width:100%;height:100%;}</style>
</head>
<body>
<iframe
   src="/widget/"
   sandbox="allow-scripts allow-same-origin allow-forms allow-downloads"
   referrerpolicy="strict-origin"
   allow="autoplay"
></iframe>
</body>
</html>
EOF

# 3. Set proper permissions
chmod 644 /opt/serpradio/iframe/index.html

# 4. Create nginx snippet
echo "⚙️  Configuring nginx..."
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

# 5. Add include to main nginx config
echo "🔗 Adding nginx include..."
if ! grep -q "snippets/serpradio_iframe.conf" /etc/nginx/sites-enabled/serpradio; then
    # Find the line with server_name and add include after it
    sed -i '/server_name.*api\.serpradio\.com/a\    include snippets/serpradio_iframe.conf;' /etc/nginx/sites-enabled/serpradio
    echo "✅ Added include directive"
else
    echo "✅ Include directive already exists"
fi

# 6. Test nginx config
echo "🧪 Testing nginx configuration..."
if nginx -t; then
    echo "✅ Nginx config is valid"
else
    echo "❌ Nginx config has errors!"
    exit 1
fi

# 7. Reload nginx
echo "🔄 Reloading nginx..."
systemctl reload nginx

# 8. Verify setup
echo "🔍 Verifying setup..."
if [ -f /opt/serpradio/iframe/index.html ]; then
    echo "✅ Iframe file exists"
else
    echo "❌ Iframe file missing!"
fi

if [ -f /etc/nginx/snippets/serpradio_iframe.conf ]; then
    echo "✅ Nginx snippet exists"
else
    echo "❌ Nginx snippet missing!"
fi

echo ""
echo "🎉 Iframe fix complete!"
echo "🌐 Test: curl -I https://api.serpradio.com/iframe/"
echo "🖥️  Visit: https://api.serpradio.com/iframe/"
echo "" 