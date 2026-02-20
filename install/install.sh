#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${1:-/opt/phobos}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

[[ "$EUID" -ne 0 ]] && { echo "Run as root: sudo $0"; exit 1; }
[[ ! -f "$SOURCE_DIR/config.yaml" ]] && { echo "ERROR: config.yaml not found. Copy config.example.yaml and fill in credentials."; exit 1; }

echo "==> Installing Phobos to $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"
cp -a "$SOURCE_DIR/." "$INSTALL_DIR/"
rm -rf "$INSTALL_DIR/.git" "$INSTALL_DIR/__pycache__" "$INSTALL_DIR/.venv" "$INSTALL_DIR/cache" "$INSTALL_DIR/tests"
chmod 600 "$INSTALL_DIR/config.yaml"

cd "$INSTALL_DIR"
uv python install 3.14
uv sync
PLAYWRIGHT_BROWSERS_PATH="$INSTALL_DIR/pw-browsers" uv run playwright install --with-deps chromium

sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" "$SCRIPT_DIR/phobos.service" > /etc/systemd/system/phobos.service
cp "$SCRIPT_DIR/phobos.timer" /etc/systemd/system/phobos.timer
systemctl daemon-reload
systemctl enable --now phobos.timer

echo "==> Done. Timer status:"
systemctl status phobos.timer --no-pager || true
