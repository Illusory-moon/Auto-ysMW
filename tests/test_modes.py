import threading
import unittest
from unittest.mock import patch

import weekly
from core.state_machine import run_mode
from weekly import BILI, OFFICIAL, _detect_server, _resolve_walk


class ModeTests(unittest.TestCase):
    def setUp(self):
        self.stop_event = threading.Event()

    @patch("daily.run_daily")
    def test_daily_mode_dispatches(self, run_daily):
        run_mode("daily", self.stop_event)
        run_daily.assert_called_once_with(self.stop_event)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "未知任务模式"):
            run_mode("invalid", self.stop_event)

    @patch("weekly.ops.read_uid", return_value=600_000_000)
    def test_bilibili_server_detection(self, _read_uid):
        self.assertIs(_detect_server(self.stop_event), BILI)

    @patch("weekly.ops.read_uid", return_value=100_000_000)
    def test_official_server_detection(self, _read_uid):
        self.assertIs(_detect_server(self.stop_event), OFFICIAL)

    def test_bilibili_walk_does_not_read_recording(self):
        self.assertEqual(_resolve_walk(BILI), [("w", 4.0)])

    @patch("weekly.ops.press_key")
    @patch("weekly.ops.wait")
    @patch("weekly.ops.wait_text", return_value=True)
    @patch("weekly._delete_and_select_next", return_value=True)
    @patch("weekly._in_wonderland", return_value=True)
    @patch("weekly._first_search_entry", return_value=True)
    @patch("weekly._detect_server", return_value=BILI)
    def test_weekly_keeps_sixteen_run_sequence(
        self,
        _detect,
        first_entry,
        in_wonderland,
        select_next,
        _wait_text,
        _wait,
        press_key,
    ):
        weekly.run_weekly(self.stop_event)

        first_entry.assert_called_once_with(self.stop_event, BILI)
        self.assertEqual(in_wonderland.call_count, 16)
        self.assertEqual(select_next.call_count, 15)
        in_wonderland.assert_called_with(self.stop_event, BILI)
        select_next.assert_called_with(self.stop_event, BILI)
        press_key.assert_called_once_with("f1")


if __name__ == "__main__":
    unittest.main()
