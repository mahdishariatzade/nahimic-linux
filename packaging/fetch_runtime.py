"""Download the runtime components and extract the verified runtime tree."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import urllib.request

from extract_runtime import extract

HERE = Path(__file__).parent


def download(url, target, expected):
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        print(f"cached {target.name}")
        return
    print(f"fetching {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "nahimic-linux"})
    with urllib.request.urlopen(request) as response, tempfile.NamedTemporaryFile(
        dir=target.parent, delete=False
    ) as handle:
        while chunk := response.read(1 << 20):
            handle.write(chunk)
        temporary = Path(handle.name)
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    if digest != expected:
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"checksum mismatch for {url}: {digest}")
    temporary.replace(target)
    print(f"verified {target.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=HERE / "dist")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    sources = json.loads((HERE / "runtime-sources.json").read_text())["components"]
    arguments.cache.mkdir(parents=True, exist_ok=True)
    cached = {}
    for component in sources:
        target = arguments.cache / component["file"]
        download(component["url"], target, component["sha256"])
        cached[component["name"]] = target
    extract(cached["nahimic-apo4"], cached["nahimic-runtime-settings"], arguments.output)
    print(f"runtime tree ready in {arguments.output}")


if __name__ == "__main__":
    sys.exit(main())