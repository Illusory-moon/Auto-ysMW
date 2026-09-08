import threading
import unittest
from unittest.mock import Mock, call, patch

import daily
import weekly


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.stop = threading.Event()
        self.ops_patch = patch("daily.ops", autospec=True)
        self.ops = self.ops_patch.start()
        self.addCleanup(self.ops_patch.stop)
        self.ops.wait_text.return_value = True
        self.ops.wait_pattern.return_value = True
        self.return_patch = patch("weekly._return_to_lobby", return_value=True)
        self.return_lobby = self.return_patch.start()
        self.addCleanup(self.return_patch.stop)

    def test_first_challenge_normal(self):
        self.assertTrue(daily._first_challenge(self.stop))
        self.ops.click_point.assert_not_called()
        self.ops.wait.assert_called_once_with(60.0, self.stop)
        self.ops.press_key.assert_called_once_with("esc")
        self.assertEqual(self.ops.click_box.call_args_list, [
            call(daily.START_CHALLENGE), call(daily.INTERRUPT_CHALLENGE),
        ])
        self.return_lobby.assert_called_once_with(self.stop)

    def test_missing_character_retries_once(self):
        self.ops.wait_pattern.side_effect = [False, True]
        self.assertTrue(daily._first_challenge(self.stop))
        self.assertEqual(self.ops.click_point.call_args_list, [
            call(*point) for point in daily.CHARACTER_POINTS
        ])
        self.assertEqual(self.ops.click_box.call_args_list, [
            call(daily.START_CHALLENGE), call(daily.START_CHALLENGE),
            call(daily.INTERRUPT_CHALLENGE),
        ])

    def test_retry_failure_does_not_interrupt_or_return(self):
        self.ops.wait_pattern.return_value = False
        self.assertFalse(daily._first_challenge(self.stop))
        self.assertEqual(self.ops.wait_pattern.call_count, 2)
        self.ops.press_key.assert_not_called()
        self.return_lobby.assert_not_called()

    def test_unknown_screen_does_not_select_character(self):
        self.ops.wait_pattern.return_value = False
        self.ops.wait_text.side_effect = [True, False]
        self.assertFalse(daily._first_challenge(self.stop))
        self.ops.click_point.assert_not_called()

    def test_stop_during_idle_does_not_press_escape(self):
        self.ops.wait.side_effect = lambda *_: self.stop.set()
        self.assertFalse(daily._first_challenge(self.stop))
        self.ops.press_key.assert_not_called()
        self.return_lobby.assert_not_called()

    def test_two_levels_in_order_for_both_servers(self):
        for server in (weekly.OFFICIAL, weekly.BILI):
            with self.subTest(server=server.name), \
                    patch("weekly._detect_server", return_value=server), \
                    patch("weekly._first_search_entry", return_value=True) as search, \
                    patch("daily._first_challenge", return_value=True) as first, \
                    patch("daily._wait_for_lobby", return_value=True) as lobby, \
                    patch("weekly._in_wonderland", return_value=True) as second:
                sequence = Mock()
                for name, mock in (("search", search), ("first", first),
                                   ("lobby", lobby), ("second", second)):
                    sequence.attach_mock(mock, name)
                daily.run_daily(self.stop)
                config = search.call_args_list[0].args[1]
                self.assertEqual(config.search_guid, daily.FIRST_GUIDS[server.name])
                self.assertEqual(config.enter_box, weekly.START_GAME)
                self.assertEqual(sequence.mock_calls, [
                    call.search(self.stop, config), call.first(self.stop),
                    call.lobby(self.stop), call.search(self.stop, server),
                    call.second(self.stop, server), call.lobby(self.stop),
                ])

    def test_first_failure_never_searches_second(self):
        with patch("weekly._detect_server", return_value=weekly.OFFICIAL), \
                patch("weekly._first_search_entry", return_value=True) as search, \
                patch("daily._first_challenge", return_value=False), \
                patch("weekly._in_wonderland") as second:
            daily.run_daily(self.stop)
            self.assertEqual(search.call_count, 1)
            second.assert_not_called()


if __name__ == "__main__":
    unittest.main()
