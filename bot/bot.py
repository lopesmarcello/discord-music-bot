"""Bot instantiation and cog loading."""

import logging
import os

import discord
from discord.ext import commands


_log = logging.getLogger(__name__)


def create_bot() -> commands.Bot:
    """Create and configure the bot instance."""
    prefix = os.getenv("COMMAND_PREFIX", "!")
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix=prefix,
        intents=intents,
        description="A Discord music bot",
    )

    @bot.event
    async def on_ready() -> None:
        _log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)

    # Load cogs
    async def setup_hook() -> None:
        from bot.cogs.music import Music  # noqa: PLC0415

        await bot.add_cog(Music(bot))
        await bot.tree.sync()

    bot.setup_hook = setup_hook  # type: ignore[method-assign]
    return bot
