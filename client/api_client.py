import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ApiError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    def __init__(self, base_url=None, timeout=3):
        self.base_url = (base_url or os.getenv("BRICKFALL_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.timeout = timeout
        self.token = None
        self.username = None

    def request(self, method, path, data=None):
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        body = None
        if data is not None:
            body = json.dumps(data, allow_nan=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as error:
            try:
                detail = json.load(error).get("detail", "")
            except (ValueError, AttributeError):
                detail = ""
            finally:
                error.close()
            if not isinstance(detail, str) or not detail:
                detail = "Check the entered data."
            raise ApiError(detail, error.code) from None
        except (URLError, TimeoutError, OSError):
            raise ApiError("Server unavailable. Start the server in a separate terminal, then try again.") from None
        except (ValueError, TypeError):
            raise ApiError("The server returned an invalid response.") from None

    def register(self, username, password):
        return self.request("POST", "/register", {"username": username, "password": password})

    def login(self, username, password):
        return self.request("POST", "/login", {"username": username, "password": password})

    def send_score(self, score, run_id):
        return self.request("POST", "/scores", {"score": score, "run_id": run_id})

    def save(self, state):
        return self.request("PUT", "/saves", state)

    def load(self):
        return self.request("GET", "/saves")