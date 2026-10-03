#!/usr/bin/env bash
# Shared steps for the distribution installers.
set -euo pipefail

PACKAGING="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$PACKAGING")"
BUILD="$ROOT/build"
RUNTIME="$BUILD/runtime"
SHARE="/usr/share/nahimic-linux"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

require_commands() {
    local missing=()
    for command in "$@"; do
        command -v "$command" >/dev/null 2>&1 || missing+=("$command")
    done
    [ "${#missing[@]}" -eq 0 ] || die "missing commands: ${missing[*]}"
}

install_dependencies() {
    if [ "${SKIP_DEPS:-0}" = "1" ]; then
        log "Skipping dependency installation"
        return
    fi
    "$@"
}

fetch_runtime() {
    log "Fetching and verifying the runtime components"
    python3 "$PACKAGING/fetch_runtime.py" --output "$RUNTIME"
}

build_host() {
    log "Building the Windows host binaries"
    make -C "$ROOT" -j"$(nproc)"
}

install_tree() {
    log "Installing into /usr"
    sudo make -C "$ROOT" install
    sudo install -d "$SHARE"
    sudo cp -r "$RUNTIME/vendor" "$RUNTIME/factory" "$SHARE/"
}

activate_sessions() {
    log "Enabling the user service and activating running sessions"
    systemctl --user daemon-reload || true
    systemctl --user enable --now nahimic.service || true
    local bus uid user
    for bus in /run/user/[0-9]*/bus; do
        [[ -S "$bus" ]] || continue
        uid="${bus#/run/user/}"; uid="${uid%/bus}"
        (( uid >= 1000 )) || continue
        user="$(getent passwd "$uid" | cut -d: -f1)"
        [[ -n "$user" ]] || continue
        sudo -u "$user" env XDG_RUNTIME_DIR="/run/user/$uid" \
            DBUS_SESSION_BUS_ADDRESS="unix:path=$bus" \
            /usr/bin/nahimic --activate ||
            echo "nahimic: open the application to see the setup error."
    done
}

verify_runtime() {
    log "Checking the audio stack"
    command -v pactl >/dev/null 2>&1 || die "PipeWire tools are missing"
    pactl list sinks 2>/dev/null | grep -q "alsa.components" ||
        die "no usable sink found; start PipeWire and choose an output first"
    log "Supported speaker entries:"
    python3 - "$ROOT" <<'PY' || true
import json, sys
from pathlib import Path
table = json.loads((Path(sys.argv[1]) / "host" / "devices.json").read_text())
for entry in table["devices"]:
    print(f"  {entry['codec']}:{entry.get('subsystem') or '*'}  {entry['name']}")
PY
}