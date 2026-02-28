"""Tests for US-002: Discord OAuth2 authentication in the API."""
from __future__ import annotations

import asyncio
import json
import sys
import urllib.parse
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

# Stubs for aiohttp and jwt are registered in tests/conftest.py before this
# file loads. Import the stub classes from sys.modules / conftest directly.
from tests.conftest import (
    FakeApplication,
    FakeHTTPFound,
    FakeHTTPUnauthorized,
    FakeResponse,
)

_mock_web = sys.modules["aiohttp.web"]

from bot.api.auth import (  # noqa: E402
    COOKIE_NAME,
    decode_jwt,
    encode_jwt,
    handle_auth_callback,
    handle_auth_discord,
    handle_auth_logout,
    handle_auth_me,
    make_jwt_middleware,
    setup_auth_routes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(path: str = "/auth/me", cookies: dict | None = None, query: dict | None = None):
    req = MagicMock()
    req.path = path
    req.cookies = cookies or {}
    req.rel_url = MagicMock()
    req.rel_url.query = query or {}
    return req


def _make_session_factory(token_data: dict, user_data: dict, guilds_data: list):
    """Return an async context manager factory that simulates aiohttp.ClientSession."""

    def _make_resp_cm(payload):
        async def _json():
            return payload

        resp = MagicMock()
        resp.json = _json

        @asynccontextmanager
        async def _cm():
            yield resp

        return _cm()

    @asynccontextmanager
    async def _session_cm():
        session = MagicMock()
        session.post = MagicMock(return_value=_make_resp_cm(token_data))

        _get_calls = [0]

        def _get_side_effect(*args, **kwargs):
            idx = _get_calls[0]
            _get_calls[0] += 1
            return _make_resp_cm(user_data if idx == 0 else guilds_data)

        session.get = MagicMock(side_effect=_get_side_effect)
        yield session

    return _session_cm


# ---------------------------------------------------------------------------
# JWT encode/decode tests
# ---------------------------------------------------------------------------


class TestJWT:
    def test_encode_returns_string(self):
        with patch.dict("os.environ", {"JWT_SECRET": "testsecret"}):
            token = encode_jwt({"user": "alice"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_roundtrip(self):
        with patch.dict("os.environ", {"JWT_SECRET": "testsecret"}):
            token = encode_jwt({"id": "123", "username": "alice"})
            payload = decode_jwt(token)
        assert payload["id"] == "123"
        assert payload["username"] == "alice"

    def test_decode_invalid_token_raises(self):
        import pytest
        with patch.dict("os.environ", {"JWT_SECRET": "testsecret"}):
            with pytest.raises(Exception):
                decode_jwt("not.a.valid.token!!!!")

    def test_jwt_secret_required(self):
        import pytest
        env = {k: v for k, v in __import__("os").environ.items() if k != "JWT_SECRET"}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="JWT_SECRET"):
                encode_jwt({"id": "1"})


# ---------------------------------------------------------------------------
# GET /auth/discord tests
# ---------------------------------------------------------------------------


class TestHandleAuthDiscord:
    def test_redirects_to_discord(self):
        import pytest
        req = _make_request(path="/auth/discord", query={"guild_id": "987654321"})
        env = {
            "JWT_SECRET": "secret",
            "DISCORD_CLIENT_ID": "client123",
            "DISCORD_REDIRECT_URI": "http://localhost:3000/auth/callback",
        }
        with patch.dict("os.environ", env):
            with pytest.raises(FakeHTTPFound) as exc_info:
                asyncio.run(handle_auth_discord(req))
        assert "discord.com/oauth2/authorize" in exc_info.value.location

    def test_redirect_contains_guild_id_as_state(self):
        import pytest
        req = _make_request(path="/auth/discord", query={"guild_id": "111222333"})
        env = {
            "JWT_SECRET": "secret",
            "DISCORD_CLIENT_ID": "client123",
            "DISCORD_REDIRECT_URI": "http://localhost:3000/auth/callback",
        }
        with patch.dict("os.environ", env):
            with pytest.raises(FakeHTTPFound) as exc_info:
                asyncio.run(handle_auth_discord(req))
        parsed = urllib.parse.urlparse(exc_info.value.location)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        assert params["state"] == "111222333"

    def test_redirect_contains_client_id(self):
        import pytest
        req = _make_request(path="/auth/discord", query={"guild_id": "1"})
        env = {
            "JWT_SECRET": "secret",
            "DISCORD_CLIENT_ID": "my_client_id",
            "DISCORD_REDIRECT_URI": "http://localhost:3000/auth/callback",
        }
        with patch.dict("os.environ", env):
            with pytest.raises(FakeHTTPFound) as exc_info:
                asyncio.run(handle_auth_discord(req))
        assert "my_client_id" in exc_info.value.location


# ---------------------------------------------------------------------------
# GET /auth/callback tests
# ---------------------------------------------------------------------------


class TestHandleAuthCallback:
    def test_missing_code_redirects_error(self):
        import pytest
        req = _make_request(path="/auth/callback", query={"code": "", "state": "123"})
        env = {"JWT_SECRET": "secret", "DASHBOARD_URL": "http://localhost:3000"}
        with patch.dict("os.environ", env):
            with pytest.raises(FakeHTTPFound) as exc_info:
                asyncio.run(handle_auth_callback(req))
        assert "error=invalid_code" in exc_info.value.location

    def test_successful_login_sets_cookie(self):
        import pytest
        req = _make_request(path="/auth/callback", query={"code": "valid_code", "state": "999"})
        factory = _make_session_factory(
            token_data={"access_token": "discord_token_abc"},
            user_data={"id": "u1", "username": "alice", "avatar": "avatar_hash"},
            guilds_data=[{"id": "999", "name": "My Server"}],
        )
        env = {
            "JWT_SECRET": "secret",
            "DISCORD_CLIENT_ID": "cid",
            "DISCORD_CLIENT_SECRET": "csecret",
            "DISCORD_REDIRECT_URI": "http://localhost:3000/auth/callback",
            "DASHBOARD_URL": "http://localhost:3000",
        }
        with patch.dict("os.environ", env):
            with pytest.raises(FakeHTTPFound) as exc_info:
                asyncio.run(handle_auth_callback(req, _http_session_factory=factory))
        assert COOKIE_NAME in exc_info.value._cookies

    def test_user_not_in_guild_redirects_error(self):
        import pytest
        req = _make_request(path="/auth/callback", query={"code": "valid_code", "state": "999"})
        factory = _make_session_factory(
            token_data={"access_token": "tok"},
            user_data={"id": "u1", "username": "alice", "avatar": None},
            guilds_data=[{"id": "111"}],  # user NOT in guild 999
        )
        env = {
            "JWT_SECRET": "secret",
            "DISCORD_CLIENT_ID": "cid",
            "DISCORD_CLIENT_SECRET": "cs",
            "DISCORD_REDIRECT_URI": "http://localhost:3000/auth/callback",
            "DASHBOARD_URL": "http://localhost:3000",
        }
        with patch.dict("os.environ", env):
            with pytest.raises(FakeHTTPFound) as exc_info:
                asyncio.run(handle_auth_callback(req, _http_session_factory=factory))
        assert "error=not_in_guild" in exc_info.value.location

    def test_discord_token_error_redirects_error(self):
        import pytest
        req = _make_request(path="/auth/callback", query={"code": "bad_code", "state": "999"})
        factory = _make_session_factory(
            token_data={"error": "invalid_grant"},
            user_data={},
            guilds_data=[],
        )
        env = {
            "JWT_SECRET": "secret",
            "DISCORD_CLIENT_ID": "cid",
            "DISCORD_CLIENT_SECRET": "cs",
            "DISCORD_REDIRECT_URI": "http://localhost:3000/auth/callback",
            "DASHBOARD_URL": "http://localhost:3000",
        }
        with patch.dict("os.environ", env):
            with pytest.raises(FakeHTTPFound) as exc_info:
                asyncio.run(handle_auth_callback(req, _http_session_factory=factory))
        assert "error=invalid_code" in exc_info.value.location

    def test_successful_redirect_contains_guild_id(self):
        import pytest
        req = _make_request(path="/auth/callback", query={"code": "valid_code", "state": "42"})
        factory = _make_session_factory(
            token_data={"access_token": "tok"},
            user_data={"id": "u1", "username": "bob", "avatar": None},
            guilds_data=[{"id": "42"}],
        )
        env = {
            "JWT_SECRET": "secret",
            "DISCORD_CLIENT_ID": "cid",
            "DISCORD_CLIENT_SECRET": "cs",
            "DISCORD_REDIRECT_URI": "http://localhost:3000/auth/callback",
            "DASHBOARD_URL": "http://localhost:3000",
        }
        with patch.dict("os.environ", env):
            with pytest.raises(FakeHTTPFound) as exc_info:
                asyncio.run(handle_auth_callback(req, _http_session_factory=factory))
        assert "guild=42" in exc_info.value.location


# ---------------------------------------------------------------------------
# GET /auth/me tests
# ---------------------------------------------------------------------------


class TestHandleAuthMe:
    def test_no_cookie_returns_401(self):
        import pytest
        req = _make_request(path="/auth/me", cookies={})
        with pytest.raises(FakeHTTPUnauthorized):
            asyncio.run(handle_auth_me(req))

    def test_invalid_token_returns_401(self):
        import pytest
        req = _make_request(path="/auth/me", cookies={COOKIE_NAME: "badtoken"})
        with patch.dict("os.environ", {"JWT_SECRET": "secret"}):
            with pytest.raises(FakeHTTPUnauthorized):
                asyncio.run(handle_auth_me(req))

    def test_valid_token_returns_user_info(self):
        with patch.dict("os.environ", {"JWT_SECRET": "secret"}):
            token = encode_jwt({"id": "u1", "username": "alice", "avatar": "abc"})
            req = _make_request(path="/auth/me", cookies={COOKIE_NAME: token})
            response = asyncio.run(handle_auth_me(req))

        data = json.loads(response.text)
        assert data["id"] == "u1"
        assert data["username"] == "alice"
        assert data["avatar"] == "abc"


# ---------------------------------------------------------------------------
# POST /auth/logout tests
# ---------------------------------------------------------------------------


class TestHandleAuthLogout:
    def test_logout_clears_cookie(self):
        req = _make_request(path="/auth/logout")
        response = asyncio.run(handle_auth_logout(req))
        assert COOKIE_NAME in response._cookies
        assert response._cookies[COOKIE_NAME] is None

    def test_logout_returns_json(self):
        req = _make_request(path="/auth/logout")
        response = asyncio.run(handle_auth_logout(req))
        assert response.content_type == "application/json"


# ---------------------------------------------------------------------------
# JWT middleware tests
# ---------------------------------------------------------------------------


class TestJwtMiddleware:
    def _run_middleware(self, request, handler=None):
        if handler is None:
            async def handler(req):
                return FakeResponse("ok")
        middleware = make_jwt_middleware()
        return asyncio.run(middleware(request, handler))

    def test_auth_paths_pass_through(self):
        req = _make_request(path="/auth/me")
        response = self._run_middleware(req)
        assert response.text == "ok"

    def test_auth_callback_passes_through(self):
        req = _make_request(path="/auth/callback")
        response = self._run_middleware(req)
        assert response.text == "ok"

    def test_missing_cookie_returns_401(self):
        import pytest
        req = _make_request(path="/api/guilds/123/queue", cookies={})
        with pytest.raises(FakeHTTPUnauthorized):
            self._run_middleware(req)

    def test_invalid_token_returns_401(self):
        import pytest
        req = _make_request(
            path="/api/guilds/123/queue",
            cookies={COOKIE_NAME: "invalid.token"},
        )
        with patch.dict("os.environ", {"JWT_SECRET": "secret"}):
            with pytest.raises(FakeHTTPUnauthorized):
                self._run_middleware(req)

    def test_valid_token_passes_through(self):
        with patch.dict("os.environ", {"JWT_SECRET": "secret"}):
            token = encode_jwt({"id": "u1"})
            req = _make_request(
                path="/api/guilds/123/queue",
                cookies={COOKIE_NAME: token},
            )
            response = self._run_middleware(req)
        assert response.text == "ok"


# ---------------------------------------------------------------------------
# setup_auth_routes tests
# ---------------------------------------------------------------------------


class TestSetupAuthRoutes:
    def test_registers_expected_routes(self):
        app = FakeApplication()
        setup_auth_routes(app)
        paths = [(method, path) for method, path, _ in app.router.routes]
        assert ("GET", "/auth/discord") in paths
        assert ("GET", "/auth/callback") in paths
        assert ("GET", "/auth/me") in paths
        assert ("POST", "/auth/logout") in paths
