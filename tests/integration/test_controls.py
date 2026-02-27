"""Integration tests for pause/resume commands (US-006)."""
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


def _make_ctx(guild_id=GUILD_ID, in_voice=True, vc=None):
    """Return a mocked discord Context."""
    ctx = MagicMock()
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.guild.id = guild_id

    if in_voice:
        _vc = vc if vc is not None else _make_vc()
        voice_channel = MagicMock()
        voice_channel.connect = AsyncMock(return_value=_vc)
        ctx.author.voice = MagicMock()
        ctx.author.voice.channel = voice_channel
    else:
        ctx.author.voice = None

    return ctx


def _make_cog_with_vm(vc):
    """Build a Music cog with a pre-connected VoiceManager."""
    bot = MagicMock()
    bot.loop = asyncio.new_event_loop()
    ffmpeg = MagicMock()
    from bot.audio.voice import VoiceManager
    vm = VoiceManager(ffmpeg_source_class=ffmpeg)
    vm._voice_client = vc
    cog = Music(bot, ffmpeg_source_class=ffmpeg, voice_managers={GUILD_ID: vm})
    return cog, vm


# ---------------------------------------------------------------------------
# pause command tests
# ---------------------------------------------------------------------------

class TestPauseCommand:
    def test_pause_while_playing_replies_paused(self):
        vc = _make_vc(playing=True, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.pause(ctx))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert message == "Paused."

    def test_pause_while_playing_calls_vc_pause(self):
        vc = _make_vc(playing=True, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.pause(ctx))
        vc.pause.assert_called_once()

    def test_pause_when_not_playing_replies_nothing_playing(self):
        vc = _make_vc(playing=False, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.pause(ctx))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert message == "Nothing is currently playing."

    def test_pause_when_not_playing_does_not_call_vc_pause(self):
        vc = _make_vc(playing=False, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.pause(ctx))
        vc.pause.assert_not_called()

    def test_pause_when_already_paused_replies_nothing_playing(self):
        vc = _make_vc(playing=False, paused=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.pause(ctx))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert message == "Nothing is currently playing."

    def test_pause_when_not_connected_replies_nothing_playing(self):
        bot = MagicMock()
        bot.loop = asyncio.new_event_loop()
        cog = Music(bot)
        ctx = _make_ctx()
        asyncio.run(cog.pause(ctx))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert message == "Nothing is currently playing."


# ---------------------------------------------------------------------------
# resume command tests
# ---------------------------------------------------------------------------

class TestResumeCommand:
    def test_resume_while_paused_replies_resumed(self):
        vc = _make_vc(playing=False, paused=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.resume(ctx))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert message == "Resumed."

    def test_resume_while_paused_calls_vc_resume(self):
        vc = _make_vc(playing=False, paused=True)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.resume(ctx))
        vc.resume.assert_called_once()

    def test_resume_when_not_paused_replies_not_paused(self):
        vc = _make_vc(playing=True, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.resume(ctx))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert message == "Playback is not paused."

    def test_resume_when_not_paused_does_not_call_vc_resume(self):
        vc = _make_vc(playing=True, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.resume(ctx))
        vc.resume.assert_not_called()

    def test_resume_when_idle_replies_not_paused(self):
        vc = _make_vc(playing=False, paused=False)
        cog, vm = _make_cog_with_vm(vc)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.resume(ctx))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert message == "Playback is not paused."

    def test_resume_when_not_connected_replies_not_paused(self):
        bot = MagicMock()
        bot.loop = asyncio.new_event_loop()
        cog = Music(bot)
        ctx = _make_ctx()
        asyncio.run(cog.resume(ctx))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert message == "Playback is not paused."
