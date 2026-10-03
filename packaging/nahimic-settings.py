"""Read Nahimic settings from a Windows installation and seed them into the prefix.

The virtual surround of Nahimic is driven by a spatial filter database that the
Windows application hands to the driver at runtime, so it is not part of the
driver package. This tool reads it back from an installed copy of Nahimic and
writes it into the Wine prefix that the service uses.

    python3 packaging/nahimic-settings.py extract --windows /mnt/win11 --output extra
    python3 packaging/nahimic-settings.py seed --extra extra

Both steps are optional: without them the service falls back to the settings that
the driver package carries.
"""
import argparse
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

# The product folder carries the vendor name, so match the settings path only.
GLOBAL_STORE_SUFFIX = r'\NahimicSettings\GlobalControl\Store'
FILTER_VALUE = 'kSet_Hp3DDatabaseFilter'
COUNT_VALUE = 'kSet_Hp3DDatabaseFilterCount'


def windows_candidates(root):
    """Yield the Nahimic settings hives of a mounted Windows installation."""
    yield Path(root) / 'Windows/System32/config/SOFTWARE'
    users = Path(root) / 'Users'
    if users.is_dir():
        for profile in sorted(users.iterdir()):
            if profile.is_dir():
                yield profile / 'NTUSER.DAT'


def export_hive(hive, output):
    """Export the Nahimic subtree of a registry hive next to output, or return None."""
    if not hive.is_file():
        return None
    work = output.with_suffix('.hive')
    shutil.copyfile(hive, work)
    work.chmod(0o644)
    exported = output.with_suffix('.partial.reg')
    result = subprocess.run(
        ['reged', '-x', str(work), 'HKEY_LOCAL_MACHINE\\SOFTWARE', '\\Nahimic', str(exported)],
        capture_output=True, text=True,
    )
    work.unlink(missing_ok=True)
    if result.returncode:
        print(result.stderr.strip() or f'reged failed with {result.returncode}')
        return None
    return exported if exported.is_file() and exported.stat().st_size else None


def registry_values(path, suffix):
    """Return the values of the first key of an exported .reg file ending with suffix."""
    text = path.read_text(encoding='utf-8', errors='replace')
    match = re.search(r'^\[HKEY[^\]]*' + re.escape(suffix) + r'\]$', text, re.MULTILINE)
    if match is None:
        return {}
    end = text.find('\n[HKEY', match.end())
    lines = text[match.end():end if end > 0 else len(text)].splitlines()
    values, position = {}, 0
    while position < len(lines):
        line = lines[position]
        match = re.match(r'"([^"]+)"=dword:(?:0x)?([0-9a-fA-F]+)', line)
        if match:
            values[match.group(1)] = struct.pack('<I', int(match.group(2), 16))
            position += 1
            continue
        match = re.match(r'"([^"]+)"=hex:(.*)$', line)
        if match:
            data = match.group(2)
            position += 1
            while data.rstrip().endswith('\\') and position < len(lines):
                data = data.rstrip()[:-1] + lines[position].strip()
                position += 1
            values[match.group(1)] = bytes.fromhex(data.replace(',', '').replace('\\', ''))
            continue
        position += 1
    return values


def extract(arguments):
    output = arguments.output
    output.mkdir(parents=True, exist_ok=True)
    for hive in windows_candidates(arguments.windows):
        print(f'inspecting {hive}')
        exported = export_hive(hive, output / hive.name)
        if exported is None:
            print('  no Nahimic settings in this hive')
            continue
        values = registry_values(exported, GLOBAL_STORE_SUFFIX)
        if FILTER_VALUE not in values:
            print('  no spatial filter in this hive')
            continue
        blob = values[FILTER_VALUE]
        count = struct.unpack('<I', values[COUNT_VALUE])[0] if COUNT_VALUE in values else len(blob)
        (output / '3d-database.bin').write_bytes(blob)
        print(f'  wrote {output / "3d-database.bin"} ({len(blob)} bytes, count {count})')
        (output / '3d-database.count').write_text(f'{count}\n')
        shutil.move(str(exported), str(output / 'nahimic-windows.reg'))
        print(f'  kept the full settings dump at {output / "nahimic-windows.reg"}')
        return 0
    print('no Nahimic spatial filter found; nothing to extract')
    return 1


def seed(arguments):
    blob = arguments.blob
    count = arguments.count
    if arguments.extra:
        blob = arguments.extra / '3d-database.bin'
        stored = arguments.extra / '3d-database.count'
        if stored.is_file():
            count = int(stored.read_text().strip())
    if blob is None or not blob.is_file():
        print(f'no spatial filter at {blob}; run the extract step first')
        return 1
    prefix = arguments.prefix
    if not prefix.is_dir():
        print(f'the Wine prefix {prefix} does not exist; install and activate first')
        return 1
    seeder = arguments.seeder
    if not seeder.is_file():
        print(f'{seeder} is missing; run make first')
        return 1
    payload = blob.read_bytes()
    print(f'seeding {len(payload)} bytes into {prefix}')
    environment = {'WINEPREFIX': str(prefix), 'WINEDEBUG': arguments.wine_debug}
    result = subprocess.run(
        ['wine', str(seeder), str(blob), str(count)], env=environment, check=False,
    )
    if result.returncode == 0:
        print('restart the service to load the spatial filter: systemctl --user restart nahimic.service')
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    read = commands.add_parser('extract', help='read the filter from a Windows installation')
    read.add_argument('--windows', type=Path, required=True, help='mount point of the Windows partition')
    read.add_argument('--output', type=Path, default=Path('extra'), help='directory for the extracted data')
    write = commands.add_parser('seed', help='write the filter into the Wine prefix')
    write.add_argument('--extra', type=Path, default=Path('extra'),
                       help='directory produced by the extract step')
    write.add_argument('--blob', type=Path, help='spatial filter file, overrides --extra')
    write.add_argument('--count', type=int, default=0, help='filter count, read from --extra by default')
    write.add_argument('--prefix', type=Path,
                       default=Path.home() / '.local/share/nahimic-linux/runtime/prefix')
    write.add_argument('--seeder', type=Path, default=Path('bin/seed3d.exe'))
    write.add_argument('--wine-debug', default='-all')
    arguments = parser.parse_args()
    return extract(arguments) if arguments.command == 'extract' else seed(arguments)


if __name__ == '__main__':
    sys.exit(main())