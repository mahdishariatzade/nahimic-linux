"""Hardware table: which speaker endpoints are supported and which tuning file each one uses."""
import json
import os
from pathlib import Path

BUILTIN = Path(__file__).with_name("devices.json")
GENERATED = "Devices.auto.json"
USER = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "nahimic-linux" / "devices.json"


def table_at(path):
    """Read a hardware table, returning empty lists when it is absent."""
    path = Path(path) if path else None
    if path is None or not path.is_file():
        return [], []
    local = json.loads(path.read_text())
    return list(local.get("devices", [])), list(local.get("speaker_ports", []))


def load(user_path=USER, generated=None):
    """Return the hardware table: user entries first, then builtin, then generated.

    generated points at the table the installer derives from the vendor cabinets.
    It only carries subsystem identifiers, so it sits behind the curated table and
    acts as the fallback that makes an unlisted laptop work without any edit.
    """
    table = json.loads(BUILTIN.read_text())
    ports = list(table["speaker_ports"])
    devices, _ = table_at(user_path)
    devices = devices + list(table["devices"])
    generated_devices, generated_ports = table_at(generated)
    devices = devices + generated_devices
    for extra in (ports, generated_ports):
        ports = ports + [p for p in extra if p not in ports]
    for device in devices:
        if not device.get("device_file") or not (device.get("codec") or device.get("subsystem")):
            raise ValueError("Device entries need device_file and a codec or a subsystem: "
                             + json.dumps(device))
    return devices, ports


def components(sink):
    """Return every (codec, subsystem) pair in alsa.components.

    A sink can list several codecs, e.g. on Intel SOF/DSP machines where the
    HDMI codec and the analog codec both appear:
    "HDA:8086281c,80860101,00100000 HDA:10ec0256,1c05c022,00100002 cfg-dmics:2".
    """
    value = sink.get("properties", {}).get("alsa.components", "").lower()
    found = []
    for part in value.split():
        if part.startswith("hda:"):
            fields = part[4:].split(",")
            if len(fields) >= 2:
                found.append((fields[0], fields[1]))
    return found


def match(sink, table=None, generated=None):
    """Return the device entry for a speaker sink on its speaker port, or None."""
    devices, ports = table or load(generated=generated)
    if sink.get("active_port") not in ports:
        return None
    present = components(sink)
    for device in devices:
        for codec, subsystem in present:
            wanted_codec = device.get("codec")
            wanted_subsystem = device.get("subsystem")
            if wanted_codec and wanted_codec.lower() != codec:
                continue
            if wanted_subsystem not in (None, "", "*") and wanted_subsystem.lower() != subsystem:
                continue
            if wanted_subsystem in (None, "", "*") and not wanted_codec:
                continue
            return device
    return None
