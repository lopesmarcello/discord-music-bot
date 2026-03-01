"""Tests for US-001 (guild-picker PRD): GET /api/guilds endpoint."""
from __future__ import annotations

import asyncio
import json
import sys
from unittest.mock import MagicMock

from tests.conftest import FakeApplication, FakeResponse

_mock_web = sys.modules["aiohttp.web"]

from bot.api.guilds import handle_guilds_get, setup_guilds_routes  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guild(guild_id=123, name="Test Guild", icon="abc123"):
    g = MagicMock()
    g.id = guild_id
    g.name = name
    g.icon = icon
    return g


def _make_request(bot=None, jwt_payload=None):
    req = MagicMock()
    app = FakeApplication()
    if bot is not None:
        app["bot"] = bot
    req.app = app
    _data = {} if jwt_payload is None else {"jwt_payload": jwt_payload}
    req.get = lambda key, default=None: _data.get(key, default)
    return req


def _make_bot(guilds=None):
    bot = MagicMock()
    bot.guilds = guilds if guilds is not None else []
    return bot


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHandleGuildsGet:
    def test_returns_empty_list_when_no_bot(self):
        """Returns empty guilds list when no bot is attached."""
        req = _make_request(bot=None)
        resp = asyncio.run(handle_guilds_get(req))
        data = json.loads(resp.text)
        assert data == {"guilds": []}

    def test_returns_empty_list_when_bot_has_no_guilds(self):
        """Returns empty guilds list when bot is in no guilds."""
        bot = _make_bot(guilds=[])
        req = _make_request(bot=bot)
        resp = asyncio.run(handle_guilds_get(req))
        data = json.loads(resp.text)
        assert data == {"guilds": []}

    def test_returns_guild_list(self):
        """Returns guilds with id, name, and icon fields."""
        g1 = _make_guild(guild_id=111, name="Alpha", icon="hash1")
        g2 = _make_guild(guild_id=222, name="Beta", icon="hash2")
        bot = _make_bot(guilds=[g1, g2])
        req = _make_request(bot=bot, jwt_payload={"guild_ids": ["111", "222"]})
        resp = asyncio.run(handle_guilds_get(req))
        data = json.loads(resp.text)
        assert len(data["guilds"]) == 2
        assert data["guilds"][0] == {"id": "111", "name": "Alpha", "icon": "hash1"}
        assert data["guilds"][1] == {"id": "222", "name": "Beta", "icon": "hash2"}

    def test_guild_id_returned_as_string(self):
        """Guild IDs are serialised as strings (not integers)."""
        g = _make_guild(guild_id=999999999999)
        bot = _make_bot(guilds=[g])
        req = _make_request(bot=bot, jwt_payload={"guild_ids": ["999999999999"]})
        resp = asyncio.run(handle_guilds_get(req))
        data = json.loads(resp.text)
        assert isinstance(data["guilds"][0]["id"], str)
        assert data["guilds"][0]["id"] == "999999999999"

    def test_icon_can_be_none(self):
        """Icon field is None when guild has no icon."""
        g = _make_guild(icon=None)
        bot = _make_bot(guilds=[g])
        req = _make_request(bot=bot, jwt_payload={"guild_ids": ["123"]})
        resp = asyncio.run(handle_guilds_get(req))
        data = json.loads(resp.text)
        assert data["guilds"][0]["icon"] is None

    def test_response_content_type_is_json(self):
        """Response has application/json content type."""
        req = _make_request(bot=None)
        resp = asyncio.run(handle_guilds_get(req))
        assert resp.content_type == "application/json"


class TestSetupGuildsRoutes:
    def test_registers_get_guilds_route(self):
        """setup_guilds_routes registers GET /api/guilds."""
        app = FakeApplication()
        setup_guilds_routes(app)
        routes = [(method, path) for method, path, _ in app.router.routes]
        assert ("GET", "/api/guilds") in routes
