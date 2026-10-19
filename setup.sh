#!/usr/bin/env bash
#
# Nahimic Linux - Setup & Management Utility
# https://github.com/mahdishariatzade/nahimic-linux
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGING="$ROOT/packaging"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
    printf "${CYAN}${BOLD}"
    cat <<'EOF'
  _   _       _     _           _        _     _                 
 | \ | | __ _| |__ (_)_ __ ___ (_) ___  | |   (_)_ __  _   ___  __
 |  \| |/ _` | '_ \| | '_ ` _ \| |/ __| | |   | | '_ \| | | \ \/ /
 | |\  | (_| | | | | | | | | | | | (__  | |___| | | | | |_| |>  < 
 |_| \_|\__,_|_| |_|_|_| |_| |_|_|\___| |_____|_|_| |_|\__,_/_/\_\
EOF
    printf "${NC}\n"
    printf "   Universal Audio Enhancer for Linux Laptops\n"
    printf "   https://github.com/mahdishariatzade/nahimic-linux\n\n"
}

log_step() { printf "${BLUE}${BOLD}==>${NC} %s\n" "$*"; }
log_ok()   { printf "${GREEN}${BOLD}  ✓${NC} %s\n" "$*"; }
log_warn() { printf "${YELLOW}${BOLD}  !${NC} %s\n" "$*"; }
log_err()  { printf "${RED}${BOLD}  ✗ error:${NC} %s\n" "$*" >&2; }
die()      { log_err "$*"; exit 1; }

check_not_root() {
    if [ "$(id -u)" -eq 0 ]; then
        die "Do not run this script as root/sudo directly. It will request sudo permissions when needed."
    fi
}

check_architecture() {
    local arch
    arch="$(uname -m)"
    if [ "$arch" != "x86_64" ]; then
        die "Nahimic Linux requires a 64-bit (x86_64) processor; detected '$arch'."
    fi
    log_ok "Architecture: $arch"
}

detect_distro() {
    if [ ! -r /etc/os-release ]; then
        die "Cannot detect operating system (/etc/os-release missing)."
    fi
    # shellcheck disable=SC1091
    . /etc/os-release
    local id_str="${ID:-}:${ID_LIKE:-}"

    case "$id_str" in
        *arch*|*endeavouros*|*manjaro*|*cachyos*|*garuda*)
            DISTRO_FAMILY="arch"
            ;;
        *debian*|*ubuntu*|*linuxmint*|*pop*)
            DISTRO_FAMILY="debian"
            ;;
        *)
            DISTRO_FAMILY="unknown"
            ;;
    esac
    log_ok "Detected OS: ${PRETTY_NAME:-$ID} (Family: $DISTRO_FAMILY)"
}

check_multilib_arch() {
    if [ "$DISTRO_FAMILY" = "arch" ]; then
        if [ -f /etc/pacman.conf ]; then
            if ! grep -q "^\[multilib\]" /etc/pacman.conf; then
                log_warn "[multilib] repository is not enabled in /etc/pacman.conf."
                log_warn "Wine requires multilib. Please uncomment [multilib] in /etc/pacman.conf."
            else
                log_ok "Arch [multilib] repository is enabled."
            fi
        fi
    fi
}

check_audio_stack() {
    log_step "Checking audio stack and hardware..."
    if ! command -v pactl >/dev/null 2>&1; then
        log_warn "'pactl' is not installed yet (will be installed during setup)."
        return 0
    fi

    local sinks_json
    sinks_json=$(pactl --format=json list sinks 2>/dev/null || true)
    if [ -z "$sinks_json" ]; then
        log_warn "No audio sinks found. Make sure PipeWire is running."
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        python3 - "$ROOT" "$sinks_json" <<'PY' || true
import sys, json
from pathlib import Path

root = Path(sys.argv[1])
sinks_json = sys.argv[2]
sys.path.insert(0, str(root))

try:
    from host import devices
    sinks = json.loads(sinks_json)
    matched = None
    speaker_active = False

    for s in sinks:
        port = s.get("active_port")
        if port in ("analog-output-speaker", "[Out] Speaker"):
            speaker_active = True
        m = devices.match(s)
        if m:
            matched = m
            break

    if speaker_active:
        print("\033[0;32m\033[1m  ✓\033[0m Active audio output: Built-in Speakers")
    else:
        print("\033[1;33m\033[1m  !\033[0m Notice: Built-in speakers are not currently the active output.")

    if matched:
        verified_str = "Verified Support" if matched.get("verified") else "Community Support"
        print(f"\033[0;32m\033[1m  ✓\033[0m Matched Hardware Profile: {matched.get('name')} [{verified_str}]")
    else:
        print("\033[0;32m\033[1m  ✓\033[0m Hardware will use auto-extracted OEM tuning tables.")
except Exception as e:
    pass
PY
    fi
}

