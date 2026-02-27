"""Integration tests for queue command (US-009)."""
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
# queue command tests
# ---------------------------------------------------------------------------

class TestQueueCommand:
    def test_queue_empty_queue_and_no_current_track_replies_text(self):
        """When queue is empty and nothing is playing, send plain text message."""
        bot = MagicMock()
        cog = Music(bot)
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        msg = ctx.send.call_args[0][0]
        assert msg == "The queue is empty."

    def test_queue_with_current_track_sends_embed(self):
        """When a track is currently playing, an embed is sent."""
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        cog._current_tracks[GUILD_ID] = _make_track(title="Playing Song")
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        call_kwargs = ctx.send.call_args[1]
        assert "embed" in call_kwargs

    def test_queue_with_current_track_shows_now_playing_label(self):
        """Currently playing track is shown with 'Now Playing' label."""
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        cog._current_tracks[GUILD_ID] = _make_track(title="My Favorite Song")
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        embed = ctx.send.call_args[1]["embed"]
        assert "Now Playing" in embed.description
        assert "My Favorite Song" in embed.description

    def test_queue_with_queued_tracks_sends_embed(self):
        """When there are queued tracks, an embed is sent."""
        bot = MagicMock()
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        queue.add(_make_track(title="Track 1"))
        cog = Music(bot, queue_registry=registry)
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        call_kwargs = ctx.send.call_args[1]
        assert "embed" in call_kwargs

    def test_queue_with_queued_tracks_shows_track_titles(self):
        """Queued track titles appear in the embed description."""
        bot = MagicMock()
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        queue.add(_make_track(title="First Song"))
        queue.add(_make_track(title="Second Song"))
        cog = Music(bot, queue_registry=registry)
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        embed = ctx.send.call_args[1]["embed"]
        assert "First Song" in embed.description
        assert "Second Song" in embed.description

    def test_queue_with_more_than_10_tracks_shows_max_10(self):
        """Queue embed shows a maximum of 10 tracks."""
        bot = MagicMock()
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        for i in range(12):
            queue.add(_make_track(title=f"Track {i + 1}"))
        cog = Music(bot, queue_registry=registry)
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        embed = ctx.send.call_args[1]["embed"]
        # Track 11 and 12 should NOT appear as numbered entries
        assert "Track 11" not in embed.description
        assert "Track 12" not in embed.description

    def test_queue_with_more_than_10_tracks_shows_and_n_more(self):
        """When queue has >10 tracks, shows '...and N more'."""
        bot = MagicMock()
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        for i in range(13):
            queue.add(_make_track(title=f"Track {i + 1}"))
        cog = Music(bot, queue_registry=registry)
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        embed = ctx.send.call_args[1]["embed"]
        assert "...and 3 more" in embed.description

    def test_queue_sends_exactly_one_message(self):
        """Queue command sends exactly one message."""
        bot = MagicMock()
        registry = GuildQueueRegistry()
        queue = registry.get_queue(GUILD_ID)
        queue.add(_make_track())
        cog = Music(bot, queue_registry=registry)
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        assert ctx.send.call_count == 1

    def test_queue_with_only_current_track_no_queued_tracks_shows_embed(self):
        """Only current track, no queued tracks → embed with Now Playing, no Up Next."""
        vc = _make_vc(playing=True)
        cog, vm = _make_cog_with_vm(vc)
        cog._current_tracks[GUILD_ID] = _make_track(title="Solo Song")
        ctx = _make_ctx()
        asyncio.run(cog.queue(ctx))
        embed = ctx.send.call_args[1]["embed"]
        assert "Now Playing" in embed.description
        assert "Solo Song" in embed.description
