"""Integration tests for play command (US-005)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.audio.resolver import AudioTrack, UnsupportedSourceError
from bot.audio.queue import GuildQueueRegistry
from bot.cogs.music import Music

GUILD_ID = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_track(title="Test Song", stream_url="https://stream.example.com/audio.webm"):
    return AudioTrack(
        title=title,
        url="https://youtube.com/watch?v=abc123",
        stream_url=stream_url,
        duration=210,
        source="youtube",
    )


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


def _make_cog(track=None, ffmpeg_source_class=None):
    """Build a Music cog with all external deps mocked."""
    bot = MagicMock()
    bot.loop = asyncio.new_event_loop()
    mock_resolver = MagicMock()
    if track is not None:
        mock_resolver.resolve = MagicMock(return_value=track)
    ffmpeg = ffmpeg_source_class or MagicMock()
    cog = Music(bot, resolver=mock_resolver, ffmpeg_source_class=ffmpeg)
    return cog, mock_resolver


# ---------------------------------------------------------------------------
# User not in voice channel
# ---------------------------------------------------------------------------

class TestPlayUserNotInVoice:
    def test_sends_error_when_user_not_in_voice(self):
        cog, _ = _make_cog(_make_track())
        ctx = _make_ctx(in_voice=False)
        asyncio.run(cog.play(ctx, query="test song"))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert "voice channel" in message.lower()

    def test_does_not_resolve_query_when_not_in_voice(self):
        cog, resolver = _make_cog(_make_track())
        ctx = _make_ctx(in_voice=False)
        asyncio.run(cog.play(ctx, query="test song"))
        resolver.resolve.assert_not_called()

    def test_does_not_start_playback_when_not_in_voice(self):
        cog, _ = _make_cog(_make_track())
        vc = _make_vc()
        ctx = _make_ctx(in_voice=False, vc=vc)
        asyncio.run(cog.play(ctx, query="test song"))
        vc.play.assert_not_called()


# ---------------------------------------------------------------------------
# Bot joins channel automatically
# ---------------------------------------------------------------------------

class TestPlayBotJoinsChannel:
    def test_bot_joins_users_channel(self):
        cog, _ = _make_cog(_make_track())
        vc = _make_vc()
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="test song"))
        ctx.author.voice.channel.connect.assert_called_once()

    def test_on_track_end_callback_registered_after_join(self):
        cog, _ = _make_cog(_make_track())
        vc = _make_vc()
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="test song"))
        vm = cog._get_voice_manager(GUILD_ID)
        assert vm._on_track_end is not None

    def test_bot_does_not_rejoin_when_already_connected(self):
        track1 = _make_track(title="Song 1")
        track2 = _make_track(title="Song 2")
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = [track1, track2]
        bot = MagicMock()
        bot.loop = asyncio.new_event_loop()
        ffmpeg = MagicMock()
        cog = Music(bot, resolver=mock_resolver, ffmpeg_source_class=ffmpeg)

        vc = _make_vc(playing=False)
        ctx = _make_ctx(vc=vc)

        # First play
        asyncio.run(cog.play(ctx, query="song 1"))
        # Simulate vc is now playing
        vc.is_playing.return_value = True

        # Second play
        asyncio.run(cog.play(ctx, query="song 2"))

        # connect() called only once (for first play)
        assert ctx.author.voice.channel.connect.call_count == 1


# ---------------------------------------------------------------------------
# Resolver called with query
# ---------------------------------------------------------------------------

class TestPlayResolution:
    def test_resolver_called_with_query(self):
        cog, resolver = _make_cog(_make_track())
        ctx = _make_ctx()
        asyncio.run(cog.play(ctx, query="never gonna give you up"))
        resolver.resolve.assert_called_once_with("never gonna give you up")


# ---------------------------------------------------------------------------
# Queue and playback logic
# ---------------------------------------------------------------------------

class TestPlayQueueBehaviour:
    def test_starts_playback_immediately_when_idle(self):
        track = _make_track()
        cog, _ = _make_cog(track)
        vc = _make_vc(playing=False, paused=False)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="test song"))
        # vc.play should have been called via VoiceManager
        vc.play.assert_called_once()

    def test_track_queued_when_already_playing(self):
        track = _make_track()
        cog, _ = _make_cog(track)
        vc = _make_vc(playing=True, paused=False)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="test song"))
        # vc.play should NOT be called (already playing)
        vc.play.assert_not_called()
        # Track should remain in the queue (not popped)
        queue = cog._queue_registry.get_queue(GUILD_ID)
        assert len(queue.list()) == 1
        assert queue.list()[0] is track

    def test_track_queued_when_paused(self):
        track = _make_track()
        cog, _ = _make_cog(track)
        vc = _make_vc(playing=False, paused=True)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="test song"))
        # vc.play should NOT be called (paused = track in progress)
        vc.play.assert_not_called()
        queue = cog._queue_registry.get_queue(GUILD_ID)
        assert len(queue.list()) == 1

    def test_second_track_queued_when_first_playing(self):
        track1 = _make_track(title="Song 1")
        track2 = _make_track(title="Song 2")
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = [track1, track2]
        bot = MagicMock()
        bot.loop = asyncio.new_event_loop()
        ffmpeg = MagicMock()
        cog = Music(bot, resolver=mock_resolver, ffmpeg_source_class=ffmpeg)

        vc = _make_vc(playing=False)
        ctx = _make_ctx(vc=vc)

        # First play: track1 starts
        asyncio.run(cog.play(ctx, query="song 1"))
        assert vc.play.call_count == 1

        # Simulate vc is now playing
        vc.is_playing.return_value = True

        # Second play: track2 queued
        asyncio.run(cog.play(ctx, query="song 2"))
        assert vc.play.call_count == 1  # still only 1 call

        queue = cog._queue_registry.get_queue(GUILD_ID)
        assert len(queue.list()) == 1
        assert queue.list()[0] is track2

    def test_queue_empty_after_playback_starts(self):
        track = _make_track()
        cog, _ = _make_cog(track)
        vc = _make_vc(playing=False, paused=False)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="test song"))
        # Track was popped from queue to play
        queue = cog._queue_registry.get_queue(GUILD_ID)
        assert len(queue.list()) == 0


# ---------------------------------------------------------------------------
# Reply messages
# ---------------------------------------------------------------------------

class TestPlayMessages:
    def test_now_playing_message_when_idle(self):
        track = _make_track(title="Bohemian Rhapsody")
        cog, _ = _make_cog(track)
        vc = _make_vc(playing=False, paused=False)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="queen"))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert "Bohemian Rhapsody" in message
        assert "playing" in message.lower()

    def test_added_to_queue_message_when_already_playing(self):
        track = _make_track(title="Stairway to Heaven")
        cog, _ = _make_cog(track)
        vc = _make_vc(playing=True, paused=False)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="led zeppelin"))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert "Stairway to Heaven" in message

    def test_added_to_queue_message_when_paused(self):
        track = _make_track(title="Hotel California")
        cog, _ = _make_cog(track)
        vc = _make_vc(playing=False, paused=True)
        ctx = _make_ctx(vc=vc)
        asyncio.run(cog.play(ctx, query="eagles"))
        ctx.send.assert_called_once()
        message = ctx.send.call_args[0][0]
        assert "Hotel California" in message

    def test_defer_called_at_start(self):
        track = _make_track()
        cog, _ = _make_cog(track)
        ctx = _make_ctx()
        asyncio.run(cog.play(ctx, query="test"))
        ctx.defer.assert_called_once()
