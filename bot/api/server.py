"""HTTP API server that runs alongside the Discord bot."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp.web


def create_app() -> "aiohttp.web.Application":
    """Create and return the aiohttp web application."""
    import aiohttp.web  # noqa: PLC0415

    return aiohttp.web.Application()


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
