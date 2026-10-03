import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

MODULE = importlib.util.spec_from_file_location(
    'nahimic_settings', Path(__file__).with_name('..') / 'packaging' / 'nahimic-settings.py')
nahimic_settings = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(nahimic_settings)

EXPORT = """Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\\SOFTWARE\\Nahimic\\NahimicAPO4\\A-Voluteinternal\\Other]
"Skip"="me"

[HKEY_LOCAL_MACHINE\\SOFTWARE\\Nahimic\\NahimicAPO4\\A-Voluteinternal\\NahimicSettings\\GlobalControl\\Store]
"kSet_RenderState"=dword:00000001
"kSet_Hp3DDatabaseFilterCount"=dword:00025150
"kSet_Hp3DDatabaseFilter"=hex:64,62,0a,00,01,02,\\
  03,04,ff,ff\\
,ff,ee\\
"""


def build_export(vendor):
    return EXPORT.replace('A-Voluteinternal', vendor)


class RegistryParsingTest(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'nahimic.reg'
            path.write_text(text, encoding='utf-8')
            return nahimic_settings.registry_values(path, nahimic_settings.GLOBAL_STORE_SUFFIX)

    def test_binary_and_dword_values_are_decoded(self):
        values = self.read(EXPORT)
        self.assertEqual(len(values['kSet_Hp3DDatabaseFilter']), 12)
        self.assertEqual(values['kSet_Hp3DDatabaseFilter'][:4], b'db\n\x00')
        self.assertEqual(struct.unpack('<I', values['kSet_Hp3DDatabaseFilterCount'])[0], 0x25150)
        self.assertEqual(struct.unpack('<I', values['kSet_RenderState'])[0], 1)

    def test_dword_with_hex_prefix_is_accepted(self):
        text = EXPORT.replace('dword:00000001', 'dword:0x00000001')
        values = self.read(text)
        self.assertEqual(struct.unpack('<I', values['kSet_RenderState'])[0], 1)

    def test_windows_line_endings_are_accepted(self):
        values = self.read(EXPORT.replace('\n', '\r\n'))
        self.assertEqual(len(values['kSet_Hp3DDatabaseFilter']), 12)
        self.assertEqual(struct.unpack('<I', values['kSet_Hp3DDatabaseFilterCount'])[0], 0x25150)

    def test_the_vendor_directory_name_does_not_matter(self):
        for vendor in ('A-Voluteinternal', 'A-Voluteinteger', 'A-Voluteon'):
            values = self.read(build_export(vendor))
            self.assertIn(nahimic_settings.FILTER_VALUE, values, vendor)

    def test_other_keys_are_ignored(self):
        self.assertEqual(self.read(EXPORT.split('GlobalControl')[0]), {})


class WindowsLayoutTest(unittest.TestCase):
    def test_only_user_profiles_are_inspected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'Users' / 'mahdi').mkdir(parents=True)
            (root / 'Users' / 'Public').mkdir(parents=True)
            (root / 'Users' / 'desktop.ini').write_text('')
            (root / 'Windows' / 'System32' / 'config').mkdir(parents=True)
            candidates = [path.name for path in nahimic_settings.windows_candidates(root)]
        self.assertEqual(candidates, ['SOFTWARE', 'NTUSER.DAT', 'NTUSER.DAT'])


if __name__ == '__main__':
    unittest.main()