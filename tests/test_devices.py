"""Speaker hardware matching from devices.json."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
import devices


def sink(components, port='[Out] Speaker'):
    return {'active_port': port, 'properties': {'alsa.components': components}}


class DevicesTest(unittest.TestCase):
    def setUp(self):
        self.table = devices.load(user_path=None)
        self.temporary = tempfile.mkdtemp()
        self.addCleanup(__import__('shutil').rmtree, self.temporary, True)

    def test_original_senary_speakers(self):
        entry = devices.match(sink('HDA:14f11f87,1d05e022,00100100'), self.table)
        self.assertTrue(entry['verified'])

    def test_intel_dsp_sink_listing_several_codecs(self):
        # Intel SOF/DSP machines list the HDMI codec first; the analog codec must still match.
        real = 'HDA:8086281c,80860101,00100000 HDA:10ec0256,1c05c022,00100002 cfg-dmics:2'
        self.assertEqual(devices.match(sink(real), self.table)['codec'], '10ec0256')
        hdmi = 'HDA:8086281c,80860101,00100000 HDA:10ec0256,1462139b,00100002 cfg-dmics:2'
        self.assertIsNone(devices.match(sink(hdmi, '[Out] HDMI3'), self.table))
        self.assertIsNone(devices.match(sink(hdmi), self.table))

    def test_realtek_alc256_speakers_on_both_port_names(self):
        for port in ('[Out] Speaker', 'analog-output-speaker'):
            entry = devices.match(sink('HDA:10ec0256,1c05c022,00100002 HDA:8086280b,80860101,00100000', port), self.table)
            self.assertEqual(entry['codec'], '10ec0256')
            self.assertFalse(entry['verified'])

    def test_msi_alc274_speakers_on_intel_sof(self):
        # MSI Stealth 14 Studio A13VF: Realtek ALC274 behind Intel SOF, subsystem 146213c0.
        real = 'HDA:8086281f,80860101,00100000 HDA:10ec0274,146213c0,00100004 cfg-dmics:2'
        entry = devices.match(sink(real), self.table)
        self.assertEqual(entry['codec'], '10ec0274')
        self.assertEqual(entry['device_file'], 'Devices/146213C0_InternalSpeakers.nsx')
        # The HDMI endpoints of the same laptop share the subsystem and must not match.
        self.assertIsNone(devices.match(sink('HDA:10de00a7,146213c0,00100100'), self.table))
        self.assertIsNone(devices.match(sink('HDA:8086281f,80860101,00100000 HDA:10ec0274,146213c0,00100004',
                                             '[Out] HDMI3'), self.table))

    def write(self, name, payload):
        path = Path(self.temporary) / name
        path.write_text(json.dumps(payload))
        return path

    def test_generated_table_matches_by_subsystem_only(self):
        # The installer derives entries from vendor cabinets; they carry no codec.
        generated = self.write('Devices.auto.json', {"devices": [{
            "name": "146213C0 InternalSpeakers",
            "subsystem": "146213c0",
            "device_file": "Devices/146213C0_InternalSpeakers.nsx",
            "verified": False,
        }]})
        table = devices.load(user_path=Path(self.temporary) / "missing.json", generated=generated)
        entry = devices.match(sink('HDA:8086281f,80860101,00100000 HDA:10ec0287,146213c0,00100004'),
                              table)
        self.assertEqual(entry['device_file'], 'Devices/146213C0_InternalSpeakers.nsx')

    def test_curated_table_wins_over_the_generated_one(self):
        generated = self.write('Devices.auto.json', {"devices": [{
            "name": "146213C0 InternalSpeakers",
            "subsystem": "146213c0",
            "device_file": "Devices/146213C0_InternalSpeakers.nsx",
            "verified": False,
        }]})
        generated = self.write('Devices.auto.json', {"devices": [{
            "name": "146213C0 InternalSpeakers",
            "subsystem": "146213c0",
            "device_file": "Devices/146213C0_InternalSpeakers.nsx",
        }]})
        table = devices.load(user_path=Path(self.temporary) / "missing.json", generated=generated)
        entry = devices.match(sink('HDA:10ec0274,146213c0,00100004'), table)
        self.assertEqual(entry['name'], 'MSI Stealth 14 Studio A13VF (Realtek ALC274, Intel SOF)')

    def test_user_table_wins_over_everything(self):
        local = self.write('local.json', {"devices": [{
            "name": "Mine", "codec": "10ec0274", "subsystem": "146213c0",
            "device_file": "/home/user/tuning.nsx",
        }]})
        table = devices.load(user_path=local)
        self.assertEqual(devices.match(sink('HDA:10ec0274,146213c0,00100004'), table)['name'], 'Mine')

    def test_entries_need_an_identifier(self):
        broken = self.write('broken.json', {"devices": [{"name": "No id", "device_file": "x.nsx"}]})
        with self.assertRaises(ValueError):
            devices.load(user_path=broken)

    def test_other_codecs_and_ports_are_rejected(self):
        self.assertIsNone(devices.match(sink('HDA:10ec0257,17aa3801,00100001'), self.table))
        self.assertIsNone(devices.match(sink('HDA:14f11f87,deadbeef,00100100'), self.table))
        self.assertIsNone(devices.match(sink('HDA:10ec0256,1c05c022,00100002', '[Out] Headphones'), self.table))
        self.assertIsNone(devices.match(sink('HDA:10ec0256,deadbeef,00100002'), self.table))
        self.assertIsNone(devices.match({'active_port': '[Out] Speaker'}, self.table))

    def test_user_entries_take_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'devices.json'
            path.write_text(json.dumps({'devices': [{'name': 'Mine', 'codec': '10ec0256',
                                                     'subsystem': None, 'device_file': '/x.nsx'}]}))
            table = devices.load(user_path=path)
            self.assertEqual(devices.match(sink('HDA:10ec0256,1c05c022,0'), table)['name'], 'Mine')
            self.assertEqual(devices.match(sink('HDA:10ec0256,11111111,0'), table)['name'], 'Mine')


if __name__ == '__main__': unittest.main()
