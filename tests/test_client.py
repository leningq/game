import os
import time
import unittest
from concurrent.futures import Future
from unittest.mock import Mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from client import main as client
from client.api_client import ApiClient, ApiError


class ClientTests(unittest.TestCase):
    def setUp(self):
        client.api = ApiClient()
        client.initialize()

    def tearDown(self):
        client.shutdown()

    def finish_request(self):
        # Ждём только фоновую тестовую функцию, затем обрабатываем результат в окне.
        client.pending.result(timeout=2)
        client.poll_request()

    def test_login_registration_and_screens(self):
        client.api.register = Mock(return_value={"username": "Student"})
        client.api.login = Mock(return_value={"username": "Student", "token": "test-session"})
        client.perform_action("start")
        self.assertEqual(client.game.state, "login")
        client.perform_action("register")
        client.username_input, client.password_input = "Student", "practice-pass"
        client.submit_auth()
        self.finish_request()
        self.assertEqual(client.game.state, "login")
        self.assertEqual(client.password_input, "")
        client.password_input = "practice-pass"
        client.submit_auth()
        self.finish_request()
        self.assertEqual(client.game.state, "menu")
        client.perform_action("start")
        self.assertEqual(client.game.state, "playing")
        self.assertEqual(client.api.username, "Student")
        for state in ("menu", "login", "register", "controls", "playing", "paused", "win", "game_over"):
            client.game.state = state
            client.draw()
        self.assertEqual(client.screen.get_size(), (900, 600))

    def test_pause_menu_continue_save_load(self):
        client.api.token = "test-session"
        client.api.save = Mock(return_value={})
        client.perform_action("start")
        client.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertFalse(client.game.ball_attached)
        client.perform_action("menu")
        self.assertEqual(client.game.state, "paused")
        client.perform_action("save")
        self.finish_request()
        saved = client.api.save.call_args.args[0]
        client.perform_action("menu")
        self.assertEqual(client.game.state, "menu")
        client.perform_action("continue")
        self.assertEqual(client.game.state, "playing")
        client.api.load = Mock(return_value=saved)
        client.perform_action("pause")
        client.perform_action("load")
        self.finish_request()
        self.assertEqual(client.game.state, "paused")
        self.assertEqual(client.game.run_id, saved["run_id"])

    def test_result_sent_once_and_explicit_retry(self):
        client.api.token = "test-session"
        client.api.send_score = Mock(side_effect=ApiError("Server unavailable."))
        client.perform_action("start")
        client.game.state = "game_over"
        client.update(1 / 60)
        with self.assertRaises(ApiError):
            client.pending.result(timeout=2)
        client.poll_request()
        for _ in range(20):
            client.update(1 / 60)
        self.assertEqual(client.api.send_score.call_count, 1)
        self.assertEqual(client.score_state, "error")
        client.api.send_score.side_effect = None
        client.api.send_score.return_value = {}
        client.perform_action("send_score")
        self.finish_request()
        self.assertEqual(client.score_state, "saved")
        self.assertEqual(client.api.send_score.call_count, 2)

    def test_pending_network_does_not_block_frame_or_menu(self):
        client.pending = Future()
        client.pending_action = "login"
        client.game.state = "login"
        started = time.monotonic()
        client.update(1 / 60)
        client.draw()
        client.perform_action("menu")
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(client.game.state, "menu")
        self.assertFalse(client.pending.done())

    def test_unavailable_server_has_clear_error(self):
        api = ApiClient("http://127.0.0.1:1", timeout=0.2)
        with self.assertRaisesRegex(ApiError, "Server unavailable"):
            api.login("Student", "practice-pass")


if __name__ == "__main__":
    unittest.main()