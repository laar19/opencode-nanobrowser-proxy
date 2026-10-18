#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

sed "s|%h/opencode-proxy|$DIR|g" "$DIR/opencode-proxy.service" > "$SERVICE_DIR/opencode-proxy.service"

systemctl --user daemon-reload
systemctl --user enable opencode-proxy.service
systemctl --user start opencode-proxy.service

echo "OpenCode Proxy installed and started as a systemd user service!"
echo "Check status with: systemctl --user status opencode-proxy.service"
