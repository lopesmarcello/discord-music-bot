"""Guild listing API route handler."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp.web


async def handle_guilds_get(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """GET /api/guilds — return the list of guilds the bot is in."""
    import aiohttp.web  # noqa: PLC0415, F401

    bot = request.app.get("bot")
    if bot is None:
        return aiohttp.web.Response(
            text=json.dumps({"guilds": []}),
            content_type="application/json",
        )

    guilds = [
        {
            "id": str(guild.id),
            "name": guild.name,
            "icon": guild.icon,
        }
        for guild in bot.guilds
    ]

    return aiohttp.web.Response(
        text=json.dumps({"guilds": guilds}),
        content_type="application/json",
    )


def setup_guilds_routes(app: "aiohttp.web.Application") -> None:
    """Register guilds route on the aiohttp application."""
    import aiohttp.web  # noqa: PLC0415, F401

    app.router.add_get("/api/guilds", handle_guilds_get)
