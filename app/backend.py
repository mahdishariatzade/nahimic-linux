"""Original effect controls and installed application state."""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

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

    def set_setting(self, name, value):
        output = self.control("--set-setting", name, str(value))
        match = re.search(r"name=(kSet_\w+) value=([-+\d.eE]+)", output)
        if not match or match[1] != name or abs(float(match[2]) - float(value)) > 1e-5:
            raise RuntimeError("The effect setting was not applied")
        if self._cached_settings and "settings" in self._cached_settings and name in self._cached_settings["settings"]:
            self._cached_settings["settings"][name]["value"] = float(match[2])
            return copy.deepcopy(self._cached_settings)
        return self.settings()

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

    def volume(self, value):
        target = json.loads((DATA / "installation.json").read_text())["target"]
        pulse("set-sink-volume", target, str(int(value)) + "%")

    def mute(self, value):
        target = json.loads((DATA / "installation.json").read_text())["target"]
        pulse("set-sink-mute", target, str(int(value)))

    def autostart(self, enabled):
        subprocess.run(["systemctl", "--user", "enable" if enabled else "disable", "nahimic.service"],
                       check=True, capture_output=True, text=True, timeout=10)

    def status(self):
        service = subprocess.run(["systemctl", "--user", "is-active", "nahimic.service"],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
        auto = subprocess.run(["systemctl", "--user", "is-enabled", "nahimic.service"],
                              capture_output=True, text=True, timeout=5).returncode == 0
        result = {"ready": False, "service": service, "autostart": auto}
        status_path = RUNTIME / "desktop-state.json"
        if service == "active" and status_path.exists():
            result["waiting_for_speakers"] = json.loads(status_path.read_text()).get("waiting_for_speakers", False)
        path = RUNTIME / "session.json"
        if path.exists():
            session = json.loads(path.read_text())
            if session.get("ready") and service == "active":
                status = RUNTIME / "desktop-state.json"
                if status.exists():
                    result.update(json.loads(status.read_text()))
                    result["ready"] = True
                    result["instance"] = session["pid"]
        return result
