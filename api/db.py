import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PASSWORD_ITERATIONS = 260_000
SESSION_SECONDS = 7 * 24 * 60 * 60


@contextmanager
def connection():
    path = Path(os.environ.get("BRICKFALL_DB_PATH", BASE_DIR / "data" / "brickfall.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(path, timeout=5)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    try:
        # Этот блок сохраняет изменения или отменяет их при ошибке.
        with database:
            yield database
    finally:
        database.close()


def init_db():
    with connection() as database:
        database.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                run_id TEXT NOT NULL,
                score INTEGER NOT NULL CHECK (score >= 0),
                UNIQUE (user_id, run_id)
            );
            CREATE TABLE IF NOT EXISTS saves (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                run_id TEXT NOT NULL,
                state_json TEXT NOT NULL
            );
        """)


def password_hash(password, salt):
    # Соль делает хеши одинаковых паролей разными.
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PASSWORD_ITERATIONS
    ).hex()


def register_user(username, password):
    salt = secrets.token_hex(16)
    hashed = password_hash(password, salt)
    with connection() as database:
        cursor = database.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, hashed, salt),
        )
        return {"id": cursor.lastrowid, "username": username}


def login_user(username, password):
    with connection() as database:
        user = database.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
    if user is None or not secrets.compare_digest(
        user["password_hash"], password_hash(password, user["salt"])
    ):
        return None
    return {"id": user["id"], "username": user["username"]}


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = int(time.time())
    with connection() as database:
        database.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        database.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (hashed, user_id, now + SESSION_SECONDS),
        )
    return token


def session_user(token):
    hashed = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with connection() as database:
        user = database.execute(
            "SELECT users.id, users.username FROM sessions "
            "JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
            (hashed, int(time.time())),
        ).fetchone()
    return dict(user) if user else None


def add_score(user_id, run_id, score):
    with connection() as database:
        # У одной попытки может быть только один окончательный результат.
        database.execute(
            "INSERT INTO scores (user_id, run_id, score) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, run_id) DO NOTHING", (user_id, run_id, score),
        )
        existing = database.execute(
            "SELECT score FROM scores WHERE user_id = ? AND run_id = ?", (user_id, run_id)
        ).fetchone()
        if existing["score"] != score:
            raise ValueError("This game already has a different score.")
        database.execute(
            "DELETE FROM saves WHERE user_id = ? AND run_id = ?", (user_id, run_id)
        )


def top_scores():
    with connection() as database:
        rows = database.execute(
            "SELECT users.username AS name, MAX(scores.score) AS score "
            "FROM users JOIN scores ON users.id = scores.user_id "
            "GROUP BY users.id ORDER BY score DESC, users.username COLLATE NOCASE LIMIT 10"
        ).fetchall()
    return [dict(row) for row in rows]


def player_stats(name):
    with connection() as database:
        row = database.execute(
            "SELECT users.username AS name, COUNT(scores.id) AS games, "
            "COALESCE(MAX(scores.score), 0) AS best_score, "
            "ROUND(COALESCE(AVG(scores.score), 0), 2) AS average_score "
            "FROM users LEFT JOIN scores ON users.id = scores.user_id "
            "WHERE users.username = ? COLLATE NOCASE GROUP BY users.id", (name,)
        ).fetchone()
    return dict(row) if row else None


def save_game(user_id, state):
    with connection() as database:
        database.execute("BEGIN IMMEDIATE")
        finished = database.execute(
            "SELECT id FROM scores WHERE user_id = ? AND run_id = ?",
            (user_id, state["run_id"]),
        ).fetchone()
        if finished:
            raise ValueError("This game is already finished. Start a new game.")
        database.execute(
            "INSERT INTO saves (user_id, run_id, state_json) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET run_id = excluded.run_id, "
            "state_json = excluded.state_json",
            (user_id, state["run_id"], json.dumps(state, allow_nan=False)),
        )


def load_game(user_id):
    with connection() as database:
        row = database.execute(
            "SELECT state_json FROM saves WHERE user_id = ?", (user_id,)
        ).fetchone()
    return json.loads(row["state_json"]) if row else None
