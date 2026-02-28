"""Tests for US-003: Queue and playback API endpoints."""
from __future__ import annotations

import asyncio
import json
import sys
from unittest.mock import AsyncMock, MagicMock

# Shared stubs already injected via tests/conftest.py (aiohttp, jwt).
from tests.conftest import (
    FakeApplication,
    FakeHTTPBadRequest,
    FakeHTTPException,
    FakeHTTPServiceUnavailable,
    FakeResponse,
)

_mock_web = sys.modules["aiohttp.web"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_track(
    title="Test Track",
    url="http://example.com/song",
    duration=180,
    source="youtube",
):
    track = MagicMock()
    track.title = title
    track.url = url
    track.duration = duration
    track.source = source
    return track


def _make_vm(is_playing=False, is_paused=False, is_connected=True):
    vm = MagicMock()
    vm.is_playing.return_value = is_playing
    vm.is_paused.return_value = is_paused
    vm.is_connected.return_value = is_connected
    vm.pause = MagicMock()
    vm.resume = MagicMock()
    vm.stop = MagicMock()
    vm.leave = AsyncMock()
    return vm


def _make_queue(tracks=None):
    q = MagicMock()
    q.list.return_value = list(tracks) if tracks else []
    q.clear = MagicMock()
    return q


def _make_music_cog(
    guild_id=123,
    current_track=None,
    queue_tracks=None,
    vm=None,
):
    cog = MagicMock()
    cog._current_tracks = {}
    if current_track is not None:
        cog._current_tracks[guild_id] = current_track

    fake_queue = _make_queue(queue_tracks)
    registry = MagicMock()
    registry.get_queue.return_value = fake_queue
    cog._queue_registry = registry

    _vm = vm if vm is not None else _make_vm()
    cog._get_voice_manager = MagicMock(return_value=_vm)
    cog._play_next = AsyncMock()

    return cog, _vm, fake_queue


def _make_bot(music_cog=None):
    bot = MagicMock()
    bot.cogs = {}
    if music_cog is not None:
        bot.cogs["Music"] = music_cog
    return bot


def _make_request(guild_id=None, app_data=None):
    """Return a fake aiohttp Request with query params and app dict."""
    request = MagicMock()
    if guild_id is not None:
        request.rel_url.query = {"guild_id": str(guild_id)}
    else:
        request.rel_url.query = {}

    # Use a real FakeApplication so app.get() and app[] work correctly.
    app = FakeApplication()
    if app_data:
        for k, v in app_data.items():
            app[k] = v
    request.app = app
    return request


# ---------------------------------------------------------------------------
# setup_player_routes
# ---------------------------------------------------------------------------


class TestSetupPlayerRoutes:
    def test_registers_all_routes(self):
        from bot.api.player import setup_player_routes

        app = FakeApplication()
        setup_player_routes(app)
        routes = {(method, path) for method, path, _ in app.router.routes}
        assert ("GET", "/api/queue") in routes
        assert ("POST", "/api/queue/skip") in routes
        assert ("POST", "/api/queue/clear") in routes
        assert ("GET", "/api/playback") in routes
        assert ("POST", "/api/playback/pause") in routes
        assert ("POST", "/api/playback/resume") in routes
        assert ("POST", "/api/playback/stop") in routes


# ---------------------------------------------------------------------------
# GET /api/queue
# ---------------------------------------------------------------------------


class TestHandleQueueGet:
    def test_no_bot_returns_empty_queue(self):
        from bot.api.player import handle_queue_get

        request = _make_request(guild_id=123)
        resp = asyncio.run(handle_queue_get(request))
        data = json.loads(resp.text)
        assert data == {"current": None, "tracks": []}

    def test_empty_queue_and_no_current(self):
        from bot.api.player import handle_queue_get

        cog, vm, q = _make_music_cog()
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_queue_get(request))
        data = json.loads(resp.text)
        assert data["current"] is None
        assert data["tracks"] == []

    def test_returns_current_track(self):
        from bot.api.player import handle_queue_get

        track = _make_track("Song A", url="http://example.com/a", duration=120, source="youtube")
        cog, vm, q = _make_music_cog(guild_id=123, current_track=track)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_queue_get(request))
        data = json.loads(resp.text)
        assert data["current"] == {
            "title": "Song A",
            "url": "http://example.com/a",
            "duration": 120,
            "source": "youtube",
        }
        assert data["tracks"] == []

    def test_returns_queued_tracks(self):
        from bot.api.player import handle_queue_get

        tracks = [
            _make_track("Song B", url="http://example.com/b", duration=200, source="youtube"),
            _make_track("Song C", url="http://example.com/c", duration=300, source="search"),
        ]
        cog, vm, q = _make_music_cog(queue_tracks=tracks)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_queue_get(request))
        data = json.loads(resp.text)
        assert len(data["tracks"]) == 2
        assert data["tracks"][0]["title"] == "Song B"
        assert data["tracks"][1]["title"] == "Song C"

    def test_missing_guild_id_raises_bad_request(self):
        from bot.api.player import handle_queue_get

        request = _make_request(guild_id=None)
        try:
            asyncio.run(handle_queue_get(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest:
            pass

    def test_invalid_guild_id_raises_bad_request(self):
        from bot.api.player import handle_queue_get

        request = MagicMock()
        request.rel_url.query = {"guild_id": "not-a-number"}
        request.app = FakeApplication()
        try:
            asyncio.run(handle_queue_get(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest:
            pass


# ---------------------------------------------------------------------------
# POST /api/queue/skip
# ---------------------------------------------------------------------------


class TestHandleQueueSkip:
    def test_skips_and_returns_next_track(self):
        from bot.api.player import handle_queue_get, handle_queue_skip

        next_track = _make_track("Song Next")
        vm = _make_vm(is_playing=True)
        cog, _, q = _make_music_cog(vm=vm)

        # After _play_next is called, simulate it setting current track
        async def fake_play_next(guild_id):
            cog._current_tracks[guild_id] = next_track

        cog._play_next.side_effect = fake_play_next

        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_queue_skip(request))
        data = json.loads(resp.text)
        assert data["skipped"] is True
        assert data["current"]["title"] == "Song Next"
        vm.stop.assert_called_once()
        cog._play_next.assert_awaited_once_with(123)

    def test_skips_when_paused(self):
        from bot.api.player import handle_queue_skip

        vm = _make_vm(is_playing=False, is_paused=True)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_queue_skip(request))
        data = json.loads(resp.text)
        assert data["skipped"] is True
        vm.stop.assert_called_once()

    def test_skip_when_nothing_playing_raises_bad_request(self):
        from bot.api.player import handle_queue_skip

        vm = _make_vm(is_playing=False, is_paused=False)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        try:
            asyncio.run(handle_queue_skip(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest:
            pass

    def test_no_bot_raises_service_unavailable(self):
        from bot.api.player import handle_queue_skip

        request = _make_request(guild_id=123)
        try:
            asyncio.run(handle_queue_skip(request))
            assert False, "expected HTTPServiceUnavailable"
        except FakeHTTPServiceUnavailable:
            pass

    def test_skip_queue_empty_returns_null_current(self):
        from bot.api.player import handle_queue_skip

        vm = _make_vm(is_playing=True)
        cog, _, q = _make_music_cog(vm=vm)
        # _play_next sets current to None (empty queue)
        cog._play_next.side_effect = AsyncMock()
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_queue_skip(request))
        data = json.loads(resp.text)
        assert data["skipped"] is True
        assert data["current"] is None


# ---------------------------------------------------------------------------
# POST /api/queue/clear
# ---------------------------------------------------------------------------


class TestHandleQueueClear:
    def test_clears_queue(self):
        from bot.api.player import handle_queue_clear

        cog, vm, q = _make_music_cog()
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_queue_clear(request))
        data = json.loads(resp.text)
        assert data == {"cleared": True}
        q.clear.assert_called_once()

    def test_no_bot_raises_service_unavailable(self):
        from bot.api.player import handle_queue_clear

        request = _make_request(guild_id=123)
        try:
            asyncio.run(handle_queue_clear(request))
            assert False, "expected HTTPServiceUnavailable"
        except FakeHTTPServiceUnavailable:
            pass


# ---------------------------------------------------------------------------
# GET /api/playback
# ---------------------------------------------------------------------------


class TestHandlePlaybackGet:
    def test_no_bot_returns_stopped(self):
        from bot.api.player import handle_playback_get

        request = _make_request(guild_id=123)
        resp = asyncio.run(handle_playback_get(request))
        data = json.loads(resp.text)
        assert data == {"state": "stopped"}

    def test_returns_playing_state(self):
        from bot.api.player import handle_playback_get

        vm = _make_vm(is_playing=True)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_playback_get(request))
        data = json.loads(resp.text)
        assert data == {"state": "playing"}

    def test_returns_paused_state(self):
        from bot.api.player import handle_playback_get

        vm = _make_vm(is_playing=False, is_paused=True)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_playback_get(request))
        data = json.loads(resp.text)
        assert data == {"state": "paused"}

    def test_returns_stopped_state(self):
        from bot.api.player import handle_playback_get

        vm = _make_vm(is_playing=False, is_paused=False)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_playback_get(request))
        data = json.loads(resp.text)
        assert data == {"state": "stopped"}


