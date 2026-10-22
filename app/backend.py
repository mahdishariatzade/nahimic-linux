"""Original effect controls and installed application state."""
import copy
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "nahimic-linux"
RUNTIME = DATA / "runtime"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "host"))
from desktop_audio import atomic_json, pulse

PROFILES = {
    "Music": ("Music", "77f15d10-d6b9-11e7-8f1a-0800200c9a66"),
    "Movie": ("Movie", "77f15d11-d6b9-11e7-8f1a-0800200c9a66"),
    "Gaming": ("Gaming", "77f18421-d6b9-11e7-8f1a-0800200c9a66"),
    "Communication": ("Communication", "77f18420-d6b9-11e7-8f1a-0800200c9a66"),
}


class Backend:
    def __init__(self):
        self._cached_settings = None

    def control(self, *args):
        api = "Z:" + str(Path("/usr/share/nahimic-linux/vendor/NahimicAPO4API.dll")).replace("/", "\\")
        result = subprocess.run(["wine", str(Path(__file__).resolve().parents[1] / "bin/apo_control.exe"), api, *args],
                                env=os.environ | {"WINEPREFIX": str(RUNTIME / "prefix"), "WINEDEBUG": "-all",
                                                  "WINEDLLOVERRIDES": "mscoree,mshtml="},
                                capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise RuntimeError(result.stderr.strip()[-1200:] or "Vendor effect control failed")
        return result.stdout

    def _parse_settings(self, output):
        profile = re.search(r"(?:global_profile|default_application) id=\S+ name=(\S+)", output)
        if not profile:
            raise RuntimeError("Could not read the current effect profile")
        settings = {}
        for line in output.splitlines():
            match = re.search(r"name=(kSet_\w+) value=([-+\d.eE]+)", line)
            if not match:
                continue
            item = {"value": float(match[2])}
            for key in ("default", "min", "max"):
                found = re.search(rf"\b{key}=([-+\d.eE]+)", line)
                if found:
                    item[key] = float(found[1])
            settings[match[1]] = item
        res = {"profile": profile[1], "settings": settings}
        self._cached_settings = res
        return copy.deepcopy(res)

    def settings(self):
        output = self.control("--settings")
        return self._parse_settings(output)

    def set_settings(self, items):
        if isinstance(items, dict):
            items = list(items.items())
        args = ["--set-setting"]
        for k, v in items:
            args.extend([str(k), str(v)])
        self.control(*args)
        if self._cached_settings and "settings" in self._cached_settings and all(k in self._cached_settings["settings"] for k, _ in items):
            for k, v in items:
                self._cached_settings["settings"][k]["value"] = float(v)
            return copy.deepcopy(self._cached_settings)
        return self.settings()

    def set_setting(self, name, value):
        return self.set_settings([(name, value)])

    def profile(self, name):
        output = self.control("--global-profile", "{" + PROFILES[name][1] + "}")
        try:
            state = self._parse_settings(output)
            if state["settings"]:
                if state["profile"] != name:
                    raise RuntimeError("The effect profile was not applied")
                return state
        except Exception:
            pass
        state = self.settings()
        if state["profile"] != name:
            raise RuntimeError("The effect profile was not applied")
        return state

    def enabled(self, enabled):
        preferences = json.loads((RUNTIME / "preferences.json").read_text())
        preferences["enabled"] = bool(enabled)
        atomic_json(RUNTIME / "preferences.json", preferences)

    def _get_target(self):
        if not hasattr(self, "_target") or not self._target:
            self._target = json.loads((DATA / "installation.json").read_text())["target"]
        return self._target

    def volume(self, value):
        pulse("set-sink-volume", self._get_target(), str(int(value)) + "%")

    def mute(self, value):
        pulse("set-sink-mute", self._get_target(), str(int(value)))

    def autostart(self, enabled):
        subprocess.run(["systemctl", "--user", "enable" if enabled else "disable", "nahimic.service"],
                       check=True, capture_output=True, text=True, timeout=10)
        self._last_service_check = 0

    def _read_native_volume(self):
        volume_state_path = RUNTIME / "native-volume.state"
        if not volume_state_path.exists():
            return None
        try:
            data = volume_state_path.read_bytes()
            if len(data) >= 600:
                seq, _ = struct.unpack_from("<II", data, 0)
                slot_offset = 8 + (seq & 1) * 296
                slot = struct.unpack_from("<IIQIIIfff256s", data, slot_offset)
                magic, valid, muted, master_db = slot[1], slot[3], slot[5], slot[6]
                if magic == 0x41564F31 and valid:
                    linear = 10.0 ** (master_db / 60.0)
                    vol = max(0, min(100, round(linear * 100)))
                    return vol, bool(muted)
        except Exception:
            pass
        return None

    def status(self):
        now = time.monotonic()
        if not hasattr(self, "_last_service_check") or now - self._last_service_check > 2.0 or getattr(self, "_service_active", None) != "active":
            self._service_active = subprocess.run(["systemctl", "--user", "is-active", "nahimic.service"],
                                                  capture_output=True, text=True, timeout=5).stdout.strip()
            self._autostart_active = subprocess.run(["systemctl", "--user", "is-enabled", "nahimic.service"],
                                                    capture_output=True, text=True, timeout=5).returncode == 0
            self._last_service_check = now
        service = self._service_active
        auto = self._autostart_active
        result = {"ready": False, "service": service, "autostart": auto}
        status_path = RUNTIME / "desktop-state.json"
        if service == "active" and status_path.exists():
            try:
                result["waiting_for_speakers"] = json.loads(status_path.read_text()).get("waiting_for_speakers", False)
            except Exception:
                pass
        path = RUNTIME / "session.json"
        if path.exists():
            try:
                session = json.loads(path.read_text())
                if session.get("ready") and service == "active":
                    if status_path.exists():
                        result.update(json.loads(status_path.read_text()))
                        result["ready"] = True
                        result["instance"] = session["pid"]
            except Exception:
                pass
        nv = self._read_native_volume()
        if nv is not None and result.get("ready"):
            result["volume"], result["muted"] = nv
        return result
