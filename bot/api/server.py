"""HTTP API server that runs alongside the Discord bot."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp.web


async def handle_health(request: "aiohttp.web.Request") -> "aiohttp.web.Response":
    """GET /health — lightweight health check for container orchestration."""
    import aiohttp.web  # noqa: PLC0415

    bot = request.app.get("bot")
    bot_ready = bot is not None and bot.is_ready() if bot is not None else False

    import json  # noqa: PLC0415

    return aiohttp.web.Response(
        text=json.dumps({"status": "ok", "bot_ready": bot_ready}),
        content_type="application/json",
    )


def create_app(bot=None) -> "aiohttp.web.Application":
    """Create and return the aiohttp web application.

    Pass the Discord bot instance so queue/playback routes can access it.
    """
    import aiohttp.web  # noqa: PLC0415

    from bot.api.auth import make_jwt_middleware, setup_auth_routes  # noqa: PLC0415
    from bot.api.guilds import setup_guilds_routes  # noqa: PLC0415
    from bot.api.player import setup_player_routes  # noqa: PLC0415
    from bot.api.search import setup_search_routes  # noqa: PLC0415

    app = aiohttp.web.Application(middlewares=[make_jwt_middleware()])
    app.router.add_get("/health", handle_health)
    if bot is not None:
        app["bot"] = bot
    setup_auth_routes(app)
    setup_guilds_routes(app)
    setup_player_routes(app)
    setup_search_routes(app)
    return app


async def start_api_server(
    app: "aiohttp.web.Application",
    host: str,
    port: int,
) -> "aiohttp.web.AppRunner":
    """Start the API server and return the runner for later cleanup."""
    import aiohttp.web  # noqa: PLC0415

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, host, port)
    await site.start()
    return runner
