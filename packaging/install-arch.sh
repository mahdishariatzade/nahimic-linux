#!/usr/bin/env bash
# Install Nahimic Linux on Arch Linux and derivatives.
#
#   ./packaging/install-arch.sh
#   SKIP_DEPS=1 ./packaging/install-arch.sh    # dependencies already present
#
# AUR users can install the packaged build instead:
#   yay -S nahimic-linux
set -euo pipefail

# shellcheck source=packaging/install-common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-common.sh"

require_commands python make sudo

if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    case "${ID:-}" in
        arch|endeavouros|manjaro|cachyos|garuda) ;;
        *) die "this installer targets Arch Linux; detected ${PRETTY_NAME:-unknown}" ;;
    esac
fi

RUNTIME_PACKAGES=(
    python
    pyside6
    wine
    pipewire
    pipewire-pulse
    wireplumber
    libpulse
    hicolor-icon-theme
)

BUILD_PACKAGES=(
    base-devel
    pkgconf
    mingw-w64-gcc
    cabextract
)

install_dependencies() {
    log "Installing distribution packages with pacman"
    sudo pacman -S --needed --noconfirm "${RUNTIME_PACKAGES[@]}" "${BUILD_PACKAGES[@]}"
}

install_dependencies
fetch_runtime
build_host
install_tree
seed_spatial_filter
verify_runtime
activate_sessions

log "Done. Run 'nahimic' for the panel and 'nahimic --status' to check the service."