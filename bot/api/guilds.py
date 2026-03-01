"""Guild listing API route handler."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp.web


async def handle_guilds_get(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """GET /api/guilds — return guilds the bot and user share.

    Filters bot.guilds to only those present in the JWT guild_ids claim.
    If guild_ids is absent (old session), returns all bot guilds as a
    backward-compatible fallback.
    """
    import aiohttp.web  # noqa: PLC0415, F401

    bot = request.app.get("bot")
    if bot is None:
        return aiohttp.web.Response(
            text=json.dumps({"guilds": []}),
            content_type="application/json",
        )

    jwt_payload = request.get("jwt_payload", {})
    user_guild_ids = jwt_payload.get("guild_ids")

    if user_guild_ids is not None:
        user_guild_id_set = set(user_guild_ids)
        bot_guilds = [g for g in bot.guilds if str(g.id) in user_guild_id_set]
    else:
        bot_guilds = list(bot.guilds)

    guilds = [
        {
            "id": str(guild.id),
            "name": guild.name,
            "icon": guild.icon,
        }
        for guild in bot_guilds
    ]

    return aiohttp.web.Response(
        text=json.dumps({"guilds": guilds}),
        content_type="application/json",
    )


def setup_guilds_routes(app: "aiohttp.web.Application") -> None:
    """Register guilds route on the aiohttp application."""
    import aiohttp.web  # noqa: PLC0415, F401

    app.router.add_get("/api/guilds", handle_guilds_get)
