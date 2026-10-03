#!/usr/bin/env bash
# Install Nahimic Linux on Debian, Ubuntu and derivatives.
#
#   ./packaging/install-ubuntu.sh
#   SKIP_DEPS=1 ./packaging/install-ubuntu.sh    # dependencies already present
#
# Run it from a clone of the repository; nothing outside /usr and your user
# session is touched.
set -euo pipefail

# shellcheck source=packaging/install-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-common.sh"

require_commands python3 make sudo

if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    case "${ID:-}:${ID_LIKE:-}" in
        *debian*|*ubuntu*) ;;
        *) die "this installer targets Debian and Ubuntu; detected ${PRETTY_NAME:-unknown}" ;;
    esac
fi

RUNTIME_PACKAGES=(
    python3
    python3-pyside6.qtcore
    python3-pyside6.qtgui
    python3-pyside6.qtwidgets
    python3-pyside6.qtnetwork
    pipewire
    pipewire-pulse
    wireplumber
    libpulse0
    hicolor-icon-theme
)

BUILD_PACKAGES=(
    build-essential
    pkgconf
    libpulse-dev
    mingw-w64
    cabextract
    curl
)

install_dependencies() {
    log "Installing distribution packages with apt"
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends \
        "${RUNTIME_PACKAGES[@]}" "${BUILD_PACKAGES[@]}"
}

install_dependencies
fetch_runtime
build_host
install_tree
seed_spatial_filter
verify_runtime
activate_sessions

log "Done. Run 'nahimic' for the panel and 'nahimic --status' to check the service."