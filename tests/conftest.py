"""Shared test fixtures and stubs for the test suite.

Sets up sys.modules stubs for packages not installed in the test environment
(aiohttp, jwt) before any test file is imported.
"""
from __future__ import annotations

import json
import sys
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# aiohttp.web stubs
# ---------------------------------------------------------------------------


class FakeHTTPException(Exception):
    """Base fake HTTP exception (mirrors aiohttp.web.HTTPException)."""


class FakeHTTPFound(FakeHTTPException):
    def __init__(self, location: str):
        super().__init__(location)
        self.location = location
        self._cookies: dict = {}

    def set_cookie(self, name, value, **kwargs):
        self._cookies[name] = value

    def del_cookie(self, name, **kwargs):
        self._cookies.pop(name, None)


class FakeHTTPUnauthorized(FakeHTTPException):
    pass


class FakeHTTPBadRequest(FakeHTTPException):
    def __init__(self, *, reason: str = ""):
        super().__init__(reason)
        self.reason = reason


class FakeHTTPServiceUnavailable(FakeHTTPException):
    def __init__(self, *, reason: str = ""):
        super().__init__(reason)
        self.reason = reason


class FakeResponse:
    def __init__(self, text="", content_type="text/plain"):
        self.text = text
        self.content_type = content_type
        self._cookies: dict = {}

    def del_cookie(self, name, **kwargs):
        self._cookies[name] = None


class FakeRouter:
    def __init__(self):
        self.routes: list = []

    def add_get(self, path, handler):
        self.routes.append(("GET", path, handler))

    def add_post(self, path, handler):
        self.routes.append(("POST", path, handler))


class FakeApplication:
    def __init__(self, middlewares=None):
        self.middlewares = middlewares or []
        self.router = FakeRouter()
        self._data: dict = {}

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)


class FakeAppRunner:
    def __init__(self, app):
        self.app = app
        self.setup = AsyncMock()
        self.cleanup = AsyncMock()


class FakeTCPSite:
    def __init__(self, runner, host, port):
        self.runner = runner
        self.host = host
        self.port = port
        self.start = AsyncMock()


mock_web = MagicMock()
mock_web.Application = FakeApplication
mock_web.AppRunner = FakeAppRunner
mock_web.TCPSite = FakeTCPSite
mock_web.HTTPFound = FakeHTTPFound
mock_web.HTTPUnauthorized = FakeHTTPUnauthorized
mock_web.HTTPBadRequest = FakeHTTPBadRequest
mock_web.HTTPServiceUnavailable = FakeHTTPServiceUnavailable
mock_web.HTTPException = FakeHTTPException
mock_web.Response = FakeResponse
mock_web.middleware = lambda fn: fn  # pass-through: aiohttp.web.middleware is a no-op decorator

mock_aiohttp = MagicMock()
mock_aiohttp.web = mock_web
mock_aiohttp.ClientSession = MagicMock()

sys.modules.setdefault("aiohttp", mock_aiohttp)
sys.modules.setdefault("aiohttp.web", mock_web)


# ---------------------------------------------------------------------------
# PyJWT stub (jwt module)
# ---------------------------------------------------------------------------


class FakeJWTDecodeError(Exception):
    pass


class _FakeJWTModule:
    DecodeError = FakeJWTDecodeError

    @staticmethod
    def encode(payload: dict, secret: str, algorithm: str = "HS256") -> str:
        import base64
        data = json.dumps(payload).encode()
        return base64.urlsafe_b64encode(data).decode() + "." + secret[:4]

    @staticmethod
    def decode(token: str, secret: str, algorithms=None) -> dict:
        import base64
        try:
            b64_part = token.rsplit(".", 1)[0]
            data = base64.urlsafe_b64decode(b64_part + "==")
            return json.loads(data)
        except Exception as exc:
            raise FakeJWTDecodeError("invalid token") from exc


sys.modules.setdefault("jwt", _FakeJWTModule())  # type: ignore[arg-type]
