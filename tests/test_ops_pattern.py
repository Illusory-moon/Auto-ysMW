import threading
import unittest
from unittest.mock import call, patch

import weekly
from app import ops
from app.ocr import TextLine


class PatternTests(unittest.TestCase):
    @patch("app.ops._game_rect", return_value=(320, 274, 2240, 1354))
    @patch("app.ops.scan_text")
    def test_full_window_recovers_reported_hp(self, scan, _rect):
        scan.side_effect = [[], [TextLine("17332/17332", (904, 1001, 1021, 1020), 0.99)]]
        self.assertTrue(ops.wait_pattern(
            weekly.HP_PATTERN, weekly.HP_BOX, timeout=0, full_window_fallback=True,
        ))
        self.assertEqual(scan.call_args_list, [
            call(region=(1176, 1236, 1386, 1335)),
            call(region=(320, 274, 2240, 1354)),
        ])

    @patch("app.ops._game_rect", return_value=(320, 274, 2240, 1354))
    @patch("app.ops.scan_text")
    def test_unrelated_fraction_outside_hp_is_rejected(self, scan, _rect):
        scan.side_effect = [[], [TextLine("17332/17332", (100, 100, 200, 130), 0.99)]]
        self.assertFalse(ops.wait_pattern(
            weekly.HP_PATTERN, weekly.HP_BOX, timeout=0, full_window_fallback=True,
        ))

    @patch("app.ops._game_rect", return_value=(0, 0, 1920, 1080))
    @patch("app.ops.scan_text")
    def test_stop_during_scan_prevents_fallback(self, scan, _rect):
        stop = threading.Event()

        def cancel(**_kwargs):
            stop.set()
            return []

        scan.side_effect = cancel
        self.assertFalse(ops.wait_pattern(
            weekly.HP_PATTERN, weekly.HP_BOX, stop_event=stop, full_window_fallback=True,
        ))
        self.assertEqual(scan.call_count, 1)


if __name__ == "__main__":
    unittest.main()
