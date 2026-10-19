"""Capture chain helpers of the launcher."""
import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
MODULE = importlib.util.spec_from_file_location(
    'run_local', Path(__file__).with_name('..') / 'host' / 'run_local.py')
run_local = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(run_local)

LISTING = """speaker:playback_FL
  |<- effect_render:output_FL
speaker:playback_FR
  |<- effect_render:output_FR
"""


class EdgesTest(unittest.TestCase):
    def test_pairs_follow_the_direction_of_the_pipe(self):
        # pw-link prints "|->" under the sending node and "|<-" under the
        # receiving one; both have to end up as the same directed pair.
        self.assertEqual(run_local._edges(LISTING), {
            ('effect_render:output_FL', 'speaker:playback_FL'),
            ('effect_render:output_FR', 'speaker:playback_FR'),
        })


class SetPipeSizeTest(unittest.TestCase):
    def test_set_pipe_size_expands_pipe_buffer(self):
        import fcntl, os
        r, w = os.pipe()
        try:
            self.assertEqual(fcntl.fcntl(r, fcntl.F_GETPIPE_SZ), 65536)
            run_local.set_pipe_size(r, 262144)
            self.assertEqual(fcntl.fcntl(r, fcntl.F_GETPIPE_SZ), 262144)
            self.assertEqual(fcntl.fcntl(w, fcntl.F_GETPIPE_SZ), 262144)
        finally:
            os.close(r)
            os.close(w)

    def test_set_pipe_size_handles_none_and_invalid_fd_gracefully(self):
        run_local.set_pipe_size(None)
        run_local.set_pipe_size(-1)


if __name__ == '__main__':
    unittest.main()