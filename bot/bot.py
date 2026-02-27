"""Bot instantiation and cog loading."""
import os

import discord
from discord.ext import commands


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
        await bot.tree.sync()
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Load cogs
    async def setup_hook() -> None:
        from bot.cogs.music import Music  # noqa: PLC0415
        await bot.add_cog(Music(bot))

    bot.setup_hook = setup_hook  # type: ignore[method-assign]
    return bot
