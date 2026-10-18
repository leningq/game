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

    def press(self, key):
        client.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def click(self, action):
        rect = client.ui.buttons_for_state(client.game.state)[action]
        client.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))

    def type_field(self, index, value):
        rect = client.ui.AUTH_FIELDS[index]
        client.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        client.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=value))

    def finish_request(self):
        client.pending.result(timeout=2)
        client.poll_request()

    def test_login_registration_and_screens(self):
        client.api.register = Mock(return_value={"username": "Student"})
        client.api.login = Mock(return_value={"username": "Student", "token": "test-session"})
        self.click("start")
        self.assertEqual(client.game.state, "login")
        self.type_field(0, "StudentX")
        self.press(pygame.K_BACKSPACE)
        self.press(pygame.K_TAB)
        client.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="practice-pass"))
        for action in ("register", "login", "register"):
            self.click(action)
            self.assertEqual(client.game.state, action)
            self.assertEqual(client.username_input, "Student")
            self.assertEqual(client.password_input, "practice-pass")
            self.assertEqual(client.active_field, 1)
        self.press(pygame.K_RETURN)
        self.finish_request()
        client.api.register.assert_called_once_with("Student", "practice-pass")
        client.api.login.assert_called_once_with("Student", "practice-pass")
        self.assertEqual(client.game.state, "menu")
        self.assertEqual(client.password_input, "")
        self.assertEqual(client.api.username, "Student")
        self.press(pygame.K_RETURN)
        self.assertEqual(client.game.state, "playing")
        self.assertEqual(client.game.level, 1)
        self.press(pygame.K_SPACE)
        self.assertFalse(client.game.ball_attached)
        for state in ("menu", "login", "register", "controls", "playing", "paused", "win", "game_over"):
            client.game.state = state
            client.draw()
        self.assertEqual(client.screen.get_size(), (900, 600))

    def test_duplicate_registration_and_wrong_password_allow_login(self):
        client.api.register = Mock(side_effect=ApiError("This username is already registered.", 409))
        client.api.login = Mock(side_effect=ApiError("Incorrect username or password.", 401))
        self.click("account")
        self.click("register")
        self.type_field(0, "Student")
        self.type_field(1, "wrong-password")
        self.click("auth")
        with self.assertRaises(ApiError):
            client.pending.result(timeout=2)
        client.poll_request()
        self.assertEqual(client.game.state, "login")
        self.assertIn("Sign in", client.status)
        self.assertEqual(client.username_input, "Student")
        self.assertEqual(client.password_input, "wrong-password")
        self.assertEqual(client.active_field, 1)
        self.click("auth")
        with self.assertRaises(ApiError):
            client.pending.result(timeout=2)
        client.poll_request()
        self.assertEqual(client.game.state, "login")
        self.assertTrue(client.status_error)
        self.assertIn("Incorrect username or password", client.status)
        for _ in "wrong-password":
            self.press(pygame.K_BACKSPACE)
        client.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="practice-pass"))
        client.api.login.side_effect = None
        client.api.login.return_value = {"username": "Student", "token": "test-session"}
        self.click("auth")
        self.finish_request()
        self.assertEqual(client.game.state, "menu")
        client.api.login.assert_called_with("Student", "practice-pass")
        self.click("start")
        self.assertEqual(client.game.state, "playing")
        self.assertEqual(client.game.level, 1)

    def test_pause_menu_continue_save_load(self):
        client.api.token = "test-session"
        client.api.save = Mock(return_value={})
        client.perform_action("start")
        self.press(pygame.K_SPACE)
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
        self.assertEqual(client.game.run_id, saved["run_id"])
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

    def test_pending_network_does_not_block_or_restore_cancelled_login(self):
        self.click("account")
        future = Future()
        client.pending = future
        client.pending_action = "login"
        started = time.monotonic()
        client.update(1 / 60)
        client.draw()
        self.press(pygame.K_ESCAPE)
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(client.game.state, "menu")
        self.assertFalse(future.done())
        self.assertFalse(client.require_login())
        future.set_result({"username": "Student", "token": "cancelled-session"})
        client.poll_request()
        self.assertEqual(client.game.state, "login")
        self.assertIsNone(client.api.token)
        self.assertIsNone(client.pending)

    def test_resized_window_keeps_buttons_clickable(self):
        client.api.token = "test-session"
        client.perform_action("start")
        for size, point in (((720, 480), (642, 40)),
                            ((1200, 800), (1069, 67)),
                            ((1280, 720), (1062, 60))):
            with self.subTest(size=size):
                pygame.display.set_mode(size, pygame.RESIZABLE)
                client.handle_event(pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, button=1, pos=point))
                self.assertEqual(client.game.state, "paused")
                self.assertEqual(client.screen.get_size(), (900, 600))
                client.draw()
                client.present()
                client.perform_action("resume")

    def test_unavailable_server_has_clear_error(self):
        api = ApiClient("http://127.0.0.1:1", timeout=0.2)
        with self.assertRaisesRegex(ApiError, "Server unavailable.*separate terminal"):
            api.login("Student", "practice-pass")


if __name__ == "__main__":
    unittest.main()
