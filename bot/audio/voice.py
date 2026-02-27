"""Voice connection manager for Discord audio playback."""
from __future__ import annotations

from typing import Callable, Optional


class VoiceManager:
    """Manages voice channel connection and audio playback for a guild."""

    def __init__(self) -> None:
        self._voice_client = None
        self._on_track_end: Optional[Callable] = None

    async def join(self, channel: object) -> None:
        """Connect to a voice channel."""
        raise NotImplementedError("VoiceManager.join() not yet implemented (US-004)")

    async def leave(self) -> None:
        """Disconnect from the voice channel and clear state."""
        raise NotImplementedError("VoiceManager.leave() not yet implemented (US-004)")

    async def play(self, stream_url: str) -> None:
        """Start audio playback from a stream URL using FFmpeg."""
        raise NotImplementedError("VoiceManager.play() not yet implemented (US-004)")

    def pause(self) -> None:
        """Pause currently playing audio."""
        raise NotImplementedError("VoiceManager.pause() not yet implemented (US-004)")

    def resume(self) -> None:
        """Resume paused audio."""
        raise NotImplementedError("VoiceManager.resume() not yet implemented (US-004)")

    def stop(self) -> None:
        """Stop audio without disconnecting."""
        raise NotImplementedError("VoiceManager.stop() not yet implemented (US-004)")

    def is_playing(self) -> bool:
        """Return True if audio is currently playing."""
        raise NotImplementedError("VoiceManager.is_playing() not yet implemented (US-004)")

    def is_paused(self) -> bool:
        """Return True if audio is currently paused."""
        raise NotImplementedError("VoiceManager.is_paused() not yet implemented (US-004)")

    def set_on_track_end(self, callback: Callable) -> None:
        """Register a callback to be called when a track ends."""
        self._on_track_end = callback
