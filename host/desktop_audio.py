"""Desktop routing and real endpoint volume for the installed application."""
import json
from pathlib import Path
import subprocess
import devices


def pulse(*args):
    return subprocess.run(["pactl", *args], check=True, capture_output=True,
                          text=True, timeout=5).stdout.strip()


def atomic_json(path, value):
    path = Path(path)
    # The state directory is created at activation time, so a reset that removed
    # it must not leave the service unable to write.
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    pending.replace(path)


def level(sink):
    return (tuple(sink["volume"][ch]["value"] for ch in ("front-left", "front-right")), sink["mute"])


class OutputUnavailable(RuntimeError):
    """The configured speaker endpoint is temporarily unavailable."""


def supported_speaker(sink):
    """True when the sink is a known built-in speaker on its speaker port (see devices.json)."""
    return devices.match(sink) is not None


class DesktopAudio:
    def __init__(self, work, sink, target):
        self.work, self.sink, self.target = Path(work), sink, target
        self.enabled = None
        self.node_id = None
        self.last_status = None

    def sinks(self):
        return {s["name"]: s for s in json.loads(pulse("--format=json", "list", "sinks"))}

    def set_enabled(self, enabled):
        subprocess.run(["pw-metadata", "-n", "filters", str(self.node_id),
                        "filter.smart.disabled", json.dumps(not enabled), "Spa:String:JSON"],
                       check=True, capture_output=True, text=True, timeout=5)
        self.enabled = enabled

    def tick(self, initializing=False):
        preferences = json.loads((self.work / "preferences.json").read_text())
        if type(preferences.get("enabled")) is not bool:
            raise ValueError("Missing boolean enabled preference")
        enabled = preferences["enabled"]
        sinks = self.sinks()
        physical = sinks.get(self.target)
        if physical is None or not supported_speaker(physical):
            raise OutputUnavailable("Waiting for the configured built-in speakers")
        virtual = sinks[self.sink]
        properties = virtual["properties"]
        if (properties.get("filter.smart") != "true"
                or json.loads(properties["filter.smart.target"]) != {"node.name": self.target}
                or properties.get("monitor.channel-volumes") != "false"):
            raise RuntimeError("Speaker filter properties were not applied correctly")
        self.node_id = int(properties["object.id"])
        if enabled != self.enabled:
            self.set_enabled(enabled)
        actual = level(physical)
        streams = json.loads(pulse("--format=json", "list", "sink-inputs"))
        applications = [s for s in streams
                        if s.get("properties", {}).get("node.name") != self.sink + "_render"
                        and s["sink"] == virtual["index"]]
        # Report the actual filter connection, including streams explicitly
        # assigned to speakers while another device is the system default.
        renderers = [s for s in streams
                     if s.get("properties", {}).get("node.name") == self.sink + "_render"]
        if initializing and not renderers:
            return False
        if len(renderers) != 1:
            raise RuntimeError("Original audio playback stream is missing")
        linked = renderers[0]["sink"] == physical["index"]
        if renderers[0]["sink"] not in (physical["index"], 4294967295):
            # Name the device that took the stream: another effect application
            # owning the default sink is the usual cause and is actionable.
            taken = next((name for name, item in sinks.items()
                          if item["index"] == renderers[0]["sink"]), "another device")
            raise RuntimeError(f"Effect playback is linked to {taken} instead of the built-in "
                               "speakers. Another application is processing the system output "
                               "(EasyEffects is the common case); quit it, or make the built-in "
                               "speakers the default output again, then restart the service.")
        active = enabled and linked and bool(applications)
        status = {"enabled": enabled, "active": active, "volume": round(max(actual[0]) / 65536 * 100),
                  "muted": actual[1], "applications": len(applications), "output": physical["description"]}
        if status != self.last_status:
            atomic_json(self.work / "desktop-state.json", status)
            self.last_status = status
        return True

    def close(self):
        # WirePlumber restores each stream's own target when the filter is
        # disabled. Never rewrite the system default or individual app targets.
        if self.node_id is not None and self.enabled:
            self.set_enabled(False)
