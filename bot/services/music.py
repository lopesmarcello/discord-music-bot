"""Shared music service — single source of truth for playback state."""

from __future__ import annotations

import time
from typing import Optional

from bot.audio.queue import GuildQueueRegistry
from bot.audio.resolver import AudioResolver
from bot.audio.voice import VoiceManager


class MusicService:
    """Owns playback state and operations shared by the cog and API layer."""

    def __init__(
        self,
        *,
        resolver: Optional[AudioResolver] = None,
        queue_registry: Optional[GuildQueueRegistry] = None,
        ffmpeg_source_class=None,
        voice_managers: Optional[dict] = None,
    ) -> None:
        self.resolver = resolver if resolver is not None else AudioResolver()
        self.queue_registry = (
            queue_registry if queue_registry is not None else GuildQueueRegistry()
        )
        self.ffmpeg_source_class = ffmpeg_source_class
        self.voice_managers: dict[int, VoiceManager] = (
            voice_managers if voice_managers is not None else {}
        )
        self.current_tracks: dict[int, object] = {}
        self.skipping: dict[int, bool] = {}
        self.started_at: dict[int, float | None] = {}
        self.elapsed_offset: dict[int, float] = {}

    def get_voice_manager(self, guild_id: int) -> VoiceManager:
        """Return (or create) the VoiceManager for the given guild."""
        if guild_id not in self.voice_managers:
            self.voice_managers[guild_id] = VoiceManager(
                ffmpeg_source_class=self.ffmpeg_source_class
            )
        return self.voice_managers[guild_id]

    async def play_next(self, guild_id: int) -> None:
        """Pop the next track from the queue and start playback."""
        queue = self.queue_registry.get_queue(guild_id)
        track = queue.next()
        if track is None:
            self.current_tracks[guild_id] = None
            self.started_at[guild_id] = None
            return
        self.current_tracks[guild_id] = track
        self.started_at[guild_id] = time.time()
        self.elapsed_offset[guild_id] = 0.0
        vm = self.get_voice_manager(guild_id)
        await vm.play(track.stream_url)