do_install() {
    banner
    check_not_root
    check_architecture
    detect_distro
    check_multilib_arch
    check_audio_stack

    echo ""
    log_step "Starting installation for $DISTRO_FAMILY..."

    case "$DISTRO_FAMILY" in
        arch)
            "$PACKAGING/install-arch.sh"
            ;;
        debian)
            "$PACKAGING/install-ubuntu.sh"
            ;;
        *)
            die "Automated installation is currently supported for Arch-based and Debian/Ubuntu-based distributions.\nFor other distributions, please consult README.md."
            ;;
    esac

    echo ""
    log_step "Verifying installation..."
    sleep 1
    if command -v nahimic >/dev/null 2>&1; then
        local status_out
        status_out=$(nahimic --status 2>/dev/null || echo "Service starting...")
        log_ok "Nahimic Linux installed successfully!"
        echo "  Service status: $status_out"
        echo ""
        printf "${GREEN}${BOLD}All done!${NC} Launch ${BOLD}Nahimic${NC} from your application menu or run '${BOLD}nahimic${NC}'.\n\n"
    else
        log_warn "Installation finished. Please log out and back in, or run 'nahimic --activate'."
    fi
}

do_status() {
    banner
    log_step "Checking Nahimic status..."
    if command -v nahimic >/dev/null 2>&1; then
        echo "--- Status ---"
        nahimic --status || true
        echo ""
    fi
    echo "--- Systemd Service ---"
    systemctl --user status nahimic.service --no-pager || true
}

do_restart() {
    log_step "Restarting nahimic.service..."
    systemctl --user restart nahimic.service
    log_ok "Service restarted."
    if command -v nahimic >/dev/null 2>&1; then
        nahimic --status || true
    fi
}

do_uninstall() {
    banner
    check_not_root
    detect_distro

    printf "${YELLOW}${BOLD}Warning:${NC} This will completely remove Nahimic Linux from your system.\n"
    read -r -p "Are you sure you want to proceed? [y/N] " confirm
    case "$confirm" in
        [yY][eE][sS]|[yY]) ;;
        *) echo "Aborted."; exit 0 ;;
    esac

    log_step "Stopping and disabling service..."
    pkill -f '[a]pp/main.py' || true
    systemctl --user disable --now nahimic.service >/dev/null 2>&1 || true
    WINEPREFIX="$HOME/.local/share/nahimic-linux/runtime/prefix" wineserver -k 2>/dev/null || true

    log_step "Removing installed files..."
    if [ "$DISTRO_FAMILY" = "arch" ] && pacman -Qq nahimic-linux >/dev/null 2>&1; then
        sudo pacman -Rns --noconfirm nahimic-linux
    else
        sudo rm -rf /usr/lib/nahimic-linux \
                    /usr/share/nahimic-linux \
                    /usr/bin/nahimic \
                    /usr/lib/systemd/user/nahimic.service \
                    /usr/share/applications/nahimic.desktop \
                    /usr/share/icons/hicolor/scalable/apps/nahimic.svg \
                    /etc/xdg/autostart/nahimic.desktop
        systemctl --user daemon-reload || true
        systemctl --user reset-failed nahimic.service 2>/dev/null || true
    fi

    log_step "Cleaning user data and Wine prefix..."
    rm -rf "$HOME/.local/share/nahimic-linux"
    
    log_ok "Nahimic Linux has been cleanly removed."
}

show_help() {
    cat <<EOF
Usage: ./setup.sh [COMMAND]

Commands:
  install        Install and activate Nahimic Linux (default)
  --status       Check current runtime and systemd service status
  --restart      Restart the background audio service
  --uninstall    Cleanly remove Nahimic Linux and its runtime data
  --help, -h     Show this help message

Examples:
  ./setup.sh              # Quick full install
  ./setup.sh --status     # View current status
  ./setup.sh --uninstall  # Remove Nahimic
EOF
}

case "${1:-install}" in
    install|--install)
        do_install
        ;;
    status|--status)
        do_status
        ;;
    restart|--restart)
        do_restart
        ;;
    uninstall|--uninstall)
        do_uninstall
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_err "Unknown option '$1'"
        show_help
        exit 1
        ;;
esac
