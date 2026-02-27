"""Integration tests for skip command (US-007)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.audio.resolver import AudioTrack
from bot.audio.queue import GuildQueueRegistry
from bot.cogs.music import Music

GUILD_ID = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vc(playing=False, paused=False):
    """Return a mock discord.VoiceClient."""
    vc = MagicMock()
    vc.disconnect = AsyncMock()
    vc.play = MagicMock()
    vc.pause = MagicMock()
    vc.resume = MagicMock()
    vc.stop = MagicMock()
    vc.is_playing = MagicMock(return_value=playing)
    vc.is_paused = MagicMock(return_value=paused)
    return vc


def _make_ctx(guild_id=GUILD_ID):
    """Return a mocked discord Context."""
    ctx = MagicMock()
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.guild.id = guild_id
    return ctx


def _make_cog_with_vm(vc, queue_registry=None):
    """Build a Music cog with a pre-connected VoiceManager."""
    bot = MagicMock()
    bot.loop = asyncio.new_event_loop()
    ffmpeg = MagicMock()
    from bot.audio.voice import VoiceManager
    vm = VoiceManager(ffmpeg_source_class=ffmpeg)
    vm._voice_client = vc
    registry = queue_registry if queue_registry is not None else GuildQueueRegistry()
    cog = Music(bot, ffmpeg_source_class=ffmpeg, voice_managers={GUILD_ID: vm}, queue_registry=registry)
    return cog, vm


def _make_track(title="Test Track", url="http://test.com/audio"):
    return AudioTrack(title=title, url=url, stream_url=url, duration=180, source="youtube")


# ---------------------------------------------------------------------------
# skip command tests
# ---------------------------------------------------------------------------

class TestSkipCommand:
    def test_skip_while_playing_with_next_track_replies_now_playing(self):
        vc = _make_vc(playing=True)
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        next_track = _make_track(title="Next Song")
        queue.add(next_track)
        cog, vm = _make_cog_with_vm(vc, registry)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        msg = ctx.send.call_args[0][0]
        assert "Skipped. Now playing:" in msg
        assert "Next Song" in msg

    def test_skip_while_playing_calls_vc_stop(self):
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        vc.stop.assert_called_once()

    def test_skip_while_playing_no_next_track_replies_queue_empty(self):
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "Skipped. Queue is empty."

    def test_skip_while_paused_with_next_track_replies_now_playing(self):
        vc = _make_vc(playing=False, paused=True)
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        next_track = _make_track(title="Another Song")
        queue.add(next_track)
        cog, vm = _make_cog_with_vm(vc, registry)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        msg = ctx.send.call_args[0][0]
        assert "Skipped. Now playing:" in msg
        assert "Another Song" in msg

    def test_skip_while_paused_no_next_track_replies_queue_empty(self):
        vc = _make_vc(playing=False, paused=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "Skipped. Queue is empty."

    def test_skip_when_nothing_playing_replies_nothing_to_skip(self):
        vc = _make_vc(playing=False, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "Nothing to skip."

    def test_skip_when_not_connected_replies_nothing_to_skip(self):
        bot = MagicMock()
        bot.loop = asyncio.new_event_loop()
        cog = Music(bot)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "Nothing to skip."

    def test_skip_when_nothing_playing_does_not_call_stop(self):
        vc = _make_vc(playing=False, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        vc.stop.assert_not_called()

    def test_skip_with_next_track_starts_playback(self):
        vc = _make_vc(playing=True)
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        next_track = _make_track(title="Next Song", url="http://test.com/next")
        queue.add(next_track)
        cog, vm = _make_cog_with_vm(vc, registry)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        vc.play.assert_called_once()

    def test_skip_sends_exactly_one_message(self):
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.skip(ctx))
        assert ctx.send.call_count == 1
