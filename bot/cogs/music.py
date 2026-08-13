"""Music commands cog for the Discord bot."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from bot.audio.queue import GuildQueueRegistry
from bot.audio.resolver import AudioResolver, UnsupportedSourceError
from bot.services.music import MusicService

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
        self.service = MusicService(
            resolver=resolver,
            queue_registry=queue_registry,
            ffmpeg_source_class=ffmpeg_source_class,
            voice_managers=voice_managers,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_on_track_end(self, guild_id: int):
        """Return a callback that advances the queue when a track finishes."""

        def callback(error: Optional[Exception]) -> None:  # pragma: no cover
            if self.service.skipping.get(guild_id, False):
                self.service.skipping[guild_id] = False
                return
            loop = self.bot.loop
            if loop and not loop.is_closed():
                asyncio.run_coroutine_threadsafe(self.service.play_next(guild_id), loop)

        return callback

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    @commands.hybrid_command(name="join", description="Join your current voice channel")
    async def join(self, ctx: commands.Context) -> None:
        """Join the voice channel the user is currently in."""
        if ctx.author.voice is None:
            await ctx.send("You must be in a voice channel for me to join.")
            return

        vm = self.service.get_voice_manager(ctx.guild.id)
        if vm.is_connected():
            await ctx.send("I'm already in a voice channel.")
            return

        await vm.join(ctx.author.voice.channel)
        vm.set_on_track_end(self._make_on_track_end(ctx.guild.id))
        await ctx.send(f"Joined **{ctx.author.voice.channel.name}**.")

    @commands.hybrid_command(
        name="leave", description="Leave the current voice channel"
    )
    async def leave(self, ctx: commands.Context) -> None:
        """Leave the voice channel, stop playback, and clear the queue."""
        vm = self.service.get_voice_manager(ctx.guild.id)
        if not vm.is_connected():
            await ctx.send("I'm not in a voice channel.")
            return

        vm.stop()
        self.service.started_at[ctx.guild.id] = None
        self.service.elapsed_offset[ctx.guild.id] = 0.0
        self.service.queue_registry.get_queue(ctx.guild.id).clear()
        self.service.current_tracks[ctx.guild.id] = None
        await vm.leave()
        await ctx.send("Left the voice channel.")

    @commands.hybrid_command(
        name="play", description="Play a song by URL or search query"
    )
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Play a song in the voice channel."""
        await ctx.defer()

        if ctx.author.voice is None:
            await ctx.send("You must be in a voice channel to play music.")
            return

        vm = self.service.get_voice_manager(ctx.guild.id)

        if not vm.is_connected():
            await vm.join(ctx.author.voice.channel)
            vm.set_on_track_end(self._make_on_track_end(ctx.guild.id))

        try:
            track = await asyncio.to_thread(self.service.resolver.resolve, query)
        except UnsupportedSourceError:
            await ctx.send(
                "That URL is not supported. Try searching by song name instead,"
                " e.g. `/play artist - song title`."
            )
            return
        if not vm.is_connected():
            await ctx.send("I'm not in a voice channel.")
            return
        queue = self.service.queue_registry.get_queue(ctx.guild.id)
        queue.add(track)

        if not vm.is_playing() and not vm.is_paused():
            await self.service.play_next(ctx.guild.id)
            await ctx.send(f"Now playing: **{track.title}**")
        else:
            await ctx.send(f"Added to queue: **{track.title}**")

    @commands.hybrid_command(name="pause", description="Pause currently playing audio")
    async def pause(self, ctx: commands.Context) -> None:
        """Pause playback."""
        vm = self.service.get_voice_manager(ctx.guild.id)
        if not vm.is_playing():
            await ctx.send("Nothing is currently playing.")
            return
        started_at = self.service.started_at.get(ctx.guild.id)
        if started_at is not None:
            import time  # noqa: PLC0415

            self.service.elapsed_offset[ctx.guild.id] = self.service.elapsed_offset.get(
                ctx.guild.id, 0.0
            ) + (time.time() - started_at)
            self.service.started_at[ctx.guild.id] = None
        vm.pause()
        await ctx.send("Paused.")

    @commands.hybrid_command(name="resume", description="Resume paused audio")
    async def resume(self, ctx: commands.Context) -> None:
        """Resume playback."""
        vm = self.service.get_voice_manager(ctx.guild.id)
        if not vm.is_paused():
            await ctx.send("Playback is not paused.")
            return
        vm.resume()
        import time  # noqa: PLC0415

        self.service.started_at[ctx.guild.id] = time.time()
        await ctx.send("Resumed.")

    @commands.hybrid_command(name="skip", description="Skip the current song")
    async def skip(self, ctx: commands.Context) -> None:
        """Skip to the next track."""
        vm = self.service.get_voice_manager(ctx.guild.id)
        if not vm.is_playing() and not vm.is_paused():
            await ctx.send("Nothing to skip.")
            return
        self.service.skipping[ctx.guild.id] = True
        vm.stop()
        queue = self.service.queue_registry.get_queue(ctx.guild.id)
        next_track = queue.peek()
        await self.service.play_next(ctx.guild.id)
        self.service.skipping[ctx.guild.id] = False
        if next_track is not None:
            await ctx.send(f"Skipped. Now playing: **{next_track.title}**")
        else:
            await ctx.send("Skipped. Queue is empty.")

    @commands.hybrid_command(name="stop", description="Stop playback and disconnect")
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback, clear queue, and disconnect."""
        vm = self.service.get_voice_manager(ctx.guild.id)
        if not vm.is_connected():
            await ctx.send("I'm not in a voice channel.")
            return
        vm.stop()
        self.service.started_at[ctx.guild.id] = None
        self.service.elapsed_offset[ctx.guild.id] = 0.0
        queue = self.service.queue_registry.get_queue(ctx.guild.id)
        queue.clear()
        self.service.current_tracks[ctx.guild.id] = None
        await vm.leave()
        await ctx.send("Stopped and disconnected.")

    @commands.hybrid_command(name="queue", description="View the current song queue")
    async def queue(self, ctx: commands.Context) -> None:
        """Display the current queue."""
        guild_queue = self.service.queue_registry.get_queue(ctx.guild.id)
        current = self.service.current_tracks.get(ctx.guild.id)
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
