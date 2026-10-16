"""Start the local Brickfall server and then open the game window."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
SERVER_URL = "http://127.0.0.1:8000"


def brickfall_server_ready():
    try:
        with urlopen(SERVER_URL + "/openapi.json", timeout=0.5) as response:
            document = json.load(response)
        return document.get("info", {}).get("title") == "Brickfall"
    except (URLError, TimeoutError, ValueError, OSError):
        return False


def port_in_use():
    with socket.socket() as connection:
        return connection.connect_ex(("127.0.0.1", 8000)) == 0


def main():
    if port_in_use():
        print("Port 8000 is in use. Close the other server and run Brickfall again.")
        return 1
    log_path = ROOT / "data" / "server.log"
    log_path.parent.mkdir(exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    # Сервер запускается из папки проекта, чтобы импорты и база находились правильно.
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if brickfall_server_ready():
            break
        if server.poll() is not None:
            break
        time.sleep(0.1)
    if not brickfall_server_ready():
        print(f"Server did not start. Details: {log_path}")
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)
        log_file.close()
        return 1

    try:
        print(f"Brickfall website: {SERVER_URL}/")
        os.environ["BRICKFALL_API_URL"] = SERVER_URL
        from client.main import main as start_game

        start_game()
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)
        log_file.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
