import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from client import main as client
from client.api_client import ApiClient, ApiError
from game.logic import BALL_RADIUS, FIELD_BOTTOM


class IntegrationTests(unittest.TestCase):
    def test_real_http_server_and_pygame_client(self):
        # Один полный путь через настоящий HTTP, с отдельной временной базой.
        with tempfile.TemporaryDirectory() as folder:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            environment = dict(os.environ, BRICKFALL_DB_PATH=str(Path(folder) / "live.sqlite3"))
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
                client.perform_action("register")
                client.username_input, client.password_input = "LivePlayer", "school-practice"
                client.submit_auth()
                client.pending.result(timeout=5)
                client.poll_request()
                self.assertEqual(client.game.state, "login")
                client.password_input = "school-practice"
                client.submit_auth()
                client.pending.result(timeout=5)
                client.poll_request()
                client.perform_action("start")
                client.game.launch_ball()
                client.game.activate_slow()
                client.game.update(1 / 60)
                run_id = client.game.run_id
                client.perform_action("save")
                client.pending.result(timeout=5)
                client.poll_request()
                client.perform_action("menu")
                client.perform_action("load")
                client.pending.result(timeout=5)
                client.poll_request()
                self.assertEqual(client.game.state, "paused")
                self.assertEqual(client.game.run_id, run_id)
                self.assertTrue(client.game.slow_used)
                client.perform_action("resume")
                for _ in range(3):
                    client.game.launch_ball()
                    client.game.ball_y = FIELD_BOTTOM + BALL_RADIUS + 5
                    client.game.ball_speed_y = 360
                    client.update(1 / 60)
                self.assertEqual(client.game.state, "game_over")
                client.pending.result(timeout=5)
                client.poll_request()
                self.assertEqual(client.score_state, "saved")
                self.assertEqual(api.request("GET", "/scores/top"), [{"name": "LivePlayer", "score": 0}])
                self.assertEqual(api.request("GET", "/players/LivePlayer/stats")["games"], 1)
                with urlopen(api.base_url + "/", timeout=2) as response:
                    self.assertIn("LivePlayer", response.read().decode("utf-8"))
                client.draw()
                self.assertTrue(Path(folder, "live.sqlite3").exists())
                process.terminate()
                process.wait(timeout=5)
                client.perform_action("menu")
                client.perform_action("account")
                client.perform_action("login")
                client.password_input = "school-practice"
                client.submit_auth()
                with self.assertRaises(ApiError):
                    client.pending.result(timeout=5)
                client.poll_request()
                self.assertTrue(client.status_error)
                self.assertIn("Server unavailable", client.status)
                client.perform_action("menu")
                self.assertEqual(client.game.state, "menu")
            finally:
                client.shutdown()
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()