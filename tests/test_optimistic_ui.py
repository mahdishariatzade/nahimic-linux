"""Delayed replies, failures and rapid edits must not overwrite newer UI intent."""
import copy
from concurrent.futures import Future
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from PySide6.QtWidgets import QApplication
from main import Panel

class ManualExecutor:
    def __init__(self, **kwargs): self.calls = {}
    def submit(self, function):
        future = Future(); self.calls[future] = function; return future
    def shutdown(self, **kwargs): pass

class AudioBackend:
    def __init__(self):
        self.data = {'profile':'Music', 'settings':{}}
        self.state = {'ready':True,'service':'active','autostart':True,'instance':1,
                      'enabled':True,'active':True,'volume':50,'muted':False}
        self.writes = []
        self.reject = None
    def status(self): return copy.deepcopy(self.state)
    def settings(self): return copy.deepcopy(self.data)
    def set_setting(self, key, value):
        self.writes.append((key,value))
        if self.reject == key: raise RuntimeError('device rejected write')
        self.data['settings'][key]['value'] = value
        return self.settings()
    def profile(self, value):
        if self.reject == 'profile': raise RuntimeError('profile rejected')
        self.data['profile']=value
        for key,item in self.data['settings'].items():
            if 'GainDB' in key: item['value'] = 2
        return self.settings()
    def mute(self, value): self.state['muted']=value
    def volume(self, value): self.state['volume']=value
    def enabled(self, value): self.state['enabled']=value
    def autostart(self, value): self.state['autostart']=value

class OptimisticUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        with patch('main.Backend', AudioBackend), patch('main.ThreadPoolExecutor', ManualExecutor):
            self.panel = Panel()
        p=self.panel;p.timer.stop();p.status_timer.stop()
        for name in p.values:
            p.backend.data['settings'][name]={'min':-12,'max':12,'value':0}
        for name in p.switches:
            p.backend.data['settings'][name]={'min':0,'max':1,'value':1}
        self.drain()
    def tearDown(self):
        self.panel.busy_timer.stop();self.panel.close();self.panel.deleteLater()
    def finish(self, result=None):
        p=self.panel;future=p.pending[0]
        try: future.set_result(p.pool.calls.pop(future)() if result is None else result)
        except Exception as error: future.set_exception(error)
        p.poll()
    def drain(self):
        for _ in range(20):
            if self.panel.pending is None: return
            self.finish()
        self.fail('queue failed to settle')
    def edit(self, value, key='kSet_BassBoostGainDB'):
        slider=self.panel.values[key];slider.setValue(value);slider.sliderReleased.emit()

    def test_rapid_edits_coalesce_without_disabling_or_rolling_back(self):
        p=self.panel;self.edit(4);self.edit(7);self.edit(9)
        self.assertTrue(p.controls.isEnabled());self.assertTrue(p.equalizer.isEnabled())
        self.assertEqual(len(p.jobs),1)
        self.finish()
        self.assertEqual(p.values['kSet_BassBoostGainDB'].value(),9)
        self.drain()
        self.assertEqual(p.backend.writes,[('kSet_BassBoostGainDB',4),('kSet_BassBoostGainDB',9)])
        self.assertEqual(p.values['kSet_BassBoostGainDB'].value(),9)

    def test_status_started_before_click_cannot_revert_mute(self):
        p=self.panel;p.refresh();old=p.backend.status();p.mute.click()
        self.finish(old)
        self.assertTrue(p.mute.isChecked());self.assertTrue(p.controls.isEnabled())
        self.drain();self.assertTrue(p.mute.isChecked());self.assertFalse(p.awaiting_state)

    def test_failed_setting_is_read_back_and_error_remains_visible(self):
        p=self.panel;p.backend.reject='kSet_BassBoostGainDB';self.edit(9)
        self.assertEqual(p.values['kSet_BassBoostGainDB'].value(),9)
        self.drain()
        self.assertEqual(p.values['kSet_BassBoostGainDB'].value(),0)
        self.assertIn('device rejected write',p.status.text());self.assertTrue(p.controls.isEnabled())
        p.refresh();self.drain();self.assertIn('device rejected write',p.status.text())

    def test_profile_is_a_barrier_and_older_reply_cannot_change_selection(self):
        p=self.panel;self.edit(4);p.modes['Movie'].click();self.edit(8)
        self.finish();self.assertTrue(p.modes['Movie'].isChecked())
        self.finish();self.assertEqual(p.values['kSet_BassBoostGainDB'].value(),8)
        self.drain();self.assertEqual(p.backend.data['profile'],'Movie')
        self.assertEqual(p.backend.data['settings']['kSet_BassBoostGainDB']['value'],8)

    def test_failed_profile_does_not_write_parameters_to_the_previous_profile(self):
        p=self.panel;p.backend.reject='profile';p.modes['Movie'].click();self.edit(8)
        self.drain();self.assertTrue(p.modes['Music'].isChecked());self.assertEqual(p.backend.writes,[])
        self.assertIn('profile rejected',p.status.text())

    def test_readback_during_drag_preserves_the_active_slider(self):
        p=self.panel;slider=p.values['kSet_BassBoostGainDB']
        slider.setSliderDown(True);slider.setValue(10)
        p.apply_settings(p.backend.settings());self.assertEqual(slider.value(),10)
        slider.setSliderDown(False);self.drain();self.assertEqual(slider.value(),10)

    def test_unconfirmed_system_change_expires_and_shows_actual_state(self):
        p=self.panel;p.mute.setChecked(True);p.awaiting_state['muted']=(True,0)
        p.apply_status(p.backend.status())
        self.assertFalse(p.mute.isChecked());self.assertTrue(p.error_message)
        self.assertNotIn('muted',p.awaiting_state)

    def test_apply_settings_with_missing_keys_does_not_crash(self):
        p = self.panel
        # Should not raise KeyError when settings dictionary is incomplete
        p.apply_settings({'profile': 'Music', 'settings': {}})
        self.assertTrue(p.settings_loaded)

if __name__ == '__main__': unittest.main()
