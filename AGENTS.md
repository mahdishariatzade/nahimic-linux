# AI Installation and Maintenance Guide

Read README.md first. When the user asks for an installation, check local dependencies and hardware, then install and verify.

## Installation

1. Run `pactl --format=json list sinks` and check `alsa.components` and the speaker port. Supported hardware is listed in `host/devices.json` (verified: `HDA:14f11f87,1d05e022,` and `HDA:10ec0274,146213c0,`; experimental: `HDA:10ec0256,1c05c022,`).
2. On Arch-based systems, clone this repository and run `makepkg -si` in `packaging/` (see README.md).
3. WirePlumber 0.5+ is required; keep the system selecting the real output device. Check `nahimic --status` for `ready`, `enabled`, and `active` (true when audio is actually passing through the filter). Open the panel from the system menu and verify the effects switch, volume, and that settings are saved.
4. Logs: `journalctl --user -u nahimic.service -b`. First initialization is slow; judge readiness from the runtime status.

## Code and device support

- `app/` is the Qt interface; `host/` is the audio host, real endpoint volume, hardware table, and user service; `packaging/` handles builds, runtime verification, and system integration.
- Effects are produced by the runtime components. Before changing anything, check the existing control interface and audio chain, and reuse behavior that is already verified.
- New models must have their hardware ID, device configuration, output port, and actual audio connection checked. Add them to `host/devices.json` (or the user's `~/.config/nahimic-linux/devices.json`). Mark borrowed tuning files as `"verified": false`.
- Keep raw working material outside the working tree; public commits contain only project source and required build metadata.
- Pin versions and verify SHA-256 for any new download source, and check file contents before updating `runtime-sha256.json`.
- Packaging may only write to the build directory and DESTDIR; it must not start user services or rewrite user configuration. Activation after install is done by the install script.
- Keep both entry points, AGENTS.md and CLAUDE.md.
- Translation keys are English source strings. New UI text must be added to every file in `app/locales/`.

## Verification and pull requests

After changing build or runtime paths, run `make`, `makepkg`, and the tests; check package contents, first launch, the switch, volume, settings read-back, and persistence across a cold restart. Audio chain changes should also be verified with continuous playback and checked for underruns. Record the actual scope of verification; a successful compile is not proof that a hardware adaptation works.

PR descriptions should state the model, the problem, the new behavior, and test results. Commit, push, and open the PR only when the user authorizes it; never merge without authorization.
