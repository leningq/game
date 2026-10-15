import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from urllib.request import urlopen

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from client import main as client
from client.api_client import ApiClient, ApiError
from game.logic import BALL_RADIUS, FIELD_BOTTOM


class IntegrationTests(unittest.TestCase):
    def click(self, action):
        rect = client.ui.buttons_for_state(client.game.state)[action]
        client.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))

    def press(self, key):
        client.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def type_field(self, index, value, clear=False):
        rect = client.ui.AUTH_FIELDS[index]
        client.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        if clear:
            previous = client.username_input if index == 0 else client.password_input
            for _ in previous:
                self.press(pygame.K_BACKSPACE)
        client.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=value))

    def finish_request(self):
        client.pending.result(timeout=5)
        client.poll_request()

    def test_real_http_server_and_pygame_client(self):
        # Полный путь через события Pygame и настоящий HTTP, с временной базой.
        with tempfile.TemporaryDirectory() as folder:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            database_path = Path(folder) / "live.sqlite3"
            environment = dict(os.environ, BRICKFALL_DB_PATH=str(database_path))
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "api.main:app",
                 "--host", "127.0.0.1", "--port", str(port), "--log-level", "error"],
                cwd=Path(__file__).resolve().parents[1], env=environment,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            api = ApiClient(f"http://127.0.0.1:{port}", timeout=1)
            try:
                deadline = time.monotonic() + 10
                while True:
                    if process.poll() is not None:
                        self.fail("FastAPI failed to start.")
                    try:
                        if api.request("GET", "/scores/top") == []:
                            break
                    except Exception:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.05)
                client.api = api
                client.initialize()
                self.click("start")
                self.click("register")
                self.type_field(0, "LivePlayer")
                self.type_field(1, "school-practice")
                self.click("auth")
                self.finish_request()
                self.assertEqual(client.game.state, "menu")
                self.assertEqual(api.username, "LivePlayer")
                self.assertTrue(api.token)
                first_token = api.token
                self.click("start")
                self.assertEqual(client.game.state, "playing")
                self.assertEqual(client.game.level, 1)
                self.press(pygame.K_SPACE)
                self.assertFalse(client.game.ball_attached)
                self.press(pygame.K_ESCAPE)
                self.press(pygame.K_ESCAPE)
                self.click("account")
                self.assertIsNone(api.token)
                # Тот же аккаунт входит повторно; регистр имени не имеет значения.
                self.click("account")
                self.type_field(0, "liveplayer", clear=True)
                self.type_field(1, "school-practice")
                self.press(pygame.K_RETURN)
                self.finish_request()
                self.assertEqual(client.game.state, "menu")
                self.assertEqual(api.username, "LivePlayer")
                self.assertNotEqual(api.token, first_token)
                with self.assertRaises(ApiError) as duplicate:
                    api.register("liveplayer", "school-practice")
                self.assertEqual(duplicate.exception.status_code, 409)
                with self.assertRaises(ApiError) as incorrect:
                    api.login("LivePlayer", "wrong-password")
                self.assertEqual(incorrect.exception.status_code, 401)
                self.click("start")
                self.assertEqual(client.game.state, "playing")
                self.assertEqual(client.game.level, 1)
                self.press(pygame.K_SPACE)
                self.press(pygame.K_LSHIFT)
                client.game.update(1 / 60)
                run_id = client.game.run_id
                self.press(pygame.K_F5)
                self.finish_request()
                client.perform_action("menu")
                self.press(pygame.K_F9)
                self.finish_request()
                self.assertEqual(client.game.state, "paused")
                self.assertEqual(client.game.run_id, run_id)
                self.assertTrue(client.game.slow_used)
                self.press(pygame.K_p)
                for _ in range(3):
                    client.game.launch_ball()
                    client.game.ball_y = FIELD_BOTTOM + BALL_RADIUS + 5
                    client.game.ball_speed_y = 360
                    client.update(1 / 60)
                self.assertEqual(client.game.state, "game_over")
                self.finish_request()
                self.assertEqual(client.score_state, "saved")
                self.assertEqual(api.request("GET", "/scores/top"), [{"name": "LivePlayer", "score": 0}])
                self.assertEqual(api.request("GET", "/players/LivePlayer/stats")["games"], 1)
                with urlopen(api.base_url + "/", timeout=2) as response:
                    self.assertIn("LivePlayer", response.read().decode("utf-8"))
                for path in ("/players/LivePlayer", "/rules"):
                    with urlopen(api.base_url + path, timeout=2) as response:
                        self.assertEqual(response.status, 200)
                with closing(sqlite3.connect(database_path)) as database:
                    self.assertEqual(database.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
                    self.assertEqual(database.execute("SELECT score FROM scores").fetchone()[0], 0)
                client.draw()
                process.terminate()
                process.wait(timeout=5)
                self.click("menu")
                self.click("account")
                self.click("account")
                self.type_field(1, "school-practice")
                self.click("auth")
                with self.assertRaises(ApiError):
                    client.pending.result(timeout=5)
                client.poll_request()
                self.assertEqual(client.game.state, "login")
                self.assertTrue(client.status_error)
                self.assertIn("Server unavailable", client.status)
                self.assertIn("separate terminal", client.status)
                self.press(pygame.K_ESCAPE)
                self.assertEqual(client.game.state, "menu")
            finally:
                client.shutdown()
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
