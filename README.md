# Nahimic Linux

Nahimic audio effects for laptop speakers on Linux. Includes Music, Movie, Gaming, and Communication profiles; bass, voice, and treble controls; surround sound; volume stabilization; and a ten-band equalizer. Switch between processed and original audio with one click. Volume stays in sync with the system, settings are saved automatically, and effects keep running after you close the panel.

This fork adds support for the **Realtek ALC256** and **Realtek ALC274** audio chips, ships installers for **Arch Linux and Debian/Ubuntu**, and uses English as the source language. It is based on [wearzdk/nahimic-linux](https://github.com/wearzdk/nahimic-linux).

This is an independent community project. It is not affiliated with, endorsed by, or sponsored by Nahimic, A-Volute, SteelSeries, or PC manufacturers. Names, trademarks, and original assets belong to their respective owners.

![Nahimic Linux control panel](docs/panel.png)

---

## Setup guide

Follow these steps **in order**. Do not skip ahead. Every command is typed into a terminal on the Linux laptop you want to use.

### Before you start: requirements

You need all of the following. If any are missing, this project will not work on your machine.

- An **Arch Linux** based distribution (Arch, EndeavourOS, Manjaro, CachyOS, Garuda, and similar) or **Debian/Ubuntu** and derivatives. The Arch package uses `pacman` and `makepkg`; Debian/Ubuntu uses the bundled shell installer.
- A 64-bit (x86_64) laptop.
- **PipeWire** as your sound system (the default on current Arch-based systems).
- A supported audio chip (you check this in Step 1).

### Step 1: Check your audio hardware (before installing anything)

This step only reads information. It does not change your system, and you do not need Nahimic installed yet.

1. **Unplug** any headphones and disconnect Bluetooth audio.
2. In your system sound settings, select the **built-in speakers** as the output.
3. Run:

   ```sh
   pactl --format=json list sinks | python3 -c "import json,sys; [print(s['name'], '|', s['active_port'], '|', s['properties'].get('alsa.components')) for s in json.load(sys.stdin)]"
   ```

   If you get `pactl: command not found`, run `sudo pacman -S libpulse` and try again.

4. Look at the output. You should see a line similar to:

   ```
   alsa_output.pci-0000_00_1f.3.analog-stereo | analog-output-speaker | HDA:10ec0256,1c05c022,00100002
   ```

   Check both of these on the same line:

   | Check | What you need to see |
   |---|---|
   | Middle column (port) | `[Out] Speaker` or `analog-output-speaker` |
   | Last column (hardware) | `HDA:10ec0256,1c05c022,` (Realtek ALC256), `HDA:10ec0274,146213c0,` (MSI Stealth 14 Studio A13VF) or `HDA:14f11f87,1d05e022,` (MECHREVO Wujie 14X Pro) |

5. Decide:
   - **Both checks match:** continue to Step 2.
   - **Hardware matches but the port says headphones:** go back to items 1 and 2, then run the command again.
   - **Codec matches (`10ec0256`) but the subsystem differs:** your laptop is an ALC256 with different speakers. Add your own entry as shown in "Adding a device" below, using your subsystem ID.
   - **Codec does not match:** stop here. Your chip is not supported yet. Open an issue and include the full output of the command.

Write down the middle value of the hardware ID (in the example above, `1c05c022`). This is your laptop's **subsystem ID**. You may need it in Step 6.

### Step 2: Enable the multilib repository (Arch only)

Wine, which this project needs, is in Arch's `multilib` repository. Many systems have it enabled already.

1. Open the pacman config:

   ```sh
   sudo nano /etc/pacman.conf
   ```

2. Find these two lines and remove the `#` from the start of both, if it is there:

   ```
   #[multilib]
   #Include = /etc/pacman.d/mirrorlist
   ```

3. Save (`Ctrl+O`, `Enter`) and exit (`Ctrl+X`).
4. Refresh and update your system:

   ```sh
   sudo pacman -Syu
   ```

### Step 3: Install the build tools

Arch:

```sh
sudo pacman -S --needed base-devel git
```

Debian/Ubuntu:

```sh
sudo apt-get update
sudo apt-get install -y build-essential pkgconf libpulse-dev mingw-w64 cabextract git
```

The remaining dependencies (Wine, PySide6, and others) are installed automatically in Step 4.

### Step 4: Download, build, and install

Keep the **built-in speakers selected** during this step. The installer sets up the audio service at the end, and it looks for the speakers at that moment.

Arch:

```sh
cd ~
git clone https://github.com/mahdishariatzade/nahimic-linux.git
cd nahimic-linux/packaging
makepkg -si
```

Debian/Ubuntu:

```sh
cd ~
git clone https://github.com/mahdishariatzade/nahimic-linux.git
cd nahimic-linux
./packaging/install-ubuntu.sh
```

Both paths download the Nahimic runtime files from Microsoft Update and the Nahimic support site, check their SHA-256 hashes, build the program, install it under `/usr`, and enable the user service. This can take several minutes.

- `makepkg` and the Debian/Ubuntu installer ask for your password. Answer `Y` when asked to confirm dependencies.
- Do **not** run `makepkg` with `sudo`. It refuses to run as root. The Debian/Ubuntu installer uses `sudo` only for the individual steps that need it.

If the end of the output says `Nahimic: open the application to see the setup error.`, the speakers were not detected. Go back to Step 1, fix the output selection, then continue to Step 5 anyway. Opening the app retries the setup.

### Step 5: Open the app and confirm it works

1. Open **Nahimic** from your application menu, or run `nahimic` in a terminal.
2. Wait. The first launch prepares a Wine environment and can take a minute or two. The status line reads "Preparing effects. Please wait…" during this time.
3. Play some audio (music or a video) through the speakers.
4. In a terminal, run:

   ```sh
   nahimic --status
   ```

   You should see `"ready": true`, `"enabled": true`, and `"active": true`. `active` only becomes true while audio is actually playing.

5. Toggle the power button at the top of the app. You should hear the difference between processed and original sound.
6. Log out and back in (or reboot) and confirm the effects start again on their own.

On the Realtek ALC256 laptop, the ALC256 support is **experimental**: it borrows the speaker tuning from a different laptop. Start with a low bass setting.

The MSI Stealth 14 Studio A13VF entry (Realtek ALC274, Intel SOF, subsystem `146213c0`) uses the tuning file that MSI ships for that machine, so it starts from the correct speaker correction. It is still marked `verified: false` until the entry has been tested on the hardware. Step 6 explains how to use tuning made for your own laptop.

### Step 6 (optional): Use your laptop's own speaker tuning

Only do this if your laptop originally shipped with Nahimic on Windows and you can get its tuning file.

1. On the Windows side (or a Windows backup), look in `C:\Windows\System32\DriverStore\FileRepository\` for a file named like `*ProductSettings.cab`, or for a `Devices\<SUBSYSTEM ID>_Speakers.nsx` file matching the subsystem ID from Step 1.
2. If you found a `.cab` file, extract it on Linux with `cabextract` and find the `Devices/<SUBSYSTEM ID>_Speakers.nsx` file inside.
3. Copy the `.nsx` file to your Linux home folder, for example `~/nahimic/1C05C022_Speakers.nsx`.
4. Create the file `~/.config/nahimic-linux/devices.json` with this content, replacing the subsystem ID and path with yours (use lowercase for `subsystem` and the full path, not `~`):

   ```json
   {
     "devices": [
       {
         "name": "My laptop (ALC256, own tuning)",
         "codec": "10ec0256",
         "subsystem": "1c05c022",
         "device_file": "/home/YOURNAME/nahimic/1C05C022_Speakers.nsx",
         "verified": false
       }
     ]
   }
   ```

5. Reset the effect engine so it loads the new tuning. This also resets your effect settings:

   ```sh
   systemctl --user stop nahimic.service
   rm -rf ~/.local/share/nahimic-linux/runtime ~/.local/share/nahimic-linux/installation.json
   nahimic --activate
   ```

6. Repeat Step 5 to confirm everything works.

---

## Adding more hardware later

Supported hardware lives in a plain JSON table that is read at startup, so adding a laptop needs no rebuild and no code changes. You need the codec and subsystem values from the hardware ID in Step 1, in lowercase.

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
- `device_file` is the speaker tuning. Point it at `Devices/1D05E022_Speakers.nsx` to borrow the existing tuning, or at the full path of your own `.nsx` file (see Step 6).
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

```sh
sudo pacman -R nahimic-linux        # Arch
```

```sh
sudo rm -rf /usr/lib/nahimic-linux /usr/share/nahimic-linux /usr/bin/nahimic \
    /usr/lib/systemd/user/nahimic.service /usr/share/applications/nahimic.desktop \
    /usr/share/icons/hicolor/scalable/apps/nahimic.svg /etc/xdg/autostart/nahimic.desktop
systemctl --user disable --now nahimic.service   # Debian/Ubuntu
```

This stops and disables the service. To also remove your settings and the Wine environment:

```sh
rm -rf ~/.local/share/nahimic-linux ~/.config/nahimic-linux
```

## Troubleshooting

| Problem | What to do |
|---|---|
| "No supported built-in speakers were found" | Repeat Step 1. The speakers must be the selected output with nothing plugged in. |
| Status stuck on "Preparing effects" | Wait two minutes, then check the log (below). |
| "The audio service is not running" | Run `systemctl --user restart nahimic.service`, then reopen the app. |
| Effects stop when headphones are plugged in | Expected. Effects only apply to the built-in speakers and resume when you unplug. |
| `unverified hardware profile in use` in the log | Expected on Realtek ALC256. It is a reminder that the tuning is borrowed. |

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
