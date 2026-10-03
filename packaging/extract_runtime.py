"""Extract and verify the runtime data required by supported hardware."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

# Settings archives inside the generic restore tool, in resolution order. The
# first archive holding a file wins, so shared files such as Global.nsx and
# AudioProfiles come from the generic archive while device tuning comes from
# the vendor archive that carries it.
SETTINGS_ARCHIVES = (
    "Drivers\\EXT\\AIstone\\APO4\\NH3CNXTProductSettings.cab",
    "Drivers\\EXT\\MSI\\APO4\\NH3ProductSettings1.cab",
)


def settings_archives(path):
    """Read every settings cabinet out of the restore tool payload."""
    data = Path(path).read_bytes()
    start = data.find(b"PK\x03\x04")
    end = data.find(b"PK\x05\x06", start)
    if start < 0 or end < 0:
        raise ValueError("Runtime settings archive is absent")
    comment = struct.unpack_from("<H", data, end + 20)[0]
    with zipfile.ZipFile(io.BytesIO(data[start:end + 22 + comment])) as bundle:
        return [bundle.read(name) for name in SETTINGS_ARCHIVES]


def extract(swc, settings, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(Path(__file__).with_name("runtime-sha256.json").read_text())
    with tempfile.TemporaryDirectory(prefix="nahimic-runtime-", dir="/tmp") as temporary:
        work = Path(temporary)
        subprocess.run(["cabextract", "-q", "-d", str(work / "swc"), str(swc)], check=True)
        factory = []
        for index, cabinet in enumerate(settings_archives(settings)):
            root = work / f"factory{index}"
            root.mkdir()
            (work / "settings.cab").write_bytes(cabinet)
            subprocess.run(["cabextract", "-q", "-d", str(root), str(work / "settings.cab")], check=True)
            factory.append(root)
        for name, expected in manifest.items():
            group, relative = name.split("/", 1)
            roots = [work / "swc"] if group == "vendor" else factory
            source = next((root / relative for root in roots if (root / relative).is_file()), None)
            if source is None:
                raise ValueError("Runtime file is absent: " + name)
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ValueError("Runtime checksum mismatch: " + name)
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


if __name__ == "__main__":
    extract(*sys.argv[1:])