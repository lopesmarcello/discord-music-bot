"""Unit tests for VoiceManager (US-004)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from bot.audio.voice import VoiceManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_voice_client(*, playing: bool = False, paused: bool = False) -> MagicMock:
    """Return a mock discord.VoiceClient."""
    vc = MagicMock()
    vc.is_playing.return_value = playing
    vc.is_paused.return_value = paused
    vc.disconnect = AsyncMock()
    vc.play = MagicMock()
    vc.pause = MagicMock()
    vc.resume = MagicMock()
    vc.stop = MagicMock()
    return vc


def _make_mock_channel(voice_client: MagicMock | None = None) -> MagicMock:
    """Return a mock discord.VoiceChannel whose connect() returns *voice_client*."""
    channel = MagicMock()
    vc = voice_client if voice_client is not None else _make_mock_voice_client()
    channel.connect = AsyncMock(return_value=vc)
    return channel, vc


def _make_ffmpeg_source_class() -> MagicMock:
    """Return a mock FFmpegPCMAudio class."""
    mock_class = MagicMock()
    mock_class.return_value = MagicMock()
    return mock_class


# ---------------------------------------------------------------------------
# VoiceManager.join
# ---------------------------------------------------------------------------

class TestJoin:
    def test_join_connects_to_channel(self):
        channel, vc = _make_mock_channel()
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        channel.connect.assert_called_once()

    def test_join_stores_voice_client(self):
        channel, vc = _make_mock_channel()
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        assert manager._voice_client is vc

    def test_join_replaces_existing_connection(self):
        channel1, vc1 = _make_mock_channel()
        channel2, vc2 = _make_mock_channel()
        manager = VoiceManager()
        asyncio.run(manager.join(channel1))
        asyncio.run(manager.join(channel2))
        assert manager._voice_client is vc2


# ---------------------------------------------------------------------------
# VoiceManager.leave
# ---------------------------------------------------------------------------

class TestLeave:
    def test_leave_disconnects_voice_client(self):
        channel, vc = _make_mock_channel()
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        asyncio.run(manager.leave())
        vc.disconnect.assert_called_once()

    def test_leave_clears_voice_client(self):
        channel, vc = _make_mock_channel()
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        asyncio.run(manager.leave())
        assert manager._voice_client is None

    def test_leave_when_not_connected_does_nothing(self):
        manager = VoiceManager()
        # Should not raise
        asyncio.run(manager.leave())


# ---------------------------------------------------------------------------
# VoiceManager.play
# ---------------------------------------------------------------------------

class TestPlay:
    def test_play_creates_ffmpeg_source(self):
        channel, vc = _make_mock_channel()
        ffmpeg_class = _make_ffmpeg_source_class()
        manager = VoiceManager(ffmpeg_source_class=ffmpeg_class)
        asyncio.run(manager.join(channel))
        asyncio.run(manager.play("https://stream.example.com/audio.webm"))
        ffmpeg_class.assert_called_once_with(
            "https://stream.example.com/audio.webm",
            before_options=manager.FFMPEG_BEFORE_OPTIONS,
            options=manager.FFMPEG_OPTIONS,
        )

    def test_play_calls_voice_client_play(self):
        channel, vc = _make_mock_channel()
        ffmpeg_class = _make_ffmpeg_source_class()
        manager = VoiceManager(ffmpeg_source_class=ffmpeg_class)
        asyncio.run(manager.join(channel))
        asyncio.run(manager.play("https://stream.example.com/audio.webm"))
        vc.play.assert_called_once()

    def test_play_passes_after_callback_to_voice_client(self):
        channel, vc = _make_mock_channel()
        ffmpeg_class = _make_ffmpeg_source_class()
        manager = VoiceManager(ffmpeg_source_class=ffmpeg_class)
        asyncio.run(manager.join(channel))
        asyncio.run(manager.play("https://stream.example.com/audio.webm"))
        call_kwargs = vc.play.call_args[1]
        assert "after" in call_kwargs
        assert callable(call_kwargs["after"])

    def test_play_without_connection_raises(self):
        manager = VoiceManager()
        with pytest.raises(RuntimeError):
            asyncio.run(manager.play("https://stream.example.com/audio.webm"))


# ---------------------------------------------------------------------------
# VoiceManager on_track_end callback
# ---------------------------------------------------------------------------

class TestOnTrackEnd:
    def test_track_end_callback_is_called_after_playback(self):
        channel, vc = _make_mock_channel()
        ffmpeg_class = _make_ffmpeg_source_class()
        manager = VoiceManager(ffmpeg_source_class=ffmpeg_class)

        on_end = MagicMock()
        manager.set_on_track_end(on_end)

        asyncio.run(manager.join(channel))
        asyncio.run(manager.play("https://stream.example.com/audio.webm"))

        # Simulate discord calling the "after" callback (track finished)
        after_cb = vc.play.call_args[1]["after"]
        after_cb(None)  # None means no error

        on_end.assert_called_once_with(None)

    def test_track_end_callback_receives_error(self):
        channel, vc = _make_mock_channel()
        ffmpeg_class = _make_ffmpeg_source_class()
        manager = VoiceManager(ffmpeg_source_class=ffmpeg_class)

        on_end = MagicMock()
        manager.set_on_track_end(on_end)

        asyncio.run(manager.join(channel))
        asyncio.run(manager.play("https://stream.example.com/audio.webm"))

        err = Exception("Playback error")
        after_cb = vc.play.call_args[1]["after"]
        after_cb(err)

        on_end.assert_called_once_with(err)

    def test_no_track_end_callback_registered_does_not_raise(self):
        channel, vc = _make_mock_channel()
        ffmpeg_class = _make_ffmpeg_source_class()
        manager = VoiceManager(ffmpeg_source_class=ffmpeg_class)

        asyncio.run(manager.join(channel))
        asyncio.run(manager.play("https://stream.example.com/audio.webm"))

        after_cb = vc.play.call_args[1]["after"]
        after_cb(None)  # Should not raise even without a callback registered


# ---------------------------------------------------------------------------
# VoiceManager.pause
# ---------------------------------------------------------------------------

class TestPause:
    def test_pause_calls_voice_client_pause(self):
        vc = _make_mock_voice_client(playing=True)
        channel, _ = _make_mock_channel(vc)
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        manager.pause()
        vc.pause.assert_called_once()

    def test_pause_when_not_playing_does_not_call_pause(self):
        vc = _make_mock_voice_client(playing=False)
        channel, _ = _make_mock_channel(vc)
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        manager.pause()
        vc.pause.assert_not_called()

    def test_pause_when_not_connected_does_nothing(self):
        manager = VoiceManager()
        # Should not raise
        manager.pause()


# ---------------------------------------------------------------------------
# VoiceManager.resume
# ---------------------------------------------------------------------------

class TestResume:
    def test_resume_calls_voice_client_resume(self):
        vc = _make_mock_voice_client(paused=True)
        channel, _ = _make_mock_channel(vc)
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        manager.resume()
        vc.resume.assert_called_once()

    def test_resume_when_not_paused_does_not_call_resume(self):
        vc = _make_mock_voice_client(paused=False)
        channel, _ = _make_mock_channel(vc)
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        manager.resume()
        vc.resume.assert_not_called()

    def test_resume_when_not_connected_does_nothing(self):
        manager = VoiceManager()
        # Should not raise
        manager.resume()


# ---------------------------------------------------------------------------
# VoiceManager.stop
# ---------------------------------------------------------------------------

class TestStop:
    def test_stop_calls_voice_client_stop(self):
        channel, vc = _make_mock_channel()
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        manager.stop()
        vc.stop.assert_called_once()

    def test_stop_when_not_connected_does_nothing(self):
        manager = VoiceManager()
        # Should not raise
        manager.stop()

    def test_stop_does_not_disconnect(self):
        channel, vc = _make_mock_channel()
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        manager.stop()
        vc.disconnect.assert_not_called()
        assert manager._voice_client is vc


# ---------------------------------------------------------------------------
# VoiceManager.is_playing
# ---------------------------------------------------------------------------

class TestIsPlaying:
    def test_is_playing_returns_true_when_playing(self):
        vc = _make_mock_voice_client(playing=True)
        channel, _ = _make_mock_channel(vc)
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        assert manager.is_playing() is True

    def test_is_playing_returns_false_when_not_playing(self):
        vc = _make_mock_voice_client(playing=False)
        channel, _ = _make_mock_channel(vc)
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        assert manager.is_playing() is False

    def test_is_playing_returns_false_when_not_connected(self):
        manager = VoiceManager()
        assert manager.is_playing() is False


# ---------------------------------------------------------------------------
# VoiceManager.is_paused
# ---------------------------------------------------------------------------

class TestIsPaused:
    def test_is_paused_returns_true_when_paused(self):
        vc = _make_mock_voice_client(paused=True)
        channel, _ = _make_mock_channel(vc)
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        assert manager.is_paused() is True

    def test_is_paused_returns_false_when_not_paused(self):
        vc = _make_mock_voice_client(paused=False)
        channel, _ = _make_mock_channel(vc)
        manager = VoiceManager()
        asyncio.run(manager.join(channel))
        assert manager.is_paused() is False

    def test_is_paused_returns_false_when_not_connected(self):
        manager = VoiceManager()
        assert manager.is_paused() is False


# ---------------------------------------------------------------------------
# VoiceManager._get_ffmpeg_source_class lazy import path
# ---------------------------------------------------------------------------

class TestGetFfmpegSourceClassLazyImport:
    def test_lazy_import_when_ffmpeg_source_class_not_provided(self):
        """When ffmpeg_source_class is None, resolver imports discord from sys.modules."""
        from unittest.mock import patch
        mock_discord = MagicMock()
        with patch.dict("sys.modules", {"discord": mock_discord}):
            manager = VoiceManager()
            result = manager._get_ffmpeg_source_class()
        assert result is mock_discord.FFmpegPCMAudio
