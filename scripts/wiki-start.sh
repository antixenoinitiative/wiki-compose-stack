#!/bin/sh
set -eu
test -s /branding/current/axi_logo_new2.ico
ln -sf /branding/current/axi_logo_new2.ico /wiki/assets/favicon.ico
for size in 16 32; do
  ln -sf "/branding/current/axi_logo_new2_${size}x${size}.png" "/wiki/assets/favicons/favicon-${size}x${size}.png"
done
for size in 192 256; do
  ln -sf "/branding/current/axi_logo_new2_${size}x${size}.png" "/wiki/assets/favicons/android-chrome-${size}x${size}.png"
done
ln -sf /branding/current/axi_logo_new2_150x150.png /wiki/assets/favicons/mstile-150x150.png
ln -sf /branding/current/axi_logo_new2_180x180.png /wiki/assets/favicons/apple-touch-icon.png
cd /wiki
exec node server
