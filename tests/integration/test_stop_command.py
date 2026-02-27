"""Integration tests for stop command (US-008)."""
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
# stop command tests
# ---------------------------------------------------------------------------

class TestStopCommand:
    def test_stop_while_playing_replies_stopped_and_disconnected(self):
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "Stopped and disconnected."

    def test_stop_while_paused_replies_stopped_and_disconnected(self):
        vc = _make_vc(playing=False, paused=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "Stopped and disconnected."

    def test_stop_while_idle_but_connected_replies_stopped_and_disconnected(self):
        vc = _make_vc(playing=False, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "Stopped and disconnected."

    def test_stop_calls_vc_stop(self):
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        vc.stop.assert_called_once()

    def test_stop_calls_vc_disconnect(self):
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        vc.disconnect.assert_called_once()

    def test_stop_clears_the_queue(self):
        vc = _make_vc(playing=True)
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        queue.add(_make_track("Track 1"))
        queue.add(_make_track("Track 2"))
        cog, vm = _make_cog_with_vm(vc, registry)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        assert queue.list() == []

    def test_stop_when_not_connected_replies_not_in_voice_channel(self):
        bot = MagicMock()
        bot.loop = asyncio.new_event_loop()
        cog = Music(bot)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "I'm not in a voice channel."

    def test_stop_when_not_connected_does_not_clear_queue(self):
        bot = MagicMock()
        bot.loop = asyncio.new_event_loop()
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        queue.add(_make_track("Track 1"))
        cog = Music(bot, queue_registry=registry)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        # Queue should still have the track since stop did nothing
        assert len(queue.list()) == 1

    def test_stop_sends_exactly_one_message(self):
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        assert ctx.send.call_count == 1

    def test_stop_disconnects_voice_manager(self):
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx()
        asyncio.run(cog.stop(ctx))
        assert not vm.is_connected()
