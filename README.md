# Nahimic Linux

Nahimic audio effects for laptop speakers on Linux. Includes Music, Movie, Gaming, and Communication profiles; bass, voice, and treble controls; surround sound; volume stabilization; and a ten-band equalizer. Switch between processed and original audio with one click. Volume stays in sync with the system, settings are saved automatically, and effects keep running after you close the panel.

This fork is engineered for **maximum stability and universal laptop support**:
- **Rock-solid Audio Pipeline:** 1MB IPC pipe buffer capacity (`fcntl.F_SETPIPE_SZ`) eliminating underruns, dropouts, and audio stuttering under heavy CPU loads.
- **Real-Time Process Priority:** systemd scheduling priority (`Nice=-11`, RT Limits) to keep audio processing responsive and stutter-free.
- **Graceful Device Switching:** 2-second debouncing grace period preventing crashes when plugging in headphones, connecting Bluetooth, or attaching HDMI monitors.
- **Universal Hardware Support:** Auto-extracts official vendor tuning for over 1,000 laptop models, with verified support for **Realtek ALC274** (e.g. MSI Stealth 14 Studio with Intel SOF) and **MECHREVO** (`14f11f87,1d05e022`).
- **Clean Distro Packaging:** Automated native installers for **Arch Linux** and **Debian / Ubuntu**.
- **Clean Coexistence:** Clean speaker-focused enhancement that runs seamlessly alongside other native audio tools (e.g. EasyEffects with DeepFilterNet for microphone).

