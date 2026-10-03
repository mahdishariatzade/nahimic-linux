"""Prepare device and profile settings for the audio engine."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def prepare(source: Path, destination: Path):
    source = source.resolve(strict=True)
    if destination.exists():
        raise FileExistsError(f"Choose a new output directory: {destination}")
    global_tree = ET.parse(source / "Global.nsx")
    global_root = global_tree.getroot()
    metadata = ET.parse(source / "Metadata.nsx").getroot()
    default_profile = metadata.findtext("Data/DefaultProfileId/Value")
    if global_root.tag != "nhSettings" or global_root.find("Settings") is None:
        raise ValueError("Unsupported original global settings structure")
    if not default_profile or global_root.find("Data") is not None:
        raise ValueError("Missing or ambiguous original metadata")
    profiles = sorted((source / "AudioProfiles").glob("*.nsx"))
    if not profiles:
        raise ValueError("Original audio profiles are absent")
    profile_ids = {ET.parse(p).findtext("Data/ID/Value") for p in profiles}
    if default_profile not in profile_ids:
        raise ValueError("The metadata default profile is absent from the CAB")
    original_settings = ET.tostring(global_root.find("Settings"))
    data = ET.SubElement(global_root, "Data")
    default = copy.deepcopy(metadata.find("Data/DefaultProfileId"))
    default.tag = "DefaultProfileID"
    data.append(default)
    destination.mkdir(parents=True)
    global_tree.write(destination / "Global.nsx", encoding="utf-8", xml_declaration=True)
    for name in ("Devices", "AudioProfiles"):
        shutil.copytree(source / name, destination / name)
    # Preserve separate metadata for later handling of UseGlobalProfile and identity.
    shutil.copy2(source / "Metadata.nsx", destination / "Metadata.nsx")
    generated = source / "Devices.auto.json"
    if generated.is_file():
        shutil.copy2(generated, destination / generated.name)
    if ET.tostring(ET.parse(destination / "Global.nsx").find("Settings")) != original_settings:
        raise ValueError("Global setting values changed during format translation")
    manifest = {
        "translation": "Global.nsx + Metadata.nsx DefaultProfileId -> Data/DefaultProfileID",
        "originals": {
            str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source.rglob("*.nsx"))
        },
        "metadata": {e.tag: e.findtext("Value") for e in metadata.find("Data")},
    }
    (destination / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.destination)
