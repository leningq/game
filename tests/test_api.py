import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import db
from api.main import app
from game.logic import Game, MAX_SCORE


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.environment = patch.dict(
            os.environ, {"BRICKFALL_DB_PATH": os.path.join(self.folder.name, "test.sqlite3")}
        )
        self.environment.start()
        self.client = TestClient(app)
        self.client.__enter__()
        self.credentials = {"username": "PlayerOne", "password": "school-password"}
        self.assertEqual(self.client.post("/register", json=self.credentials).status_code, 201)
        login = self.client.post("/login", json=self.credentials)
        self.assertEqual(login.status_code, 200)
        self.token = login.json()["token"]
        self.headers = {"Authorization": "Bearer " + self.token}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.environment.stop()
        self.folder.cleanup()

    def submit(self, score, run_id="0123456789abcdef0123456789abcdef"):
        return self.client.post(
            "/scores", json={"score": score, "run_id": run_id}, headers=self.headers
        )

    def test_registration_login_and_private_passwords(self):
        duplicate = {**self.credentials, "username": "playerone"}
        self.assertEqual(self.client.post("/register", json=duplicate).status_code, 409)
        incorrect = {**self.credentials, "password": "wrong-password"}
        self.assertEqual(self.client.post("/login", json=incorrect).status_code, 401)
        self.assertEqual(self.client.post("/login", json=duplicate).json()["username"], "PlayerOne")
        self.client.post("/register", json={**self.credentials, "username": "PlayerTwo"})
        with db.connection() as database:
            users = database.execute("SELECT * FROM users ORDER BY id").fetchall()
            session = database.execute("SELECT * FROM sessions LIMIT 1").fetchone()
        self.assertNotEqual(users[0]["salt"], users[1]["salt"])
        self.assertNotEqual(users[0]["password_hash"], users[1]["password_hash"])
        self.assertNotEqual(users[0]["password_hash"], self.credentials["password"])
        self.assertNotEqual(session["token_hash"], self.token)

    def test_bad_json_and_credentials(self):
        for name in ("", "ab", "x" * 21, "bad name", "Игрок", "a'--", None):
            response = self.client.post(
                "/register", json={**self.credentials, "username": name}
            )
            self.assertEqual(response.status_code, 400, name)
        for password in ("", "short", "x" * 129, 12345678):
            response = self.client.post(
                "/register", json={**self.credentials, "password": password}
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/register", json={}).status_code, 400)
        self.assertEqual(
            self.client.post("/register", content="{", headers={"Content-Type": "application/json"}).status_code,
            400,
        )

    def test_authentication_expiry_and_persistence(self):
        self.assertEqual(self.client.get("/saves").status_code, 401)
        self.assertEqual(
            self.client.get("/saves", headers={"Authorization": "Bearer invalid"}).status_code, 401
        )
        with TestClient(app) as restarted:
            self.assertEqual(restarted.get("/saves", headers=self.headers).status_code, 404)
        with db.connection() as database:
            database.execute("UPDATE sessions SET expires_at = 0")
        self.assertEqual(self.client.get("/saves", headers=self.headers).status_code, 401)

    def test_scores_are_idempotent_and_stats_use_all_games(self):
        self.assertEqual(self.submit(100).status_code, 201)
        self.assertEqual(self.submit(100).status_code, 201)
        self.assertEqual(self.submit(110).status_code, 409)
        self.assertEqual(self.submit(200, "fedcba9876543210fedcba9876543210").status_code, 201)
        self.assertEqual(self.client.get("/scores/top").json(), [{"name": "PlayerOne", "score": 200}])
        self.assertEqual(
            self.client.get("/players/playerone/stats").json(),
            {"name": "PlayerOne", "games": 2, "best_score": 200, "average_score": 150.0},
        )
        self.assertEqual(self.client.get("/players/missing/stats").status_code, 404)
        for score in (-10, 5, MAX_SCORE + 10, True, 1.5, "100", None):
            self.assertEqual(self.submit(score).status_code, 400)
        self.assertEqual(self.submit(100, "bad").status_code, 400)

    def test_top_ten_unique_players(self):
        for index in range(12):
            user = db.register_user(f"Test{index:02}", "school-password")
            db.add_score(user["id"], "first-run-0000000", index * 10)
            db.add_score(user["id"], "second-run-00000", index * 20)
        top = self.client.get("/scores/top").json()
        self.assertEqual(len(top), 10)
        self.assertEqual(top[0], {"name": "Test11", "score": 220})
        self.assertEqual(len({player["name"] for player in top}), 10)
        self.assertEqual([player["score"] for player in top], sorted(
            [player["score"] for player in top], reverse=True
        ))

    def test_save_round_trip_and_finished_run_cannot_be_replayed(self):
        self.assertEqual(self.client.get("/saves", headers=self.headers).status_code, 404)
        game = Game()
        game.start()
        game.launch_ball()
        game.activate_slow()
        game.update(1 / 60, direction=1)
        state = game.to_dict()
        response = self.client.put("/saves", json=state, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        expected = Game.from_dict(state).to_dict()
        self.assertEqual(response.json(), expected)
        self.assertEqual(self.client.get("/saves", headers=self.headers).json(), expected)
        self.assertEqual(self.submit(game.score, game.run_id).status_code, 201)
        self.assertEqual(self.client.get("/saves", headers=self.headers).status_code, 404)
        self.assertEqual(self.client.put("/saves", json=state, headers=self.headers).status_code, 409)
        self.assertEqual(self.client.put("/saves", json={}, headers=self.headers).status_code, 400)
        invalid = {**state, "lives": -1}
        self.assertEqual(self.client.put("/saves", json=invalid, headers=self.headers).status_code, 400)

    def test_saves_belong_to_authenticated_player(self):
        game = Game()
        game.start()
        self.client.put("/saves", json=game.to_dict(), headers=self.headers)
        other = {"username": "OtherPlayer", "password": "other-password"}
        self.client.post("/register", json=other)
        token = self.client.post("/login", json=other).json()["token"]
        headers = {"Authorization": "Bearer " + token}
        self.assertEqual(self.client.get("/saves", headers=headers).status_code, 404)

    def test_website_uses_database_and_profiles(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Leaderboard", page.text)
        self.assertNotIn("Dimond", page.text)
        self.submit(230)
        page = self.client.get("/")
        self.assertIn("PlayerOne", page.text)
        self.assertIn("230", page.text)
        self.assertEqual(self.client.get("/players/PlayerOne").status_code, 200)
        self.assertEqual(self.client.get("/players/missing").status_code, 404)
        self.assertEqual(self.client.get("/rules").status_code, 200)
        self.assertEqual(self.client.get("/static/style.css").status_code, 200)


if __name__ == "__main__":
    unittest.main()