It is based on [wearzdk/nahimic-linux](https://github.com/wearzdk/nahimic-linux).

This is an independent community project. It is not affiliated with, endorsed by, or sponsored by Nahimic, A-Volute, SteelSeries, or PC manufacturers. Names, trademarks, and original assets belong to their respective owners.

![Nahimic Linux control panel](docs/panel.png)

---

## Setup guide

### Fast Install (Recommended)
Clone the repository and run the automated setup script. It auto-detects your distribution (Arch, Ubuntu, Debian, Manjaro, etc.), verifies hardware and PipeWire support, installs dependencies, builds, and activates the audio service:

```sh
git clone https://github.com/mahdishariatzade/nahimic-linux.git
cd nahimic-linux
./setup.sh
```

### Manual Install

**Arch / EndeavourOS / Manjaro (native package):**
```sh
cd packaging && makepkg -si
```

**Debian / Ubuntu:**
```sh
./packaging/install-ubuntu.sh
```

### Management Commands
```sh
./setup.sh --status       # Check runtime and systemd service status
./setup.sh --restart      # Restart audio service
./setup.sh --uninstall    # Cleanly remove Nahimic Linux and runtime data
```

---

## Optional: the Nahimic spatial filter

Virtual surround and the headphone spatialisation of Nahimic are driven by a filter database that the Windows application hands to the driver at runtime, so it is not part of the driver package. Without it the service still works and every other effect applies; the spatial filter simply stays at whatever the driver package provides.

If you have a Windows installation that runs Nahimic, read the database back and seed it into the Wine prefix:

```sh
python3 packaging/nahimic-settings.py extract --windows /mnt/win11
python3 packaging/nahimic-settings.py seed
systemctl --user restart nahimic.service
```

The first command needs `reged` from the `chntpw` package and writes `extra/3d-database.bin` plus the full settings dump for reference. Nothing proprietary is stored in this repository, so `extra/` is ignored by git. The installers run the seeding step automatically when `extra/3d-database.bin` is present.

Seeding only works while the prefix is consistent. If the service reports `Original APO initialization failed`, a rejected import has left the product half initialized; reset it and start over:

```sh
systemctl --user stop nahimic.service
rm -rf ~/.local/share/nahimic-linux/runtime ~/.local/share/nahimic-linux/installation.json
nahimic --activate
```

## Hardware support

Most laptops need nothing: the installer opens every vendor cabinet in the Nahimic driver tool, copies the speaker tuning it finds and writes a matching table, so a laptop whose manufacturer ships tuning with the driver works out of the box. On a current driver tool that is over a thousand laptops.

The curated table in `host/devices.json` only pins the hardware that has been tested. It wins over the generated one, because the generated entries can only match a subsystem identifier: a tuning cabinet records no codec. To have a laptop recognised with its codec, its real name and the verified flag, add an entry there:

```json
{
  "name": "Laptop model (Realtek ALC287)",
  "codec": "10ec0287",
  "subsystem": "1462xxxx",
  "device_file": "Devices/1462xxxx_InternalSpeakers.nsx",
  "verified": false
}
```

A laptop that matches nothing still works through `~/.config/nahimic-linux/devices.json`, which takes priority over both tables and needs no rebuild.

## Adding more hardware later

The tables are plain JSON read at startup, so nothing here needs a rebuild. You need the codec and subsystem values from the hardware ID in Step 1, in lowercase. An unlisted laptop that ships its own tuning is picked up by the generated table, so this is only needed when you want a codec, a real name or the verified flag.

**For your own machines**, create `~/.config/nahimic-linux/devices.json`. Entries there are checked before the built-in table, and package updates never touch them:

```json
{
  "devices": [
    {
      "name": "Other laptop",
      "codec": "10ec0256",
      "subsystem": "1043abcd",
      "device_file": "Devices/1D05E022_Speakers.nsx",
      "verified": false
    }
  ]
}
```

Then run `nahimic --activate` so the service picks up the new speaker output. Notes:

- `subsystem` can be `null` to match every laptop using that codec.
- `device_file` is the speaker tuning. Point it at `Devices/1D05E022_Speakers.nsx` to borrow the existing tuning, at a file the generated table already produced under `/usr/share/nahimic-linux/factory/Devices/`, or at the full path of your own `.nsx` file (extracted from your vendor Windows driver CAB).
- `codec` may be left out to match the subsystem with any codec, which is what the generated entries do.
- Leave `verified` as `false` unless you have tested that entry on the machine itself.

**For everyone**, add the entry to [host/devices.json](host/devices.json) in the repository instead, then commit, push, and reinstall. Do not edit the installed copy under `/usr/lib/nahimic-linux/`, because a package update overwrites it.

## Moving to another distribution

**Another Arch-based distribution** (Arch, EndeavourOS, Manjaro, Garuda, and similar): nothing changes. Use the same steps in the setup guide. Your settings in `~/.local/share/nahimic-linux/` and `~/.config/nahimic-linux/` carry over if you keep your home folder. Distributions that update packages more slowly may ship an older Wine or PySide6, which is the first thing to check if it works on one system but not another.

**Debian, Ubuntu and derivatives:** use the bundled installer, which installs the Debian package set, fetches and verifies the runtime files, builds, installs and enables the service:

```sh
./packaging/install-ubuntu.sh
```

**Another distribution** (Fedora, openSUSE, NixOS): everything is portable, so a manual install is possible:

1. Install the equivalents of the dependencies listed in [packaging/PKGBUILD](packaging/PKGBUILD): Wine, PySide6, PipeWire, PipeWire Pulse, WirePlumber 0.5+, libpulse, systemd, plus MinGW-w64 GCC and cabextract for the build.
2. Run `python3 packaging/fetch_runtime.py --output build/runtime` to download, unpack and hash-verify the runtime files.
3. Run `make` and `sudo make install`, then copy `build/runtime/vendor` and `build/runtime/factory` to `/usr/share/nahimic-linux/`.
4. Run `nahimic --activate`.

## Updating

```sh
cd ~/nahimic-linux
git pull
```

Arch: `cd packaging && makepkg -si`. Debian/Ubuntu: `./packaging/install-ubuntu.sh`.

## Uninstalling

Stop the panel and the service first, so nothing is holding the Wine prefix:

```sh
pkill -f '[a]pp/main.py'
systemctl --user disable --now nahimic.service
WINEPREFIX=~/.local/share/nahimic-linux/runtime/prefix wineserver -k   # optional, kills leftovers
```

Arch removes the package with its dependencies:

```sh
sudo pacman -Rns nahimic-linux
```

Debian/Ubuntu has no package, so remove the installed tree:

```sh
sudo rm -rf /usr/lib/nahimic-linux /usr/share/nahimic-linux /usr/bin/nahimic \
    /usr/lib/systemd/user/nahimic.service /usr/share/applications/nahimic.desktop \
    /usr/share/icons/hicolor/scalable/apps/nahimic.svg /etc/xdg/autostart/nahimic.desktop
systemctl --user daemon-reload
systemctl --user reset-failed nahimic.service 2>/dev/null || true
```

Then remove your settings, the extracted spatial filter and the Wine environment, which holds the whole prefix including the seeded database:

```sh
rm -rf ~/.local/share/nahimic-linux ~/.config/nahimic-linux
rm -rf extra                             # in the repository, if you extracted one there
```

Check that nothing is left:

```sh
systemctl --user status nahimic.service   # expected: Unit nahimic.service could not be found
pgrep -af '[n]ahimic-linux/host'            # expected: no output
```

The packages that were installed for it stay behind, because other software may use them too. On Debian/Ubuntu they are `wine`, `mingw-w64`, `cabextract`, `python3-pyside6.qtcore`, `python3-pyside6.qtgui`, `python3-pyside6.qtwidgets` and `python3-pyside6.qtnetwork`; on Arch `wine`, `mingw-w64-gcc` and `cabextract`. Remove the ones you do not need with `apt remove` or `pacman -R`.

## Troubleshooting

| Problem | What to do |
|---|---|
| "No supported built-in speakers were found" | Repeat Step 1. The speakers must be the selected output with nothing plugged in. |
| Status stuck on "Preparing effects" | Wait two minutes, then check the log (below). |
| "The audio service is not running" | Run `systemctl --user restart nahimic.service`, then reopen the app. |
| Effects stop when headphones are plugged in | Expected. Effects only apply to the built-in speakers and resume when you unplug. |
| `unverified hardware profile in use` in the log | Expected on Realtek ALC256. It is a reminder that the tuning is borrowed. |
| "Effect playback is linked to ... instead of the built-in speakers" | Another application owns the system output, EasyEffects being the usual one. Quit it, then `systemctl --user restart nahimic.service`. Only one effect chain can process the speakers at a time. |

Useful commands:

```sh
nahimic --status
systemctl --user status nahimic.service
journalctl --user -u nahimic.service -b
```

Settings are stored in `~/.local/share/nahimic-linux/`.

## Using the app

The power control at the top switches between audio effects and original audio. Open **Equalizer** for the ten-band controls, or **Settings** to configure startup and interface language. Changes appear immediately while the app applies and confirms them in the background. If a write fails, the panel reads the current state and displays an error.

The app uses a custom title bar: drag it to move the window, double-click to maximize or restore, and drag the window edges to resize.

Interface languages: English, Simplified Chinese, Traditional Chinese, Japanese, Korean, German, French, Spanish, Portuguese, Italian, Russian, and Turkish. The app follows the system language, with English used for unsupported locales. You can change it in **Settings**.

---

## For developers

### How it works

The effects are produced by the original Windows Nahimic APO4 audio engine, running under Wine inside a dedicated prefix. PipeWire sends speaker audio to that engine as 48 kHz stereo float PCM and plays the processed result on the real speaker output. Because the engine only sees PCM, it does not depend on the audio chip. Two things are hardware specific:

1. **Detection:** which PipeWire sink counts as "the built-in speakers".
2. **Tuning:** the device settings file (`Devices/*_Speakers.nsx`) that the engine loads. The pinned download only contains the tuning for subsystem `1D05E022`.

Both are defined in [host/devices.json](host/devices.json). Entries in `~/.config/nahimic-linux/devices.json` are checked first. `device_file` can be relative to the factory settings folder or an absolute path.

### Supported hardware

| Hardware | Codec | Subsystem | Tuning file | Status |
|---|---|---|---|---|
| MECHREVO Wujie 14X Pro (Senary) | `14f11f87` | `1d05e022` | factory `1D05E022_Speakers.nsx` | Verified |
| MSI Stealth 14 Studio A13VF | `10ec0274` | `146213c0` | vendor `146213C0_InternalSpeakers.nsx` | Verified |
| Realtek ALC256 laptop | `10ec0256` | `1c05c022` | borrowed `1D05E022_Speakers.nsx` | Experimental |

Accepted speaker ports: `[Out] Speaker` (ALSA UCM) and `analog-output-speaker` (legacy profiles).

### Building without installing

Build dependencies: MinGW-w64 GCC, a C compiler, pkg-config, libpulse, Python, and cabextract.

```sh
make                                      # native host components
make DESTDIR=/tmp/nahimic-stage install   # inspect the install layout
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests
```

Runtime components are downloaded and verified by [packaging/PKGBUILD](packaging/PKGBUILD) and [packaging/extract_runtime.py](packaging/extract_runtime.py). Translations are in [app/locales/](app/locales/); message keys are the English source strings, and new text must be added to every locale file.

### Contributing device support

Read [AGENTS.md](AGENTS.md) first. Include your laptop model, audio hardware ID (`alsa.components`), PipeWire output information, and results from testing effect switching, settings persistence, service restarts, and continuous playback. Verify new device support on the actual machine before submitting a pull request.

## License and attribution

The community application and host code use the [MIT license](LICENSE). Downloaded runtime components retain their [upstream licensing terms](packaging/LicenseRef-Nahimic); original interface artwork is covered by its [attribution notice](app/assets/NOTICE.txt), not the community code's MIT license. Nahimic and other names and trademarks belong to their respective owners.
