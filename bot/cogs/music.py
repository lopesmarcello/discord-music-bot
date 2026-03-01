"""Music commands cog for the Discord bot."""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from bot.audio.queue import GuildQueueRegistry
from bot.audio.resolver import AudioResolver, UnsupportedSourceError
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
        self._current_tracks: dict[int, object] = {}
        self._skipping: dict[int, bool] = {}
        self._started_at: dict[int, float | None] = {}
        self._elapsed_offset: dict[int, float] = {}

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
            if self._skipping.get(guild_id, False):
                self._skipping[guild_id] = False
                return
            loop = self.bot.loop
            if loop and not loop.is_closed():
                asyncio.run_coroutine_threadsafe(self._play_next(guild_id), loop)
        return callback

    async def _play_next(self, guild_id: int) -> None:
        """Pop the next track from the queue and start playback."""
        queue = self._queue_registry.get_queue(guild_id)
        track = queue.next()
        if track is None:
            self._current_tracks[guild_id] = None
            self._started_at[guild_id] = None
            return
        self._current_tracks[guild_id] = track
        self._started_at[guild_id] = time.time()
        self._elapsed_offset[guild_id] = 0.0
        vm = self._get_voice_manager(guild_id)
        await vm.play(track.stream_url)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    @commands.hybrid_command(name="join", description="Join your current voice channel")
    async def join(self, ctx: commands.Context) -> None:
        """Join the voice channel the user is currently in."""
        if ctx.author.voice is None:
            await ctx.send("You must be in a voice channel for me to join.")
            return

        vm = self._get_voice_manager(ctx.guild.id)
        if vm.is_connected():
            await ctx.send("I'm already in a voice channel.")
            return

        await vm.join(ctx.author.voice.channel)
        vm.set_on_track_end(self._make_on_track_end(ctx.guild.id))
        await ctx.send(f"Joined **{ctx.author.voice.channel.name}**.")

    @commands.hybrid_command(name="leave", description="Leave the current voice channel")
    async def leave(self, ctx: commands.Context) -> None:
        """Leave the voice channel, stop playback, and clear the queue."""
        vm = self._get_voice_manager(ctx.guild.id)
        if not vm.is_connected():
            await ctx.send("I'm not in a voice channel.")
            return

        vm.stop()
        self._started_at[ctx.guild.id] = None
        self._elapsed_offset[ctx.guild.id] = 0.0
        self._queue_registry.get_queue(ctx.guild.id).clear()
        self._current_tracks[ctx.guild.id] = None
        await vm.leave()
        await ctx.send("Left the voice channel.")

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

        try:
            track = self._resolver.resolve(query)
        except UnsupportedSourceError:
            await ctx.send(
                "That URL is not supported. Try searching by song name instead,"
                " e.g. `/play artist - song title`."
            )
            return
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
        started_at = self._started_at.get(ctx.guild.id)
        if started_at is not None:
            self._elapsed_offset[ctx.guild.id] = self._elapsed_offset.get(ctx.guild.id, 0.0) + (time.time() - started_at)
            self._started_at[ctx.guild.id] = None
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
        self._started_at[ctx.guild.id] = time.time()
        await ctx.send("Resumed.")

    @commands.hybrid_command(name="skip", description="Skip the current song")
    async def skip(self, ctx: commands.Context) -> None:
        """Skip to the next track."""
        vm = self._get_voice_manager(ctx.guild.id)
        if not vm.is_playing() and not vm.is_paused():
            await ctx.send("Nothing to skip.")
            return
        self._skipping[ctx.guild.id] = True
        vm.stop()
        queue = self._queue_registry.get_queue(ctx.guild.id)
        next_track = queue.peek()
        await self._play_next(ctx.guild.id)
        self._skipping[ctx.guild.id] = False
        if next_track is not None:
            await ctx.send(f"Skipped. Now playing: **{next_track.title}**")
        else:
            await ctx.send("Skipped. Queue is empty.")

    @commands.hybrid_command(name="stop", description="Stop playback and disconnect")
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback, clear queue, and disconnect."""
        vm = self._get_voice_manager(ctx.guild.id)
        if not vm.is_connected():
            await ctx.send("I'm not in a voice channel.")
            return
        vm.stop()
        self._started_at[ctx.guild.id] = None
        self._elapsed_offset[ctx.guild.id] = 0.0
        queue = self._queue_registry.get_queue(ctx.guild.id)
        queue.clear()
        self._current_tracks[ctx.guild.id] = None
        await vm.leave()
        await ctx.send("Stopped and disconnected.")

    @commands.hybrid_command(name="queue", description="View the current song queue")
    async def queue(self, ctx: commands.Context) -> None:
        """Display the current queue."""
        guild_queue = self._queue_registry.get_queue(ctx.guild.id)
        current = self._current_tracks.get(ctx.guild.id)
        tracks = guild_queue.list()

        if current is None and not tracks:
            await ctx.send("The queue is empty.")
            return

        embed = discord.Embed(title="Music Queue")
        lines = []

        if current is not None:
            lines.append(f"**Now Playing:** {current.title}")
            if tracks:
                lines.append("")

        displayed = tracks[:10]
        for i, track in enumerate(displayed, 1):
            lines.append(f"{i}. {track.title}")

        remaining = len(tracks) - 10
        if remaining > 0:
            lines.append(f"...and {remaining} more")

        embed.description = "\n".join(lines)
        await ctx.send(embed=embed)