# ---------------------------------------------------------------------------
# POST /api/playback/pause
# ---------------------------------------------------------------------------


class TestHandlePlaybackPause:
    def test_pauses_playback(self):
        from bot.api.player import handle_playback_pause

        vm = _make_vm(is_playing=True)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_playback_pause(request))
        data = json.loads(resp.text)
        assert data == {"paused": True}
        vm.pause.assert_called_once()

    def test_pause_when_not_playing_raises_bad_request(self):
        from bot.api.player import handle_playback_pause

        vm = _make_vm(is_playing=False)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        try:
            asyncio.run(handle_playback_pause(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest:
            pass

    def test_no_bot_raises_service_unavailable(self):
        from bot.api.player import handle_playback_pause

        request = _make_request(guild_id=123)
        try:
            asyncio.run(handle_playback_pause(request))
            assert False, "expected HTTPServiceUnavailable"
        except FakeHTTPServiceUnavailable:
            pass


# ---------------------------------------------------------------------------
# POST /api/playback/resume
# ---------------------------------------------------------------------------


class TestHandlePlaybackResume:
    def test_resumes_playback(self):
        from bot.api.player import handle_playback_resume

        vm = _make_vm(is_paused=True)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_playback_resume(request))
        data = json.loads(resp.text)
        assert data == {"resumed": True}
        vm.resume.assert_called_once()

    def test_resume_when_not_paused_raises_bad_request(self):
        from bot.api.player import handle_playback_resume

        vm = _make_vm(is_paused=False)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        try:
            asyncio.run(handle_playback_resume(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest:
            pass

    def test_no_bot_raises_service_unavailable(self):
        from bot.api.player import handle_playback_resume

        request = _make_request(guild_id=123)
        try:
            asyncio.run(handle_playback_resume(request))
            assert False, "expected HTTPServiceUnavailable"
        except FakeHTTPServiceUnavailable:
            pass


# ---------------------------------------------------------------------------
# POST /api/playback/stop
# ---------------------------------------------------------------------------


class TestHandlePlaybackStop:
    def test_stops_playback_and_disconnects(self):
        from bot.api.player import handle_playback_stop

        vm = _make_vm(is_connected=True)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        resp = asyncio.run(handle_playback_stop(request))
        data = json.loads(resp.text)
        assert data == {"stopped": True}
        vm.stop.assert_called_once()
        q.clear.assert_called_once()
        assert cog._current_tracks.get(123) is None
        vm.leave.assert_awaited_once()

    def test_stop_when_not_connected_raises_bad_request(self):
        from bot.api.player import handle_playback_stop

        vm = _make_vm(is_connected=False)
        cog, _, q = _make_music_cog(vm=vm)
        bot = _make_bot(cog)
        request = _make_request(guild_id=123, app_data={"bot": bot})
        try:
            asyncio.run(handle_playback_stop(request))
            assert False, "expected HTTPBadRequest"
        except FakeHTTPBadRequest:
            pass

    def test_no_bot_raises_service_unavailable(self):
        from bot.api.player import handle_playback_stop

        request = _make_request(guild_id=123)
        try:
            asyncio.run(handle_playback_stop(request))
            assert False, "expected HTTPServiceUnavailable"
        except FakeHTTPServiceUnavailable:
            pass


# ---------------------------------------------------------------------------
# create_app integration: player routes are registered
# ---------------------------------------------------------------------------


class TestCreateAppIncludesPlayerRoutes:
    def test_player_routes_registered(self):
        from bot.api.server import create_app

        app = create_app()
        routes = {(method, path) for method, path, _ in app.router.routes}
        assert ("GET", "/api/queue") in routes
        assert ("POST", "/api/queue/skip") in routes
        assert ("GET", "/api/playback") in routes

    def test_bot_stored_in_app_when_provided(self):
        from bot.api.server import create_app

        bot = _make_bot()
        app = create_app(bot=bot)
        assert app["bot"] is bot

    def test_no_bot_key_when_not_provided(self):
        from bot.api.server import create_app

        app = create_app()
        assert app.get("bot") is None
