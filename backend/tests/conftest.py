"""Integration fixtures: run the real API under uvicorn and talk to it over HTTP/WebSocket.

Expects the environment from docker-compose.test.yml (throwaway Postgres/Redis, migrated database).
"""

import os
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass, field

import httpx
import pytest

PORT = int(os.environ.get("XB_TEST_PORT", "8765"))
BASE_URL = f"http://127.0.0.1:{PORT}/api/v1"
WS_URL = f"ws://127.0.0.1:{PORT}/api/v1"


@pytest.fixture(scope="session")
def server():
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if httpx.get(f"{BASE_URL}/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    else:
        process.kill()
        raise RuntimeError("API server did not start")
    yield BASE_URL
    process.terminate()
    process.wait(timeout=10)


@pytest.fixture(scope="session")
def open_registration(server):
    owner = {"username": "owner", "email": "owner@example.com", "password": "owner-password-123"}
    response = httpx.post(f"{server}/auth/bootstrap-owner", json=owner)
    if response.status_code == 200:
        token = response.json()["data"]["access_token"]
    else:
        login = httpx.post(f"{server}/auth/admin-login", json={"username_or_email": owner["username"], "password": owner["password"]})
        login.raise_for_status()
        token = login.json()["data"]["access_token"]
    httpx.patch(
        f"{server}/admin/system-settings",
        json={"registration_mode": "open"},
        headers={"Authorization": f"Bearer {token}"},
    ).raise_for_status()


@dataclass
class Device:
    """One signed-in browser: a user plus the device key it keeps in localStorage."""

    username: str
    password: str
    device_key: str
    tokens: dict = field(default_factory=dict)

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.tokens['access_token']}"}

    def get(self, path: str, headers: dict | None = None, **kwargs) -> httpx.Response:
        return httpx.get(f"{BASE_URL}{path}", headers={**self.headers, **(headers or {})}, **kwargs)

    def post(self, path: str, headers: dict | None = None, **kwargs) -> httpx.Response:
        return httpx.post(f"{BASE_URL}{path}", headers={**self.headers, **(headers or {})}, **kwargs)

    def patch(self, path: str, headers: dict | None = None, **kwargs) -> httpx.Response:
        return httpx.patch(f"{BASE_URL}{path}", headers={**self.headers, **(headers or {})}, **kwargs)

    def delete(self, path: str, headers: dict | None = None, **kwargs) -> httpx.Response:
        return httpx.delete(f"{BASE_URL}{path}", headers={**self.headers, **(headers or {})}, **kwargs)

    def login(self, device_name: str | None = None) -> "Device":
        response = httpx.post(
            f"{BASE_URL}/auth/login",
            json={"username_or_email": self.username, "password": self.password, "device_key": self.device_key, "device_name": device_name},
        )
        response.raise_for_status()
        self.tokens = response.json()["data"]
        return self

    def another_device(self, device_name: str | None = None) -> "Device":
        return Device(self.username, self.password, secrets.token_urlsafe(24)).login(device_name)

    def data(self, response: httpx.Response):
        assert response.status_code == 200, response.text
        return response.json()["data"]


@pytest.fixture
def make_user(open_registration):
    def factory(prefix: str = "user", device_name: str | None = None) -> Device:
        username = f"{prefix}{secrets.token_hex(4)}"
        password = "test-password-123"
        device_key = secrets.token_urlsafe(24)
        response = httpx.post(
            f"{BASE_URL}/auth/register",
            json={"username": username, "email": f"{username}@example.com", "password": password, "device_key": device_key},
        )
        response.raise_for_status()
        return Device(username, password, device_key).login(device_name)

    return factory
