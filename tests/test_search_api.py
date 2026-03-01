"""Tests for US-004: YouTube search API endpoint."""
from __future__ import annotations

import asyncio
import json
import sys
from unittest.mock import MagicMock

# Shared stubs already injected via tests/conftest.py (aiohttp, jwt).
from tests.conftest import (
    FakeApplication,
    FakeHTTPBadRequest,
    FakeResponse,
)

_mock_web = sys.modules["aiohttp.web"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_resolver(results=None):
    """Return a mock resolver whose search() returns the given list."""
    resolver = MagicMock()
    resolver.search.return_value = results if results is not None else []
    return resolver


def _make_music_cog(resolver=None):
    cog = MagicMock()
    cog._resolver = resolver if resolver is not None else _make_resolver()
    return cog


def _make_bot(music_cog=None):
    bot = MagicMock()
    bot.cogs = {}
    if music_cog is not None:
        bot.cogs["Music"] = music_cog
    return bot


def _make_request(query_params=None, app_data=None):
    """Return a fake aiohttp Request with query params and app dict."""
    request = MagicMock()
    request.rel_url.query = query_params or {}

    app = FakeApplication()
    if app_data:
        for k, v in app_data.items():
            app[k] = v
    request.app = app
    return request


def _make_result(
    title="Track",
    url="https://youtube.com/watch?v=abc",
    duration=180,
    thumbnail="https://i.ytimg.com/vi/abc/default.jpg",
):
    return {"title": title, "url": url, "duration": duration, "thumbnail": thumbnail}


# ---------------------------------------------------------------------------
# setup_search_routes
# ---------------------------------------------------------------------------


class TestSetupSearchRoutes:
    def test_registers_get_search_route(self):
        from bot.api.search import setup_search_routes

        app = FakeApplication()
        setup_search_routes(app)
        routes = {(method, path) for method, path, _ in app.router.routes}
        assert ("GET", "/api/search") in routes


# ---------------------------------------------------------------------------
# GET /api/search – validation
# ---------------------------------------------------------------------------


class TestHandleSearchValidation:
    def test_missing_q_raises_bad_request(self):
        from bot.api.search import handle_search

        request = _make_request(query_params={})
        try:
            asyncio.run(handle_search(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest as exc:
            assert "q" in exc.reason.lower()

    def test_empty_q_raises_bad_request(self):
        from bot.api.search import handle_search

        request = _make_request(query_params={"q": "   "})
        try:
            asyncio.run(handle_search(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest:
            pass

    def test_invalid_limit_raises_bad_request(self):
        from bot.api.search import handle_search

        request = _make_request(query_params={"q": "test", "limit": "not-a-number"})
        try:
            asyncio.run(handle_search(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest as exc:
            assert "limit" in exc.reason.lower()


# ---------------------------------------------------------------------------
# GET /api/search – results via Music cog resolver
# ---------------------------------------------------------------------------


class TestHandleSearchWithCog:
    def test_returns_results_from_music_cog_resolver(self):
        from bot.api.search import handle_search

        results = [_make_result("Song A"), _make_result("Song B")]
        resolver = _make_resolver(results)
        cog = _make_music_cog(resolver)
        bot = _make_bot(cog)
        request = _make_request(
            query_params={"q": "test query"},
            app_data={"bot": bot},
        )
        resp = asyncio.run(handle_search(request))
        data = json.loads(resp.text)
        assert data == {"results": results}
        resolver.search.assert_called_once_with("test query", max_results=5)

    def test_default_limit_is_5(self):
        from bot.api.search import handle_search

        resolver = _make_resolver([])
        cog = _make_music_cog(resolver)
        bot = _make_bot(cog)
        request = _make_request(
            query_params={"q": "test"},
            app_data={"bot": bot},
        )
        asyncio.run(handle_search(request))
        _, kwargs = resolver.search.call_args
        assert kwargs["max_results"] == 5

    def test_custom_limit_passed_to_resolver(self):
        from bot.api.search import handle_search

        resolver = _make_resolver([])
        cog = _make_music_cog(resolver)
        bot = _make_bot(cog)
        request = _make_request(
            query_params={"q": "test", "limit": "10"},
            app_data={"bot": bot},
        )
        asyncio.run(handle_search(request))
        _, kwargs = resolver.search.call_args
        assert kwargs["max_results"] == 10

    def test_limit_clamped_to_max_25(self):
        from bot.api.search import handle_search

        resolver = _make_resolver([])
        cog = _make_music_cog(resolver)
        bot = _make_bot(cog)
        request = _make_request(
            query_params={"q": "test", "limit": "999"},
            app_data={"bot": bot},
        )
        asyncio.run(handle_search(request))
        _, kwargs = resolver.search.call_args
        assert kwargs["max_results"] == 25

    def test_limit_clamped_to_min_1(self):
        from bot.api.search import handle_search

        resolver = _make_resolver([])
        cog = _make_music_cog(resolver)
        bot = _make_bot(cog)
        request = _make_request(
            query_params={"q": "test", "limit": "0"},
            app_data={"bot": bot},
        )
        asyncio.run(handle_search(request))
        _, kwargs = resolver.search.call_args
        assert kwargs["max_results"] == 1

    def test_no_music_cog_uses_injectable_resolver(self):
        from bot.api.search import handle_search

        results = [_make_result("Injected Track")]
        resolver = _make_resolver(results)
        request = _make_request(query_params={"q": "test"})
        resp = asyncio.run(handle_search(request, _resolver_factory=lambda: resolver))
        data = json.loads(resp.text)
        assert data == {"results": results}

    def test_empty_results_returns_empty_list(self):
        from bot.api.search import handle_search

        resolver = _make_resolver([])
        request = _make_request(query_params={"q": "nothing"})
        resp = asyncio.run(handle_search(request, _resolver_factory=lambda: resolver))
        data = json.loads(resp.text)
        assert data == {"results": []}

    def test_result_fields_preserved(self):
        from bot.api.search import handle_search

        result = _make_result(
            title="Cool Track",
            url="https://youtube.com/watch?v=xyz",
            duration=300,
            thumbnail="https://i.ytimg.com/vi/xyz/default.jpg",
        )
        resolver = _make_resolver([result])
        request = _make_request(query_params={"q": "cool track"})
        resp = asyncio.run(handle_search(request, _resolver_factory=lambda: resolver))
        data = json.loads(resp.text)
        assert data["results"][0] == result


# ---------------------------------------------------------------------------
# GET /api/search – no bot in app (fallback resolver path)
# ---------------------------------------------------------------------------


class TestHandleSearchNoBotInApp:
    def test_no_bot_uses_injectable_factory(self):
        from bot.api.search import handle_search

        resolver = _make_resolver([_make_result("Fallback Track")])
        request = _make_request(query_params={"q": "fallback"})
        resp = asyncio.run(handle_search(request, _resolver_factory=lambda: resolver))
        data = json.loads(resp.text)
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Fallback Track"

    def test_bot_set_but_no_music_cog_uses_injectable_factory(self):
        from bot.api.search import handle_search

        bot = _make_bot(music_cog=None)
        resolver = _make_resolver([_make_result("Cog Absent Track")])
        request = _make_request(
            query_params={"q": "absent"},
            app_data={"bot": bot},
        )
        resp = asyncio.run(handle_search(request, _resolver_factory=lambda: resolver))
        data = json.loads(resp.text)
        assert data["results"][0]["title"] == "Cog Absent Track"


# ---------------------------------------------------------------------------
# GET /api/search – resolver raises exception → 503 Search unavailable
# ---------------------------------------------------------------------------


class TestHandleSearchError:
    def test_resolver_exception_returns_503(self):
        from bot.api.search import handle_search

        def bad_factory():
            resolver = MagicMock()
            resolver.search.side_effect = RuntimeError("something broke")
            return resolver

        request = _make_request(query_params={"q": "test"})
        resp = asyncio.run(handle_search(request, _resolver_factory=bad_factory))
        assert resp.status == 503
        data = json.loads(resp.text)
        assert data == {"error": "Search unavailable"}

    def test_resolver_exception_returns_json_content_type(self):
        from bot.api.search import handle_search

        def bad_factory():
            resolver = MagicMock()
            resolver.search.side_effect = Exception("fail")
            return resolver

        request = _make_request(query_params={"q": "test"})
        resp = asyncio.run(handle_search(request, _resolver_factory=bad_factory))
        assert resp.content_type == "application/json"


# ---------------------------------------------------------------------------
# create_app integration: search routes are registered
# ---------------------------------------------------------------------------


class TestCreateAppIncludesSearchRoutes:
    def test_search_route_registered(self):
        from bot.api.server import create_app

        app = create_app()
        routes = {(method, path) for method, path, _ in app.router.routes}
        assert ("GET", "/api/search") in routes
