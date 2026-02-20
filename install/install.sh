#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Phobos installer
# Usage: sudo ./install.sh [install_dir]
# Default install dir: /opt/phobos
# ---------------------------------------------------------------------------

INSTALL_DIR="${1:-/opt/phobos}"
SERVICE_USER="phobos"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
UV_BIN="$(command -v uv || true)"
PYTHON_TARGET="3.14"

# Re-exec with sudo if not root
if [[ "$EUID" -ne 0 ]]; then
    echo "Requesting sudo for installation..."
    exec sudo "$SCRIPT_DIR/install.sh" "$@"
fi

echo "==> Installing Phobos to $INSTALL_DIR"

if [[ -z "$UV_BIN" ]]; then
    echo "ERROR: uv is not installed or not on PATH."
    exit 1
fi

# Precondition: config.yaml must exist
if [[ ! -f "$SOURCE_DIR/config.yaml" ]]; then
    echo "ERROR: $SOURCE_DIR/config.yaml not found."
    echo "Copy config.example.yaml to config.yaml and fill in your credentials first."
    exit 1
fi

# Create unprivileged system user if it doesn't exist
if id "$SERVICE_USER" &>/dev/null; then
    echo "==> User '$SERVICE_USER' already exists, skipping creation"
else
    echo "==> Creating system user '$SERVICE_USER'"
    useradd \
        --system \
        --no-create-home \
        --shell /usr/sbin/nologin \
        "$SERVICE_USER"
fi

# Create install directory and hand it to the service user before running uv.
# All uv/playwright commands run as $SERVICE_USER so tooling cache, venv, and
# browser binaries are written with the correct ownership from the start.
mkdir -p "$INSTALL_DIR"

# Copy project files (exclude dev/build artifacts)
echo "==> Copying project files to $INSTALL_DIR"
rsync -a \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.venv' \
    --exclude='tests/' \
    --exclude='docs/' \
    --exclude='install/' \
    --exclude='cache/' \
    "$SOURCE_DIR/" "$INSTALL_DIR/"

# Give the service user ownership before running any uv commands so that
# all cache, venv, and browser files are written as $SERVICE_USER, not root.
echo "==> Setting ownership to $SERVICE_USER:$SERVICE_USER"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# Protect config.yaml (contains credentials)
chmod 600 "$INSTALL_DIR/config.yaml"

# Helper: run a command as the service user inside the install dir.
run_as_service_user() {
    sudo -u "$SERVICE_USER" \
        env HOME="$INSTALL_DIR" \
            PLAYWRIGHT_BROWSERS_PATH="$INSTALL_DIR/pw-browsers" \
        "$@"
}

echo "==> Installing Python $PYTHON_TARGET"
run_as_service_user \
    "$UV_BIN" python install \
        --install-dir "$INSTALL_DIR/.uv/python" \
        "$PYTHON_TARGET"

PYTHON_BIN="$(find "$INSTALL_DIR/.uv/python" -path "*/bin/python$PYTHON_TARGET" -type f | head -n 1)"
if [[ -z "$PYTHON_BIN" ]]; then
    echo "ERROR: could not locate installed Python $PYTHON_TARGET under $INSTALL_DIR/.uv/python"
    exit 1
fi

echo "==> Building virtual environment"
run_as_service_user \
    "$UV_BIN" sync --python "$PYTHON_BIN" --project "$INSTALL_DIR"

# Install Playwright browser into the install dir so the service user can execute it.
echo "==> Installing Playwright Chromium browser"
run_as_service_user \
    "$UV_BIN" run --project "$INSTALL_DIR" playwright install chromium

# Install systemd units (substitute install dir placeholder)
echo "==> Installing systemd units"
sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" \
    "$SCRIPT_DIR/phobos.service" \
    > /etc/systemd/system/phobos.service

cp "$SCRIPT_DIR/phobos.timer" /etc/systemd/system/phobos.timer

systemctl daemon-reload
systemctl enable --now phobos.timer

echo ""
echo "==> Phobos installed successfully!"
echo "    Install dir : $INSTALL_DIR"
echo "    Service user: $SERVICE_USER"
echo "    Timer status:"
systemctl status phobos.timer --no-pager || true
