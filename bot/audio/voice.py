"""Voice connection manager for Discord audio playback."""
from __future__ import annotations

from typing import Callable, Optional


class VoiceManager:
    """Manages voice channel connection and audio playback for a guild."""

    # FFmpeg options for reliable streaming with reconnect support
    FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    FFMPEG_OPTIONS = "-vn"

    def __init__(self, ffmpeg_source_class=None) -> None:
        self._voice_client = None
        self._on_track_end: Optional[Callable] = None
        self._ffmpeg_source_class = ffmpeg_source_class

    async def join(self, channel: object) -> None:
        """Connect to a voice channel."""
        self._voice_client = await channel.connect()

    async def leave(self) -> None:
        """Disconnect from the voice channel and clear state."""
        if self._voice_client is not None:
            await self._voice_client.disconnect()
            self._voice_client = None

    async def play(self, stream_url: str) -> None:
        """Start audio playback from a stream URL using FFmpeg."""
        if self._voice_client is None:
            raise RuntimeError("Not connected to a voice channel")

        ffmpeg_class = self._get_ffmpeg_source_class()
        source = ffmpeg_class(
            stream_url,
            before_options=self.FFMPEG_BEFORE_OPTIONS,
            options=self.FFMPEG_OPTIONS,
        )

        def _after(error: Optional[Exception]) -> None:
            if self._on_track_end is not None:
                self._on_track_end(error)

        self._voice_client.play(source, after=_after)

    def pause(self) -> None:
        """Pause currently playing audio."""
        if self._voice_client is not None and self._voice_client.is_playing():
            self._voice_client.pause()

    def resume(self) -> None:
        """Resume paused audio."""
        if self._voice_client is not None and self._voice_client.is_paused():
            self._voice_client.resume()

    def stop(self) -> None:
        """Stop audio without disconnecting."""
        if self._voice_client is not None:
            self._voice_client.stop()

    def is_playing(self) -> bool:
        """Return True if audio is currently playing."""
        if self._voice_client is None:
            return False
        return self._voice_client.is_playing()

    def is_paused(self) -> bool:
        """Return True if audio is currently paused."""
        if self._voice_client is None:
            return False
        return self._voice_client.is_paused()

    def is_connected(self) -> bool:
        """Return True if connected to a voice channel."""
        return self._voice_client is not None

    def set_on_track_end(self, callback: Callable) -> None:
        """Register a callback to be called when a track ends."""
        self._on_track_end = callback

    def _get_ffmpeg_source_class(self):
        """Return FFmpegPCMAudio class; uses injected class or imports discord."""
        if self._ffmpeg_source_class is not None:
            return self._ffmpeg_source_class
        import discord  # pragma: no cover
        return discord.FFmpegPCMAudio  # pragma: no cover
