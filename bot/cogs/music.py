"""Music commands cog for the Discord bot."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from discord.ext.commands import Bot


class Music(commands.Cog):
    """All music-related commands."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="play", description="Play a song by URL or search query")
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Play a song in the voice channel."""
        await ctx.defer()
        # Implementation in US-005
        await ctx.send(f"Play command not yet implemented: {query}")

    @commands.hybrid_command(name="pause", description="Pause currently playing audio")
    async def pause(self, ctx: commands.Context) -> None:
        """Pause playback."""
        # Implementation in US-006
        await ctx.send("Pause command not yet implemented.")

    @commands.hybrid_command(name="resume", description="Resume paused audio")
    async def resume(self, ctx: commands.Context) -> None:
        """Resume playback."""
        # Implementation in US-006
        await ctx.send("Resume command not yet implemented.")

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
