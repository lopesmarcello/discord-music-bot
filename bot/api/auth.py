"""Discord OAuth2 authentication routes and JWT utilities."""
from __future__ import annotations

import json
import os
import urllib.parse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp.web

DISCORD_OAUTH_BASE = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/v10/oauth2/token"
DISCORD_API_BASE = "https://discord.com/api/v10"
COOKIE_NAME = "session"


# ---------------------------------------------------------------------------
# JWT helpers (lazy-import PyJWT)
# ---------------------------------------------------------------------------

def _get_jwt_module():
    import jwt  # noqa: PLC0415
    return jwt


def _jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        raise ValueError("JWT_SECRET env var is required")
    return secret


def encode_jwt(payload: dict) -> str:
    """Encode a dict as a signed JWT."""
    jwt = _get_jwt_module()
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT, returning the payload dict."""
    jwt = _get_jwt_module()
    return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])


# ---------------------------------------------------------------------------
# Auth route handlers
# ---------------------------------------------------------------------------

async def handle_auth_discord(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """GET /auth/discord?guild_id={id} — redirect to Discord OAuth2."""
    import aiohttp.web  # noqa: PLC0415, F401

    guild_id = request.rel_url.query.get("guild_id", "")
    client_id = os.environ.get("DISCORD_CLIENT_ID", "")
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI", "")

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify guilds",
        "state": guild_id,
    })
    raise aiohttp.web.HTTPFound(f"{DISCORD_OAUTH_BASE}?{params}")


async def _fetch_discord_oauth_data(
    code: str,
    http_session_factory,
) -> tuple[dict | None, dict | None, list | None]:
    """Exchange code for a Discord access token, user, and guilds.

    Returns (token_data, user_data, guilds_data). Any value is None on error.
    Uses `http_session_factory` so tests can inject a mock.
    """
    import aiohttp  # noqa: PLC0415

    _factory = (
        http_session_factory
        if http_session_factory is not None
        else aiohttp.ClientSession
    )

    try:
        async with _factory() as session:
            async with session.post(
                DISCORD_TOKEN_URL,
                data={
                    "client_id": os.environ.get("DISCORD_CLIENT_ID", ""),
                    "client_secret": os.environ.get("DISCORD_CLIENT_SECRET", ""),
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": os.environ.get("DISCORD_REDIRECT_URI", ""),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as token_resp:
                token_data = await token_resp.json()

            if "error" in token_data or "access_token" not in token_data:
                return token_data, None, None

            access_token = token_data["access_token"]

            async with session.get(
                f"{DISCORD_API_BASE}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            ) as user_resp:
                user_data = await user_resp.json()

            async with session.get(
                f"{DISCORD_API_BASE}/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"},
            ) as guilds_resp:
                guilds_data = await guilds_resp.json()

            return token_data, user_data, guilds_data
    except Exception:  # noqa: BLE001
        return None, None, None


async def handle_auth_callback(
    request: "aiohttp.web.Request",
    *,
    _http_session_factory=None,
) -> "aiohttp.web.Response":
    """GET /auth/callback — exchange code, verify guild, issue JWT cookie."""
    import aiohttp.web  # noqa: PLC0415, F401

    dashboard_url = os.environ.get("DASHBOARD_URL", "http://localhost:3000")
    code = request.rel_url.query.get("code", "")
    guild_id = request.rel_url.query.get("state", "")

    if not code:
        raise aiohttp.web.HTTPFound(f"{dashboard_url}?error=invalid_code")

    token_data, user_data, guilds_data = await _fetch_discord_oauth_data(
        code, _http_session_factory
    )

    if token_data is None or user_data is None or guilds_data is None:
        raise aiohttp.web.HTTPFound(f"{dashboard_url}?error=invalid_code")

    if "error" in token_data or "access_token" not in token_data:
        raise aiohttp.web.HTTPFound(f"{dashboard_url}?error=invalid_code")

    # Verify guild membership when guild_id was provided
    if guild_id:
        member_guild_ids = [g["id"] for g in guilds_data]
        if guild_id not in member_guild_ids:
            raise aiohttp.web.HTTPFound(f"{dashboard_url}?error=not_in_guild")

    # Issue JWT session cookie
    session_payload = {
        "id": user_data["id"],
        "username": user_data["username"],
        "avatar": user_data.get("avatar"),
        "guild_id": guild_id,
        "guild_ids": [g["id"] for g in guilds_data],
    }
    token = encode_jwt(session_payload)

    redirect_url = f"{dashboard_url}?guild={guild_id}" if guild_id else dashboard_url
    response = aiohttp.web.HTTPFound(redirect_url)
    response.set_cookie(COOKIE_NAME, token, httponly=True, path="/", samesite="Lax")
    raise response


async def handle_auth_me(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """GET /auth/me — return {id, username, avatar} or 401."""
    import aiohttp.web  # noqa: PLC0415, F401

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise aiohttp.web.HTTPUnauthorized()

    try:
        payload = decode_jwt(token)
    except Exception:  # noqa: BLE001
        raise aiohttp.web.HTTPUnauthorized()

    return aiohttp.web.Response(
        text=json.dumps({
            "id": payload.get("id"),
            "username": payload.get("username"),
            "avatar": payload.get("avatar"),
        }),
        content_type="application/json",
    )


async def handle_auth_logout(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """POST /auth/logout — clear the session cookie."""
    import aiohttp.web  # noqa: PLC0415, F401

    response = aiohttp.web.Response(text="{}", content_type="application/json")
    response.del_cookie(COOKIE_NAME, path="/")
    return response


# ---------------------------------------------------------------------------
# JWT middleware
# ---------------------------------------------------------------------------

def make_jwt_middleware():
    """Return an aiohttp middleware that enforces JWT auth on non-/auth/* routes."""
    import aiohttp.web  # noqa: PLC0415, F401

    @aiohttp.web.middleware
    async def _jwt_middleware(request, handler):
        if request.path.startswith("/auth/"):
            return await handler(request)

        token = request.cookies.get(COOKIE_NAME)
        if not token:
            raise aiohttp.web.HTTPUnauthorized()

        try:
            decode_jwt(token)
        except Exception:  # noqa: BLE001
            raise aiohttp.web.HTTPUnauthorized()

        return await handler(request)

    return _jwt_middleware


# ---------------------------------------------------------------------------
# Route setup
# ---------------------------------------------------------------------------

def setup_auth_routes(app: "aiohttp.web.Application") -> None:
    """Register auth routes on the aiohttp application."""
    import aiohttp.web  # noqa: PLC0415, F401

    app.router.add_get("/auth/discord", handle_auth_discord)
    app.router.add_get("/auth/callback", handle_auth_callback)
    app.router.add_get("/auth/me", handle_auth_me)
    app.router.add_post("/auth/logout", handle_auth_logout)
