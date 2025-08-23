#!/usr/bin/env bash
set -e
echo "🛠  Copying iframe files…"
mkdir -p /opt/serpradio/iframe
cp -r iframe/* /opt/serpradio/iframe/
echo "🔄  Enabling nginx location…"
IFCONF=/etc/nginx/snippets/serpradio_iframe.conf
cp infra/nginx/serpradio_iframe.conf $IFCONF
grep -q "include snippets/serpradio_iframe.conf" /etc/nginx/sites-enabled/serpradio \
  || sed -i '/server_name/a \    include snippets/serpradio_iframe.conf;' /etc/nginx/sites-enabled/serpradio
nginx -t && systemctl reload nginx
echo "✅  iframe live at https://api.serpradio.com/iframe/" 