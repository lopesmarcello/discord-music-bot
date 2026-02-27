"""Music commands cog for the Discord bot."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from bot.audio.queue import GuildQueueRegistry
from bot.audio.resolver import AudioResolver
from bot.audio.voice import VoiceManager

if TYPE_CHECKING:
    from discord.ext.commands import Bot


class Music(commands.Cog):
    """All music-related commands."""

    def __init__(
        self,
        bot: Bot,
        *,
        resolver: Optional[AudioResolver] = None,
        queue_registry: Optional[GuildQueueRegistry] = None,
        ffmpeg_source_class=None,
        voice_managers: Optional[dict] = None,
    ) -> None:
        self.bot = bot
        self._resolver = resolver if resolver is not None else AudioResolver()
        self._queue_registry = queue_registry if queue_registry is not None else GuildQueueRegistry()
        self._ffmpeg_source_class = ffmpeg_source_class
        self._voice_managers: dict[int, VoiceManager] = (
            voice_managers if voice_managers is not None else {}
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_voice_manager(self, guild_id: int) -> VoiceManager:
        """Return (or create) the VoiceManager for the given guild."""
        if guild_id not in self._voice_managers:
            self._voice_managers[guild_id] = VoiceManager(
                ffmpeg_source_class=self._ffmpeg_source_class
            )
        return self._voice_managers[guild_id]

    def _make_on_track_end(self, guild_id: int):
        """Return a callback that advances the queue when a track finishes."""
        def callback(error: Optional[Exception]) -> None:  # pragma: no cover
            loop = self.bot.loop
            if loop and not loop.is_closed():
                asyncio.run_coroutine_threadsafe(self._play_next(guild_id), loop)
        return callback

    async def _play_next(self, guild_id: int) -> None:
        """Pop the next track from the queue and start playback."""
        queue = self._queue_registry.get_queue(guild_id)
        track = queue.next()
        if track is None:
            return
        vm = self._get_voice_manager(guild_id)
        await vm.play(track.stream_url)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    @commands.hybrid_command(name="play", description="Play a song by URL or search query")
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Play a song in the voice channel."""
        await ctx.defer()

        if ctx.author.voice is None:
            await ctx.send("You must be in a voice channel to play music.")
            return

        vm = self._get_voice_manager(ctx.guild.id)

        if not vm.is_connected():
            await vm.join(ctx.author.voice.channel)
            vm.set_on_track_end(self._make_on_track_end(ctx.guild.id))

        track = self._resolver.resolve(query)
        queue = self._queue_registry.get_queue(ctx.guild.id)
        queue.add(track)

        if not vm.is_playing() and not vm.is_paused():
            await self._play_next(ctx.guild.id)
            await ctx.send(f"Now playing: **{track.title}**")
        else:
            await ctx.send(f"Added to queue: **{track.title}**")

    @commands.hybrid_command(name="pause", description="Pause currently playing audio")
    async def pause(self, ctx: commands.Context) -> None:
        """Pause playback."""
        vm = self._get_voice_manager(ctx.guild.id)
        if not vm.is_playing():
            await ctx.send("Nothing is currently playing.")
            return
        vm.pause()
        await ctx.send("Paused.")

    @commands.hybrid_command(name="resume", description="Resume paused audio")
    async def resume(self, ctx: commands.Context) -> None:
        """Resume playback."""
        vm = self._get_voice_manager(ctx.guild.id)
        if not vm.is_paused():
            await ctx.send("Playback is not paused.")
            return
        vm.resume()
        await ctx.send("Resumed.")

    @commands.hybrid_command(name="skip", description="Skip the current song")
    async def skip(self, ctx: commands.Context) -> None:
        """Skip to the next track."""
        # Implementation in US-007
        await ctx.send("Skip command not yet implemented.")

    @commands.hybrid_command(name="stop", description="Stop playback and disconnect")
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback and clear queue."""
        # Implementation in US-008
        await ctx.send("Stop command not yet implemented.")

    @commands.hybrid_command(name="queue", description="View the current song queue")
    async def queue(self, ctx: commands.Context) -> None:
        """Display the current queue."""
        # Implementation in US-009
        await ctx.send("Queue command not yet implemented.")
